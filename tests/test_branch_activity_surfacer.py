"""Tests for primitives-core/hooks/branch-activity-surfacer/hook.py.

The hook is run as a subprocess in its real shape (SessionStart JSON on stdin,
a JSON line on stdout only when a signal fires) against real git repositories
built in tempdirs — the two signals are derived from `git rev-parse` and
`git log`, so faking the repo would test our idea of git rather than git.

`BRANCH_ACTIVITY_GH=0` in every run: the PR-attribution clause is the one path
that would otherwise reach the network.

Stdlib-only; skips cleanly when `git` is missing.
"""

import itertools
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HOOK_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "primitives-core", "hooks",
    "branch-activity-surfacer", "hook.py",
)

GIT_IDENTITY = (
    "-c", "user.name=fixture",
    "-c", "user.email=fixture@example.invalid",
    "-c", "commit.gpgsign=false",
)

_SEQ = itertools.count()


def require_git():
    if shutil.which("git") is None:
        raise unittest.SkipTest("git is not on PATH")


def git(cwd, *args, **kwargs):
    identity = () if kwargs.get("raw") else GIT_IDENTITY
    proc = subprocess.run(
        ["git"] + list(identity) + list(args),
        cwd=cwd, capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "git {0} failed in {1}: {2}".format(" ".join(args), cwd, proc.stderr.strip())
        )
    return proc.stdout.strip()


def make_repo(base, name="repo"):
    """A real repo with one commit, on branch `main`."""
    root = os.path.join(base, name)
    os.makedirs(root, exist_ok=True)
    git(root, "init", "-q")
    git(root, "commit", "-q", "--allow-empty", "-m", "first commit")
    git(root, "branch", "-M", "main")
    return os.path.realpath(root)


def commit(root, message, author="Peer Author"):
    git(
        root, "-c", "user.name={0}".format(author),
        "-c", "user.email=peer@example.invalid",
        "commit", "-q", "--allow-empty", "-m", message,
    )
    return git(root, "rev-parse", "HEAD")


class BranchActivityTestCase(unittest.TestCase):
    def setUp(self):
        require_git()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.log_path = os.path.join(self.tmp.name, "logs", "branch-activity.jsonl")

    # -- harness -------------------------------------------------------

    def run_hook(self, cwd, session_id=None, source="startup", agent_type=None,
                 env=None, raw_stdin=None):
        payload = {
            "session_id": session_id or "session-{0}".format(next(_SEQ)),
            "cwd": cwd,
            "source": source,
            "hook_event_name": "SessionStart",
        }
        if agent_type is not None:
            payload["agent_type"] = agent_type
        environ = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": self.tmp.name,
            "BRANCH_ACTIVITY_LOG_PATH": self.log_path,
            "BRANCH_ACTIVITY_GH": "0",
        }
        environ.update(env or {})
        stdin = raw_stdin if raw_stdin is not None else json.dumps(payload)
        return subprocess.run(
            [sys.executable, HOOK_PATH], input=stdin,
            capture_output=True, text=True, timeout=60, env=environ,
        )

    def rows(self):
        if not os.path.exists(self.log_path):
            return []
        out = []
        with open(self.log_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue  # the corrupt-ledger fixture writes these on purpose
        return out

    def session_rows(self):
        return [r for r in self.rows() if r.get("event") == "session"]

    def assertSilent(self, proc):
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "", proc.stdout)

    def context(self, proc):
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(
            payload["hookSpecificOutput"]["hookEventName"], "SessionStart",
        )
        return payload


# ---------------------------------------------------------------------------
# The two signals
# ---------------------------------------------------------------------------

class SignalTests(BranchActivityTestCase):
    def test_first_session_on_a_branch_is_silent_and_records_a_row(self):
        repo = make_repo(self.tmp.name)
        head = git(repo, "rev-parse", "HEAD")

        self.assertSilent(self.run_hook(repo, session_id="alpha"))

        rows = self.session_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["branch"], "main")
        self.assertEqual(rows[0]["head"], head)
        self.assertEqual(rows[0]["session_id"], "alpha")
        self.assertEqual(rows[0]["surfaced"], False)
        self.assertTrue(os.path.isabs(rows[0]["repo"]))

    def test_same_session_id_starting_again_is_silent(self):
        repo = make_repo(self.tmp.name)
        self.run_hook(repo, session_id="alpha")

        self.assertSilent(self.run_hook(repo, session_id="alpha", source="clear"))
        self.assertEqual(len(self.session_rows()), 2)

    def test_moved_tip_names_the_new_sha_and_the_commit(self):
        repo = make_repo(self.tmp.name)
        old = git(repo, "rev-parse", "HEAD")
        self.run_hook(repo, session_id="alpha")

        new = commit(repo, "teach the widget to fly", author="Peer Author")

        proc = self.run_hook(repo, session_id="beta")
        payload = self.context(proc)
        ctx = payload["hookSpecificOutput"]["additionalContext"]

        self.assertIn(new[:8], ctx)
        self.assertIn(old[:8], ctx)
        self.assertIn("teach the widget to fly", ctx)
        self.assertIn("Peer Author", ctx)
        self.assertTrue(payload["systemMessage"].startswith("atelier: "))
        self.assertEqual(len(payload["systemMessage"].splitlines()), 1)

        row = self.session_rows()[-1]
        self.assertEqual(row["surfaced"], True)
        self.assertIn("moved", row["signals"])

    def test_peer_within_ttl_fires_without_claiming_a_move(self):
        repo = make_repo(self.tmp.name)
        self.run_hook(repo, session_id="alpha")

        proc = self.run_hook(repo, session_id="beta")
        payload = self.context(proc)
        ctx = payload["hookSpecificOutput"]["additionalContext"]

        self.assertNotIn("->", ctx)
        self.assertNotIn("moved", ctx.lower())
        row = self.session_rows()[-1]
        self.assertEqual(row["signals"], ["peer"])

    def test_stale_peer_is_silent(self):
        repo = make_repo(self.tmp.name)
        self.run_hook(repo, session_id="alpha")

        proc = self.run_hook(
            repo, session_id="beta",
            env={"BRANCH_ACTIVITY_PEER_TTL_SECONDS": "0"},
        )
        self.assertSilent(proc)
        self.assertEqual(self.session_rows()[-1]["signals"], [])

    def test_an_aged_out_prior_row_is_silent(self):
        repo = make_repo(self.tmp.name)
        head = git(repo, "rev-parse", "HEAD")
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        common = os.path.realpath(git(repo, "rev-parse", "--git-common-dir"))
        if not os.path.isabs(common):
            common = os.path.realpath(os.path.join(repo, common))
        with open(self.log_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "event": "session", "ts": "2001-01-01T00:00:00.000Z",
                "repo": common, "branch": "main", "head": head,
                "session_id": "ancient", "cwd": repo,
            }) + "\n")

        self.assertSilent(self.run_hook(repo, session_id="beta"))


# ---------------------------------------------------------------------------
# Eligibility and degradation
# ---------------------------------------------------------------------------

class EligibilityTests(BranchActivityTestCase):
    def test_compact_source_records_no_session_row(self):
        repo = make_repo(self.tmp.name)
        self.run_hook(repo, session_id="alpha")

        self.assertSilent(self.run_hook(repo, session_id="beta", source="compact"))
        self.assertEqual([r["session_id"] for r in self.session_rows()], ["alpha"])

    def test_subagent_records_no_session_row(self):
        repo = make_repo(self.tmp.name)
        self.run_hook(repo, session_id="alpha")

        proc = self.run_hook(repo, session_id="beta", agent_type="builder")
        self.assertSilent(proc)
        self.assertEqual([r["session_id"] for r in self.session_rows()], ["alpha"])

    def test_main_agent_type_is_still_eligible(self):
        repo = make_repo(self.tmp.name)
        self.assertSilent(self.run_hook(repo, session_id="alpha", agent_type="main"))
        self.assertEqual(len(self.session_rows()), 1)

    def test_non_git_cwd_is_silent(self):
        plain = os.path.join(self.tmp.name, "plain")
        os.makedirs(plain)

        proc = self.run_hook(plain, session_id="alpha")
        self.assertSilent(proc)
        self.assertEqual(self.session_rows(), [])

    def test_detached_head_is_silent(self):
        repo = make_repo(self.tmp.name)
        self.run_hook(repo, session_id="alpha")
        commit(repo, "second")
        git(repo, "checkout", "-q", "--detach", "HEAD")

        self.assertSilent(self.run_hook(repo, session_id="beta"))
        self.assertEqual([r["session_id"] for r in self.session_rows()], ["alpha"])

    def test_malformed_stdin_is_silent(self):
        proc = self.run_hook(self.tmp.name, raw_stdin="not json at all")
        self.assertSilent(proc)

    def test_corrupt_ledger_does_not_crash_or_cross_attribute(self):
        repo = make_repo(self.tmp.name)
        head = git(repo, "rev-parse", "HEAD")
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        with open(self.log_path, "w", encoding="utf-8") as fh:
            fh.write("{not json\n")
            fh.write(json.dumps({
                "event": "session", "ts": "2999-01-01T00:00:00.000Z",
                "repo": "/somewhere/else", "branch": "main",
                "head": "0" * 40, "session_id": "other-repo", "cwd": "/somewhere/else",
            }) + "\n")
            fh.write(json.dumps({
                "event": "session", "ts": "2999-01-01T00:00:00.000Z",
                "repo": os.path.realpath(repo), "branch": "other-branch",
                "head": "1" * 40, "session_id": "other-branch", "cwd": repo,
            }) + "\n")
            fh.write('{"event": "session", "ts": "2999-01-0' + "\n")

        proc = self.run_hook(repo, session_id="beta")
        self.assertSilent(proc)
        self.assertEqual(self.session_rows()[-1]["head"], head)

    def test_a_truncated_leading_line_is_discarded(self):
        repo = make_repo(self.tmp.name)
        self.run_hook(repo, session_id="alpha")
        size = os.path.getsize(self.log_path)

        proc = self.run_hook(
            repo, session_id="beta",
            env={"BRANCH_ACTIVITY_MAX_BYTES": str(size // 2)},
        )
        self.assertSilent(proc)


class WorktreeTests(BranchActivityTestCase):
    def test_a_worktree_on_another_branch_does_not_trigger(self):
        repo = make_repo(self.tmp.name)
        side = os.path.join(self.tmp.name, "side")
        git(repo, "worktree", "add", "-q", "-b", "side", side)

        self.run_hook(repo, session_id="alpha")
        commit(repo, "a move on main only")

        proc = self.run_hook(side, session_id="beta")
        self.assertSilent(proc)

        rows = self.session_rows()
        self.assertEqual(rows[-1]["branch"], "side")
        self.assertEqual(rows[-1]["repo"], rows[0]["repo"])


if __name__ == "__main__":
    unittest.main()
