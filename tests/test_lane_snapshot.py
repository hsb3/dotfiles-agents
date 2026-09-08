"""Tests for primitives-core/hooks/lane-snapshot/.

Three surfaces are covered, each for a different reason:

  * `snapshot_lanes.resolve_root` — imported and called with its effects passed
    in (env dict, script dir), because the precedence order IS the fix for the
    failure this hook exists to stop (a hardcoded root that snapshotted nothing
    for its whole life).
  * the daemon's one scan pass — run as a subprocess against a real git repo
    with a real linked worktree, because faking `git add -A` under a redirected
    `GIT_INDEX_FILE` would test our idea of git rather than git.
  * the SessionStart hook's `pgrep` guard — run twice for real, counting live
    daemons 0 -> 1 -> 1 (acceptance criterion 3 asks for this to be re-derived
    here, not cited from another repo).

Every process this module starts is keyed to a path unique to its own tempdir,
so a `pgrep` count can never pick up another worktree's crew or a parallel run
of this same test; every daemon is killed in a `finally` and the cleanup is
asserted, because a test that leaves a process running is a defect.

Stdlib-only. Skips cleanly when `git` or `pgrep` is missing.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HOOK_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "primitives-core", "hooks", "lane-snapshot",
)
HOOK_PATH = os.path.join(HOOK_DIR, "hook.py")
DAEMON_PATH = os.path.join(HOOK_DIR, "snapshot_lanes.py")
# This checkout. Nothing in this module may leave a daemon running against it:
# the test suite's own cwd is a repo, so a hook run with no payload `cwd` will
# happily protect it forever.
REPO_ROOT = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

sys.path.insert(0, HOOK_DIR)
import snapshot_lanes  # noqa: E402  (path must be primed before this import)

GIT_IDENTITY = (
    "-c", "user.name=fixture",
    "-c", "user.email=fixture@example.invalid",
    "-c", "commit.gpgsign=false",
)


def require(tool):
    if shutil.which(tool) is None:
        raise unittest.SkipTest("{0} is not on PATH".format(tool))


def git(cwd, *args):
    proc = subprocess.run(
        ["git"] + list(GIT_IDENTITY) + list(args),
        cwd=cwd, capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError("git {0} failed: {1}".format(" ".join(args), proc.stderr.strip()))
    return proc.stdout.strip()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


class Sandbox:
    """A real repo, optionally with real linked agent worktrees under the
    default glob. `realpath` throughout: on macOS a tempdir is a symlink
    (/var -> /private/var) and git reports the resolved path, so an unresolved
    root would never match what the daemon derives or what pgrep sees."""

    def __init__(self, lanes=()):
        self.base = os.path.realpath(tempfile.mkdtemp(prefix="lanesnap-"))
        self.root = os.path.join(self.base, "repo")
        os.makedirs(self.root)
        git(self.root, "init", "-q", "-b", "main", ".")
        write(os.path.join(self.root, "seed.txt"), "seed\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "seed")
        self.lanes = {}
        for name in lanes:
            path = os.path.join(self.root, ".claude", "worktrees", name)
            git(self.root, "worktree", "add", "-q", "-b", "wt-" + name, path)
            self.lanes[name] = path

    @property
    def log_path(self):
        return os.path.join(self.base, "lane-snapshot.jsonl")

    def env(self, **extra):
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.path.join(self.base, "home"),
            "XDG_DATA_HOME": os.path.join(self.base, "xdg"),
            "TMPDIR": self.base,
            "LANE_SNAPSHOT_LOG_PATH": self.log_path,
        }
        env.update(extra)
        return env

    def rows(self):
        if not os.path.isfile(self.log_path):
            return []
        with open(self.log_path, encoding="utf-8") as fh:
            return [json.loads(ln) for ln in fh.read().splitlines() if ln.strip()]

    def destroy(self):
        shutil.rmtree(self.base, ignore_errors=True)


def run_daemon(sandbox, *args, **kwargs):
    env_extra = kwargs.pop("env_extra", {})
    return subprocess.run(
        [sys.executable, DAEMON_PATH] + list(args),
        capture_output=True, text=True, timeout=120,
        env=sandbox.env(**env_extra),
        **kwargs
    )


class RootResolution(unittest.TestCase):
    """Criterion 1: derived, never hardcoded — and in a stated precedence."""

    def setUp(self):
        require("git")
        self.box = Sandbox()
        self.addCleanup(self.box.destroy)

    def test_env_override_wins_over_argv(self):
        other = os.path.join(self.box.base, "elsewhere")
        os.makedirs(other)
        got = snapshot_lanes.resolve_root(
            argv_root=self.box.root,
            env={"LANE_SNAPSHOT_ROOT": other},
            script_dir=self.box.root,
        )
        self.assertEqual(got, other)

    def test_argv_wins_over_script_location(self):
        got = snapshot_lanes.resolve_root(
            argv_root=self.box.root, env={}, script_dir=self.box.base,
        )
        self.assertEqual(got, self.box.root)

    def test_script_location_is_the_fallback(self):
        """The literal mechanism criterion 1 names, kept for a repo-local
        install: with no env and no argv, the root is derived from where the
        script itself sits."""
        inner = os.path.join(self.box.root, "tools", "hooks")
        os.makedirs(inner)
        got = snapshot_lanes.resolve_root(argv_root=None, env={}, script_dir=inner)
        self.assertEqual(got, self.box.root)

    def test_no_root_anywhere_is_none_not_a_guess(self):
        outside = os.path.join(self.box.base, "not-a-repo")
        os.makedirs(outside)
        self.assertIsNone(
            snapshot_lanes.resolve_root(argv_root=None, env={}, script_dir=outside)
        )


class SnapshotPass(unittest.TestCase):
    def setUp(self):
        require("git")
        self.box = Sandbox(lanes=["agent-one"])
        self.addCleanup(self.box.destroy)
        self.lane = self.box.lanes["agent-one"]

    def ref_sha(self, name="agent-one"):
        proc = subprocess.run(
            ["git", "-C", self.box.root, "rev-parse", "-q", "--verify",
             "refs/lane-snapshots/" + name],
            capture_output=True, text=True, timeout=60,
        )
        return proc.stdout.strip() if proc.returncode == 0 else ""

    def test_dirty_worktree_is_recoverable_from_the_ref(self):
        write(os.path.join(self.lane, "work", "draft.txt"), "uncommitted lane work\n")
        result = run_daemon(self.box, "--once", self.box.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        recovered = git(
            self.box.root, "show", "refs/lane-snapshots/agent-one:work/draft.txt",
        )
        self.assertEqual(recovered, "uncommitted lane work")

    def test_worktree_itself_is_never_modified(self):
        """The out-of-tree GIT_INDEX_FILE: a live agent's index and status must
        read exactly as they did before the daemon ran."""
        write(os.path.join(self.lane, "draft.txt"), "wip\n")
        before = git(self.lane, "status", "--porcelain")
        run_daemon(self.box, "--once", self.box.root)
        self.assertEqual(git(self.lane, "status", "--porcelain"), before)

    def test_unchanged_tree_writes_no_second_commit(self):
        write(os.path.join(self.lane, "draft.txt"), "wip\n")
        run_daemon(self.box, "--once", self.box.root)
        first = self.ref_sha()
        self.assertTrue(first)
        run_daemon(self.box, "--once", self.box.root)
        self.assertEqual(self.ref_sha(), first)

        write(os.path.join(self.lane, "draft.txt"), "wip 2\n")
        run_daemon(self.box, "--once", self.box.root)
        self.assertNotEqual(self.ref_sha(), first)

    def test_adds_only_a_ref_outlives_its_worktree(self):
        """Pruning policy: adds only. A lane's ref surviving the removal of its
        worktree is exactly the case recovery is for."""
        write(os.path.join(self.lane, "draft.txt"), "wip\n")
        run_daemon(self.box, "--once", self.box.root)
        sha = self.ref_sha()
        self.assertTrue(sha)
        git(self.box.root, "worktree", "remove", "--force", self.lane)
        run_daemon(self.box, "--once", self.box.root)
        self.assertEqual(self.ref_sha(), sha)

    def test_zero_worktrees_is_logged_loudly(self):
        """The origin failure: a glob that matches nothing is indistinguishable
        from a working net unless the daemon says so."""
        run_daemon(self.box, "--once", self.box.root,
                   env_extra={"LANE_SNAPSHOT_WORKTREES": "no/such/place/*"})
        scans = [r for r in self.box.rows() if r.get("event") == "scan"]
        self.assertTrue(scans, "daemon logged no scan row at all")
        self.assertEqual(scans[-1]["lanes"], 0)
        self.assertTrue(scans[-1].get("warning"))

    def test_snapshot_row_is_logged(self):
        write(os.path.join(self.lane, "draft.txt"), "wip\n")
        run_daemon(self.box, "--once", self.box.root)
        snaps = [r for r in self.box.rows() if r.get("event") == "snapshot"]
        self.assertEqual([r["lane"] for r in snaps], ["agent-one"])
        self.assertEqual(snaps[0]["stream"], "lane-snapshot")
        self.assertTrue(snaps[0]["commit"])


class CheckMode(unittest.TestCase):
    """Criterion 2, half (b). House rule: a gate that cannot measure is red."""

    def setUp(self):
        require("git")
        self.box = Sandbox(lanes=["agent-one"])
        self.addCleanup(self.box.destroy)
        self.lane = self.box.lanes["agent-one"]

    def check(self, **env_extra):
        return run_daemon(self.box, "--check", self.box.root, env_extra=env_extra)

    def test_fresh_ref_is_green(self):
        write(os.path.join(self.lane, "draft.txt"), "wip\n")
        run_daemon(self.box, "--once", self.box.root)
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_lane_with_no_ref_at_all_is_red(self):
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("agent-one", result.stdout)

    def test_ref_older_than_two_intervals_is_red(self):
        write(os.path.join(self.lane, "draft.txt"), "wip\n")
        run_daemon(self.box, "--once", self.box.root)
        # Interval 0 makes the threshold 0s, so the ref just written is already
        # past it — staleness measured, not simulated by sleeping.
        result = self.check(LANE_SNAPSHOT_INTERVAL="0")
        self.assertEqual(result.returncode, 1)
        self.assertIn("stale", result.stdout)

    def test_unresolvable_root_is_red_not_green(self):
        outside = os.path.join(self.box.base, "not-a-repo")
        os.makedirs(outside)
        result = subprocess.run(
            [sys.executable, DAEMON_PATH, "--check", outside],
            capture_output=True, text=True, timeout=60, env=self.box.env(),
        )
        self.assertEqual(result.returncode, 1)


class HookGuard(unittest.TestCase):
    """Criterion 3: two SessionStart invocations, daemon count 0 -> 1 -> 1."""

    def setUp(self):
        require("git")
        require("pgrep")
        self.box = Sandbox(lanes=["agent-one"])
        self.addCleanup(self.box.destroy)
        # Unique to this tempdir: no sibling worktree's crew and no parallel run
        # of this test can land in the count.
        # Spelled exactly like the hook's own pattern, boundary included: this
        # count IS the assertion in the two collision tests, so a looser one
        # here would swallow the very daemon they are checking is separate.
        self.pattern = "snapshot_lanes\\.py " + re.escape(self.box.root) + "($| )"
        self.addCleanup(
            lambda: self.assertEqual(
                self.repo_daemons(), [], "a test left a daemon running against this checkout",
            )
        )

    @staticmethod
    def _pgrep(pattern):
        proc = subprocess.run(
            ["pgrep", "-f", "--", pattern], capture_output=True, text=True, timeout=30,
        )
        return [p for p in proc.stdout.split() if p.strip()]

    def daemons(self):
        return self._pgrep(self.pattern)

    def kill_pattern(self, pattern):
        for pid in self._pgrep(pattern):
            try:
                os.kill(int(pid), 15)
            except (ProcessLookupError, ValueError, PermissionError):
                pass

    def wait_for_pattern(self, pattern, count, seconds=15):
        deadline = time.time() + seconds
        while time.time() < deadline:
            if len(self._pgrep(pattern)) == count:
                return
            time.sleep(0.2)

    def repo_daemons(self):
        return self._pgrep("snapshot_lanes.py " + REPO_ROOT)

    def kill_all(self):
        for pid in self.daemons():
            try:
                os.kill(int(pid), 15)
            except (ProcessLookupError, ValueError, PermissionError):
                pass
        for _ in range(50):
            if not self.daemons():
                return
            time.sleep(0.2)

    def run_hook(self, cwd=None):
        payload = {
            "session_id": "test-session",
            "cwd": cwd or self.box.root,
            "hook_event_name": "SessionStart",
            "source": "startup",
        }
        return subprocess.run(
            [sys.executable, HOOK_PATH],
            input=json.dumps(payload), capture_output=True, text=True, timeout=60,
            env=self.box.env(LANE_SNAPSHOT_INTERVAL="1"),
        )

    def wait_for(self, count, seconds=15):
        deadline = time.time() + seconds
        while time.time() < deadline:
            if len(self.daemons()) == count:
                return
            time.sleep(0.2)

    def test_second_session_shares_one_daemon(self):
        counts = []
        try:
            counts.append(len(self.daemons()))
            first = self.run_hook()
            self.assertEqual(first.returncode, 0, first.stderr)
            self.wait_for(1)
            counts.append(len(self.daemons()))
            second = self.run_hook()
            self.assertEqual(second.returncode, 0, second.stderr)
            time.sleep(1.5)
            counts.append(len(self.daemons()))
        finally:
            self.kill_all()
        self.assertEqual(counts, [0, 1, 1])
        # Cleanup is part of the contract, not an afterthought.
        self.assertEqual(self.daemons(), [])

    def test_a_prefix_colliding_sibling_repo_still_gets_its_own_daemon(self):
        """`pgrep -f` matches a substring, so an unanchored pattern let a live
        daemon for `<root>-second` answer for `<root>`: the hook launched
        nothing and logged that a daemon was already running, while the repo
        had no protection at all."""
        sibling = self.box.root + "-second"
        os.makedirs(sibling)
        git(sibling, "init", "-q", "-b", "main", ".")
        write(os.path.join(sibling, "seed.txt"), "seed\n")
        git(sibling, "add", "-A")
        git(sibling, "commit", "-q", "-m", "seed")
        sibling_pattern = "snapshot_lanes\\.py " + re.escape(sibling) + "($|[/ ])"
        self.addCleanup(self.kill_pattern, sibling_pattern)
        try:
            self.assertEqual(self.run_hook(cwd=sibling).returncode, 0)
            self.wait_for_pattern(sibling_pattern, 1)
            self.assertEqual(len(self._pgrep(sibling_pattern)), 1, "sibling daemon did not start")

            self.assertEqual(self.run_hook().returncode, 0)
            self.wait_for(1)
            self.assertEqual(
                len(self.daemons()), 1,
                "the sibling's daemon was mistaken for this root's",
            )
        finally:
            self.kill_all()

    def test_a_lane_worktrees_daemon_does_not_answer_for_the_repo_above_it(self):
        """The boundary class must not contain `/`. A worker session opening in
        `.claude/worktrees/agent-*` resolves its toplevel to the LANE, so its
        daemon is rooted there and snapshots nothing; if that daemon can answer
        for the repo above it, every lane goes unprotected while the ledger
        says otherwise. This is the pgrep-substring defect one boundary over."""
        lane = self.box.lanes["agent-one"]
        lane_pattern = "snapshot_lanes\\.py " + re.escape(lane) + "($| )"
        self.addCleanup(self.kill_pattern, lane_pattern)
        try:
            self.assertEqual(self.run_hook(cwd=lane).returncode, 0)
            self.wait_for_pattern(lane_pattern, 1)
            self.assertEqual(len(self._pgrep(lane_pattern)), 1, "lane daemon did not start")

            self.assertEqual(self.run_hook().returncode, 0)
            self.wait_for(1)
            self.assertEqual(
                len(self.daemons()), 1,
                "the lane's daemon was mistaken for the repo root's",
            )
        finally:
            self.kill_all()

    def test_hook_never_blocks_when_the_root_is_not_a_repo(self):
        """Every path exits 0 and launches nothing: a failed resolution must
        not slow or fail a session start."""
        outside = os.path.join(self.box.base, "not-a-repo")
        os.makedirs(outside)
        result = subprocess.run(
            [sys.executable, HOOK_PATH],
            input=json.dumps({"cwd": outside, "session_id": "x", "source": "startup"}),
            capture_output=True, text=True, timeout=60, env=self.box.env(),
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.daemons(), [])

    def test_hook_survives_garbage_stdin(self):
        """Unreadable stdin still exits 0. Run from a non-repo cwd on purpose:
        with no `cwd` in the payload the hook falls back to its own working
        directory, which is correct in production (a hook runs in the project
        dir) and is exactly how an earlier draft of this test leaked a live
        daemon against the checkout it was running in."""
        outside = os.path.join(self.box.base, "cwd-not-a-repo")
        os.makedirs(outside)
        result = subprocess.run(
            [sys.executable, HOOK_PATH],
            input="not json", capture_output=True, text=True, timeout=60,
            env=self.box.env(), cwd=outside,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.repo_daemons(), [])


class ReadmeContract(unittest.TestCase):
    """Criterion 5: the recovery path is documented, not folklore."""

    def test_readme_documents_recovery_and_pruning(self):
        with open(os.path.join(HOOK_DIR, "README.md"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("git show refs/lane-snapshots/", text)
        self.assertIn("git update-ref -d refs/lane-snapshots/", text)
        self.assertTrue(re.search(r"^## Design notes", text, re.M))


if __name__ == "__main__":
    unittest.main()
