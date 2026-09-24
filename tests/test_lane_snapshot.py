"""Tests for primitives-core/hooks/lane-snapshot/.

Three surfaces are covered, each for a different reason:

  * `snapshot_lanes.resolve_root` — imported and called with its effects passed
    in (env dict, script dir), because the precedence order IS the fix for the
    failure this hook exists to stop (a hardcoded root that snapshotted nothing
    for its whole life).
  * the daemon's one scan pass — run as a subprocess against a real git repo
    with a real linked worktree, because faking `git add -A` under a redirected
    `GIT_INDEX_FILE` would test our idea of git rather than git.
  * the SessionStart hook's pidfile lock — run for real from the main checkout,
    a linked worktree and both harnesses, counting live daemons with `pgrep` as
    an observer independent of the lock under test.
  * the daemon's lifecycle — self-exit when its root is gone or its TTL lapses,
    and `--check` naming a live daemon whose root no longer exists.

Every process this module starts is keyed to a path unique to its own tempdir,
so a `pgrep` count can never pick up another worktree's crew or a parallel run
of this same test; every daemon is killed in a `finally` and the cleanup is
asserted, because a test that leaves a process running is a defect.

Stdlib-only. Skips cleanly when `git` or `pgrep` is missing.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

HOOK_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "primitives-core", "hooks", "lane-snapshot",
)
HOOK_PATH = os.path.join(HOOK_DIR, "hook.py")
DAEMON_PATH = os.path.join(HOOK_DIR, "snapshot_lanes.py")
# This checkout. Nothing in this module may START a daemon against it: the test
# suite's own cwd is a repo, so a hook run with no payload `cwd` will happily
# protect it forever. Escaped and boundary-terminated like every other pattern
# here, because `pgrep -f` takes an ERE and matches a substring: a path holding
# a regex metacharacter, a lane worktree under this root, and a sibling whose
# path merely extends it must all fall outside this count.
REPO_ROOT = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
REPO_PATTERN = "snapshot_lanes\\.py " + re.escape(REPO_ROOT) + "($| )"

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
            "LANE_SNAPSHOT_STATE_DIR": os.path.join(self.base, "state"),
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


def spawn_daemon(sandbox, test, *args, **env_extra):
    """A long-running daemon, reaped by pid in cleanup whatever the test does."""
    proc = subprocess.Popen(
        [sys.executable, DAEMON_PATH] + list(args),
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env=sandbox.env(**env_extra),
    )

    def reap():
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=10)
    test.addCleanup(reap)
    return proc


def wait_exit(proc, seconds=15):
    try:
        return proc.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        return None


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

    def ref_sha(self, name="agent-one", root=None):
        proc = subprocess.run(
            ["git", "-C", root or self.box.root, "rev-parse", "-q", "--verify",
             "refs/lane-snapshots/" + name],
            capture_output=True, text=True, timeout=60,
        )
        return proc.stdout.strip() if proc.returncode == 0 else ""

    def add_worktree(self, path, branch, cwd=None):
        """A linked worktree with dirty content, ready to snapshot."""
        git(cwd or self.box.root, "worktree", "add", "-q", "-b", branch, path)
        write(os.path.join(path, "draft.txt"), "wip\n")
        return path

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

    def test_codex_lanes_are_scanned_when_no_glob_is_set(self):
        """One daemon serves both harnesses, so whichever launched it, the
        unset default has to reach Codex's checkout layout too."""
        lane = os.path.join(self.box.root, ".git", "atelier-codex", "checkouts", "t1", "lane-c")
        git(self.box.root, "worktree", "add", "-q", "-b", "wt-lane-c", lane)
        write(os.path.join(lane, "draft.txt"), "wip\n")
        run_daemon(self.box, "--once", self.box.root)
        self.assertTrue(self.ref_sha("lane-c"), "codex lane got no snapshot ref")

    def checkout_root_lane(self, value, *parts):
        write(os.path.join(self.box.root, ".agents", "atelier.local.md"),
              "---\ncheckout-root: {0}\n---\n".format(value))
        lane = os.path.join(self.box.root, *parts)
        git(self.box.root, "worktree", "add", "-q", "-b", "wt-" + parts[-1], lane)
        write(os.path.join(lane, "draft.txt"), "wip\n")
        return lane

    def test_codex_lanes_follow_the_checkout_root_key(self):
        self.checkout_root_lane(".worktrees", ".worktrees", "t1", "lane-r")
        result = run_daemon(self.box, "--once", self.box.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.ref_sha("lane-r"), "checkout-root lane got no snapshot ref")

    def test_an_invalid_checkout_root_falls_back_to_the_default_and_warns(self):
        self.checkout_root_lane("seed.txt", ".git", "atelier-codex", "checkouts", "t1", "lane-c")
        result = run_daemon(self.box, "--once", self.box.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.ref_sha("lane-c"), "default codex lane got no snapshot ref")
        scans = [r for r in self.box.rows() if r.get("event") == "scan"]
        self.assertIn("checkout-root", scans[-1].get("warning", ""))

    def test_an_unsafe_checkout_root_is_never_globbed(self):
        for value in ("/", "~", ".", ".."):
            with self.subTest(value=value):
                write(os.path.join(self.box.root, ".agents", "atelier.local.md"),
                      "---\ncheckout-root: {0}\n---\n".format(value))
                with mock.patch.dict(os.environ, HOME=self.box.base):
                    patterns, error = snapshot_lanes.default_patterns(self.box.root)
                    lanes = snapshot_lanes.lane_paths(self.box.root, env={})
                self.assertEqual(tuple(patterns), tuple(snapshot_lanes.WORKTREES_DEFAULTS))
                self.assertIn("checkout-root", error or "")
                self.assertEqual(lanes, [self.lane])

    def test_a_root_outside_the_project_is_never_globbed(self):
        os.symlink("/etc", os.path.join(self.box.root, "etclink"))
        for value in ("/etc", "etclink", "~/..", "$HOME"):
            with self.subTest(value=value):
                write(os.path.join(self.box.root, ".agents", "atelier.local.md"),
                      "---\ncheckout-root: {0}\n---\n".format(value))
                with mock.patch.dict(os.environ, HOME=os.path.join(self.box.base, "home", "me")):
                    patterns, error = snapshot_lanes.default_patterns(self.box.root)
                self.assertEqual(tuple(patterns), tuple(snapshot_lanes.WORKTREES_DEFAULTS))
                self.assertIn("checkout-root", error or "")

    def separate_git_dir(self, value):
        root = os.path.join(self.box.base, "sep")
        subprocess.run(["git", "init", "-q", "--separate-git-dir",
                        os.path.join(self.box.base, "store.git"), root],
                       check=True, capture_output=True)
        write(os.path.join(root, ".agents", "atelier.local.md"),
              "---\n" + ("checkout-root: " + value + "\n" if value else "") + "---\n")
        rows = []
        snapshot_lanes.scan(root, rows.append)
        return snapshot_lanes.default_patterns(root), rows[-1]

    def test_separate_git_dir_with_the_key_falls_back_and_warns(self):
        (patterns, error), row = self.separate_git_dir(".worktrees")
        self.assertEqual(tuple(patterns), tuple(snapshot_lanes.WORKTREES_DEFAULTS))
        self.assertIn("unsupported git layout", error or "")
        self.assertIn("unsupported git layout", row.get("warning", ""))

    def test_separate_git_dir_without_the_key_uses_the_default_silently(self):
        (patterns, error), row = self.separate_git_dir(None)
        self.assertEqual(tuple(patterns), tuple(snapshot_lanes.WORKTREES_DEFAULTS))
        self.assertIsNone(error)
        self.assertNotIn("checkout-root", row.get("warning", ""))

    def test_the_env_glob_still_wins_over_the_checkout_root_key(self):
        self.checkout_root_lane(".worktrees", ".worktrees", "t1", "lane-r")
        write(os.path.join(self.lane, "draft.txt"), "wip\n")
        run_daemon(self.box, "--once", self.box.root,
                   env_extra={"LANE_SNAPSHOT_WORKTREES": os.path.join(".claude", "worktrees", "agent-*")})
        self.assertTrue(self.ref_sha())
        self.assertFalse(self.ref_sha("lane-r"), "env glob did not override checkout-root")

    def test_another_daemons_scratch_index_is_left_alone(self):
        """A pre-upgrade daemon holds no lock, so it can run beside a new one;
        the scratch index is per process or one deletes the other's mid-pass
        and commits an empty tree."""
        digest = hashlib.sha1(self.box.root.encode("utf-8")).hexdigest()[:10]
        theirs = os.path.join(self.box.base, "lane-snap-{0}-agent-one.idx".format(digest))
        write(theirs, "in flight\n")
        write(os.path.join(self.lane, "draft.txt"), "wip\n")
        run_daemon(self.box, "--once", self.box.root)
        self.assertTrue(self.ref_sha())
        self.assertTrue(os.path.isfile(theirs), "daemon deleted another process's index")

    def test_snapshot_row_is_logged(self):
        write(os.path.join(self.lane, "draft.txt"), "wip\n")
        run_daemon(self.box, "--once", self.box.root)
        snaps = [r for r in self.box.rows() if r.get("event") == "snapshot"]
        self.assertEqual([r["lane"] for r in snaps], ["agent-one"])
        self.assertEqual(snaps[0]["stream"], "lane-snapshot")
        self.assertTrue(snaps[0]["commit"])

    def sep_repo(self):
        """A seeded repo whose git dir sits outside its checkout."""
        sep = os.path.join(self.box.base, "sep")
        subprocess.run(["git", "init", "-q", "--separate-git-dir",
                        os.path.join(self.box.base, "store.git"), sep],
                       check=True, capture_output=True)
        write(os.path.join(sep, "seed.txt"), "seed\n")
        git(sep, "add", "-A")
        git(sep, "commit", "-q", "-m", "seed")
        return sep

    def test_separate_git_dir_codex_lane_is_snapshotted(self):
        """No `.claude`/`.git` dir tree for the default glob to match — only
        `git worktree list --porcelain` finds this lane at all."""
        sep = self.sep_repo()
        self.add_worktree(
            os.path.join(self.box.base, "store.git", "atelier-codex", "checkouts", "t1", "lane-s"),
            "wt-lane-s", cwd=sep,
        )
        result = run_daemon(self.box, "--once", sep)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.ref_sha("lane-s", root=sep), "separate-git-dir codex lane got no ref")

    def test_daemon_rooted_at_a_lane_reads_no_registry(self):
        """linked_worktrees only fires when git-dir == common-dir; a daemon
        rooted at a lane must see neither its sibling lane nor the main repo."""
        sep = self.sep_repo()
        lane_s = self.add_worktree(
            os.path.join(self.box.base, "store.git", "atelier-codex", "checkouts", "t1", "lane-s"),
            "wt-lane-s", cwd=sep,
        )
        self.add_worktree(
            os.path.join(self.box.base, "store.git", "atelier-codex", "checkouts", "t2", "lane-t"),
            "wt-lane-t", cwd=sep,
        )
        self.assertEqual(snapshot_lanes.lane_paths(lane_s, env={}), [])

    def test_duplicate_basenames_get_distinct_hashed_refs(self):
        a = self.add_worktree(os.path.join(self.box.root, ".worktrees", "dup"), "wt-dup-a")
        write(os.path.join(a, "only-a.txt"), "a\n")
        b = self.add_worktree(os.path.join(self.box.base, "x", "dup"), "wt-dup-b")
        write(os.path.join(b, "only-b.txt"), "b\n")
        result = run_daemon(self.box, "--once", self.box.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        refs = git(self.box.root, "for-each-ref", "--format=%(refname)",
                    "refs/lane-snapshots/").splitlines()
        dup_refs = [r for r in refs if r.startswith("refs/lane-snapshots/dup-")]
        self.assertEqual(len(dup_refs), 2)
        trees = [set(git(self.box.root, "ls-tree", "-r", "--name-only", r).splitlines())
                 for r in dup_refs]
        self.assertTrue(any("only-a.txt" in t and "only-b.txt" not in t for t in trees))
        self.assertTrue(any("only-b.txt" in t and "only-a.txt" not in t for t in trees))
        check = run_daemon(self.box, "--check", self.box.root)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_space_prone_lane_name_is_sanitized(self):
        self.add_worktree(os.path.join(self.box.base, "sp ace", "lane sp"), "wt-lane-sp")
        result = run_daemon(self.box, "--once", self.box.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.ref_sha("lane-sp"), "sanitized lane name got no ref")
        errors = [r for r in self.box.rows() if r.get("event") == "error"]
        self.assertEqual(errors, [])

    def test_worktree_nested_under_a_linked_worktree_is_snapshotted(self):
        outer = self.add_worktree(os.path.join(self.box.root, ".worktrees", "outer"), "wt-outer")
        self.add_worktree(os.path.join(outer, ".claude", "worktrees", "agent-inner"),
                           "wt-inner", cwd=outer)
        result = run_daemon(self.box, "--once", self.box.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.ref_sha("agent-inner"), "nested linked worktree got no ref")

    def test_linked_worktree_outside_the_repo_tree_is_snapshotted(self):
        self.add_worktree(os.path.join(self.box.base, "herdr", "lane-h"), "wt-lane-h")
        result = run_daemon(self.box, "--once", self.box.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.ref_sha("lane-h"), "outside linked worktree got no ref")

    def test_main_checkout_never_snapshotted_and_explicit_glob_stays_glob_only(self):
        self.add_worktree(os.path.join(self.box.base, "herdr", "lane-h"), "wt-lane-h")
        write(os.path.join(self.box.root, "loose.txt"), "dirty main\n")
        # Glob-only pass first: refs are adds-only, so a later default pass
        # picking up lane-h would leave a stale ref this assertion can't see.
        run_daemon(self.box, "--once", self.box.root,
                   env_extra={"LANE_SNAPSHOT_WORKTREES": os.path.join(".claude", "worktrees", "agent-*")})
        self.assertFalse(self.ref_sha("lane-h"), "explicit glob picked up an outside worktree")
        run_daemon(self.box, "--once", self.box.root)
        self.assertFalse(self.ref_sha(os.path.basename(self.box.root)), "main checkout got a ref")


class DaemonLifecycle(unittest.TestCase):
    """A daemon must not outlive the repo it guards, nor run forever idle."""

    def setUp(self):
        require("git")
        self.box = Sandbox()
        self.addCleanup(self.box.destroy)

    def wait_for_row(self, event, seconds=15):
        deadline = time.time() + seconds
        while time.time() < deadline:
            if any(r.get("event") == event for r in self.box.rows()):
                return
            time.sleep(0.1)

    def test_root_removed_daemon_exits(self):
        proc = spawn_daemon(self.box, self, "--interval", "1", self.box.root)
        self.wait_for_row("scan")
        shutil.rmtree(self.box.root)
        self.assertEqual(wait_exit(proc), 0, "daemon outlived its root")
        last = self.box.rows()[-1]
        self.assertEqual((last["event"], last["reason"]), ("exit", "root gone"))

    def test_a_nested_repo_losing_its_git_dir_exits(self):
        """With the root's .git gone, git answers from the enclosing repo; the
        daemon must notice the common dir changed rather than carry on into
        the outer repo's refs."""
        inner = os.path.join(self.box.root, "inner")
        os.makedirs(inner)
        git(inner, "init", "-q", ".")
        proc = spawn_daemon(self.box, self, "--interval", "1", inner,
                            LANE_SNAPSHOT_TTL="0")
        self.wait_for_row("scan")
        shutil.rmtree(os.path.join(inner, ".git"))
        self.assertEqual(wait_exit(proc), 0, "daemon adopted the enclosing repo")
        last = self.box.rows()[-1]
        self.assertEqual((last["event"], last["reason"]), ("exit", "not a git worktree"))

    def test_ttl_with_nothing_written_exits(self):
        proc = spawn_daemon(self.box, self, "--interval", "1", self.box.root,
                            LANE_SNAPSHOT_TTL="1")
        self.assertEqual(wait_exit(proc), 0, "idle daemon ignored its TTL")
        last = self.box.rows()[-1]
        self.assertEqual((last["event"], last["reason"]), ("exit", "ttl"))

    def test_second_daemon_for_the_same_repo_exits(self):
        """The lock, not the hook, is what finally resolves two launches."""
        first = spawn_daemon(self.box, self, "--interval", "1", self.box.root)
        self.wait_for_row("start")
        second = spawn_daemon(self.box, self, "--interval", "1", self.box.root)
        self.assertEqual(wait_exit(second), 0)
        self.assertIsNone(first.poll(), "the lock holder died instead")


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

    def test_check_names_a_live_daemon_whose_root_is_gone(self):
        write(os.path.join(self.lane, "draft.txt"), "wip\n")
        run_daemon(self.box, "--once", self.box.root)
        self.assertEqual(self.check().returncode, 0, "baseline must be green")

        gone = Sandbox()
        self.addCleanup(gone.destroy)
        state = os.path.join(self.box.base, "state")
        # A long interval keeps it asleep, and holding its lock, after the rmtree.
        proc = spawn_daemon(gone, self, "--interval", "3600", gone.root,
                            LANE_SNAPSHOT_STATE_DIR=state)
        deadline = time.time() + 15
        while time.time() < deadline and not any(
                r.get("event") == "scan" for r in gone.rows()):
            time.sleep(0.1)
        shutil.rmtree(gone.root)
        self.assertIsNone(proc.poll(), "daemon exited before it could be orphaned")

        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn(gone.root, result.stdout)
        self.assertIn(str(proc.pid), result.stdout)

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
        # Scoped to the sandbox, never the checkout: a daemon this machine was
        # already running for the checkout is not something a test could have
        # spawned, and an absolute assertion over it fails on any tree that is
        # protecting itself.
        self.addCleanup(
            lambda: self.assertEqual(
                self.daemons(), [], "a test left a daemon running against its sandbox",
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
        return self._pgrep(REPO_PATTERN)

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

    def run_hook(self, cwd=None, env_extra=None):
        payload = {
            "session_id": "test-session",
            "cwd": cwd or self.box.root,
            "hook_event_name": "SessionStart",
            "source": "startup",
        }
        return subprocess.run(
            [sys.executable, HOOK_PATH],
            input=json.dumps(payload), capture_output=True, text=True, timeout=60,
            env=self.box.env(LANE_SNAPSHOT_INTERVAL="1", **(env_extra or {})),
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

    def sandbox_daemons(self):
        """Every daemon rooted anywhere under the sandbox, lanes included."""
        return self._pgrep("snapshot_lanes\\.py .*" + re.escape(self.box.base))

    def kill_sandbox(self):
        for pid in self.sandbox_daemons():
            try:
                os.kill(int(pid), 15)
            except (ProcessLookupError, ValueError, PermissionError):
                pass

    def test_a_linked_worktree_session_shares_the_main_checkouts_daemon(self):
        """A worker session resolves its toplevel to its own lane; keyed by
        the common dir, it still lands on the one daemon for the repo."""
        self.addCleanup(self.kill_sandbox)
        self.assertEqual(self.run_hook(cwd=self.box.lanes["agent-one"]).returncode, 0)
        self.wait_for(1)
        self.assertEqual(self.run_hook().returncode, 0)
        time.sleep(1.5)
        self.assertEqual(len(self.sandbox_daemons()), 1)
        self.assertEqual(len(self.daemons()), 1, "the one daemon is not rooted at the repo")

    def test_each_worktree_of_a_bare_repo_keeps_its_own_daemon(self):
        """A bare repo has no main checkout to root a shared daemon at, so its
        worktrees keep one daemon each rather than leaving the second bare."""
        self.addCleanup(self.kill_sandbox)
        bare = os.path.join(self.box.base, "bare.git")
        git(self.box.base, "clone", "-q", "--bare", self.box.root, bare)
        pattern = "snapshot_lanes\\.py .*" + re.escape(os.path.join(self.box.base, "bt-"))
        for name in ("bt-a", "bt-b"):
            path = os.path.join(self.box.base, name)
            git(bare, "worktree", "add", "-q", "-b", name, path)
            self.assertEqual(self.run_hook(cwd=path).returncode, 0)
        self.wait_for_pattern(pattern, 2)
        time.sleep(1.5)
        self.assertEqual(len(self._pgrep(pattern)), 2)

    def test_hook_spawns_nothing_while_the_repo_lock_is_held(self):
        """The hook's own probe, apart from the daemon-side lock: with the
        pidfile held, it logs and launches nothing."""
        sys.path.insert(0, HOOK_DIR)
        try:
            import snapshot_lanes
        finally:
            sys.path.remove(HOOK_DIR)
        common = os.path.join(self.box.root, ".git")
        env = self.box.env()
        fd = snapshot_lanes.try_lock(snapshot_lanes.pidfile_path(common, env))
        self.assertIsNotNone(fd)
        self.addCleanup(os.close, fd)
        self.addCleanup(self.kill_sandbox)
        self.assertEqual(self.run_hook().returncode, 0)
        hooks = [r for r in self.box.rows() if r.get("event") == "hook"]
        self.assertEqual((hooks[-1]["launched"], hooks[-1]["reason"]),
                         (False, "daemon already running for this repo"))
        self.assertEqual(self.sandbox_daemons(), [])

    def test_stale_pidfile_is_respawned_once(self):
        """A pidfile left by a dead daemon, its lock released, is no daemon:
        the hook launches one, and the next session launches no second."""
        sys.path.insert(0, HOOK_DIR)
        try:
            import snapshot_lanes
        finally:
            sys.path.remove(HOOK_DIR)
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()
        path = snapshot_lanes.pidfile_path(os.path.join(self.box.root, ".git"),
                                           self.box.env())
        write(path, json.dumps({"pid": dead.pid, "root": self.box.root}))
        self.addCleanup(self.kill_sandbox)
        self.assertEqual(self.run_hook().returncode, 0)
        deadline = time.time() + 15
        while time.time() < deadline and not self.sandbox_daemons():
            time.sleep(0.2)
        self.assertEqual(len(self.sandbox_daemons()), 1, "stale pidfile blocked the respawn")
        self.assertEqual(self.run_hook().returncode, 0)
        time.sleep(1.5)
        hooks = [r for r in self.box.rows() if r.get("event") == "hook"]
        self.assertEqual([(r["launched"], r.get("reason")) for r in hooks],
                         [(True, None), (False, "daemon already running for this repo")])
        self.assertEqual(len(self.sandbox_daemons()), 1)

    def test_codex_and_claude_sessions_share_one_daemon(self):
        activation = os.path.join(self.box.base, "atelier.local.md")
        write(activation, "---\nenforce: advisory\n---\n")
        self.addCleanup(self.kill_sandbox)
        codex = self.run_hook(env_extra={"ATELIER_HARNESS": "codex",
                                         "ATELIER_ACTIVATION_FILE": activation})
        self.assertEqual(codex.returncode, 0, codex.stderr)
        deadline = time.time() + 15
        while time.time() < deadline and not self.sandbox_daemons():
            time.sleep(0.2)
        self.assertEqual(len(self.sandbox_daemons()), 1, "codex session launched nothing")
        self.assertEqual(self.run_hook().returncode, 0)
        time.sleep(1.5)
        self.assertEqual(len(self.sandbox_daemons()), 1)

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
        before = set(self.repo_daemons())
        result = subprocess.run(
            [sys.executable, HOOK_PATH],
            input="not json", capture_output=True, text=True, timeout=60,
            env=self.box.env(), cwd=outside,
        )
        self.assertEqual(result.returncode, 0)
        # The NEW pids, not the count: this machine may already be running a
        # daemon for the checkout, and one of the pids in `before` may exit
        # mid-test, which would send a length delta negative.
        self.assertEqual(
            set(self.repo_daemons()) - before, set(),
            "the hook started a daemon against this checkout",
        )


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
