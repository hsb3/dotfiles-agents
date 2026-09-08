"""Tests for primitives-core/hooks/branch-activity-surfacer/hook.py.

The hook is run as a subprocess in its real shape (SessionStart JSON on stdin,
a JSON line on stdout only when a signal fires) against real git repositories
built in tempdirs — the signals are derived from `git rev-parse` and `git log`,
so faking the repo would test our idea of git rather than git.

Two environment overrides keep this hermetic:

  * `BRANCH_ACTIVITY_GH=0` in every run — the PR clause is the one path that
    would otherwise reach the network.
  * `BRANCH_ACTIVITY_OWNER_PID` per run — every hook subprocess here shares one
    parent, so the real lineage walk would give them all the same owner and no
    test could ever produce a peer. The override supplies the identity the walk
    would have found. Liveness is NOT faked: a live pid is a genuinely running
    process and a dead pid is a genuinely reaped one.

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


def git(cwd, *args):
    proc = subprocess.run(
        ["git"] + list(GIT_IDENTITY) + list(args),
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


def reaped_pid():
    """A pid that is genuinely gone: a child, started and waited for."""
    proc = subprocess.Popen([sys.executable, "-c", ""])
    proc.wait()
    return proc.pid


class BranchActivityTestCase(unittest.TestCase):
    def setUp(self):
        require_git()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.log_path = os.path.join(self.tmp.name, "logs", "branch-activity.jsonl")

    # -- harness -------------------------------------------------------

    def run_hook(self, cwd, session_id=None, source="startup", agent_type=None,
                 owner_pid=None, env=None, raw_stdin=None):
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
        if owner_pid is not None:
            environ["BRANCH_ACTIVITY_OWNER_PID"] = str(owner_pid)
        environ.update(env or {})
        stdin = raw_stdin if raw_stdin is not None else json.dumps(payload)
        return subprocess.run(
            [sys.executable, HOOK_PATH], input=stdin,
            capture_output=True, text=True, timeout=60, env=environ,
        )

    def write_ledger(self, *rows):
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        with open(self.log_path, "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(row if isinstance(row, str) else json.dumps(row))
                fh.write("\n")

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
                    continue  # the corrupt-ledger fixtures write these on purpose
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
        self.assertTrue(payload["systemMessage"].startswith("atelier: "))
        self.assertEqual(len(payload["systemMessage"].splitlines()), 1)
        return payload["hookSpecificOutput"]["additionalContext"]


# ---------------------------------------------------------------------------
# moved — "has the tip moved since anyone last recorded a start here"
# ---------------------------------------------------------------------------

class MovedTests(BranchActivityTestCase):
    def test_first_session_on_a_branch_is_silent_and_records_a_row(self):
        repo = make_repo(self.tmp.name)
        head = git(repo, "rev-parse", "HEAD")

        self.assertSilent(self.run_hook(repo, session_id="alpha", owner_pid=os.getpid()))

        rows = self.session_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["branch"], "main")
        self.assertEqual(rows[0]["head"], head)
        self.assertEqual(rows[0]["session_id"], "alpha")
        self.assertEqual(rows[0]["owner_pid"], os.getpid())
        self.assertEqual(rows[0]["surfaced"], False)
        self.assertTrue(os.path.isabs(rows[0]["repo"]))

    def test_an_unchanged_tip_is_silent(self):
        repo = make_repo(self.tmp.name)
        self.run_hook(repo, session_id="alpha", owner_pid=os.getpid())

        self.assertSilent(self.run_hook(
            repo, session_id="alpha", source="clear", owner_pid=os.getpid(),
        ))
        self.assertEqual(len(self.session_rows()), 2)

    def test_moved_names_the_new_sha_and_the_commit(self):
        repo = make_repo(self.tmp.name)
        old = git(repo, "rev-parse", "HEAD")
        self.run_hook(repo, session_id="alpha", owner_pid=os.getpid())

        new = commit(repo, "teach the widget to fly", author="Ada Lovelace")

        ctx = self.context(self.run_hook(repo, session_id="beta", owner_pid=os.getpid()))
        self.assertIn(new[:8], ctx)
        self.assertIn(old[:8], ctx)
        self.assertIn("teach the widget to fly", ctx)
        self.assertIn("Ada Lovelace", ctx)

        row = self.session_rows()[-1]
        self.assertEqual(row["surfaced"], True)
        self.assertIn("moved", row["signals"])

    def test_moved_fires_against_this_sessions_own_earlier_row(self):
        """The peer restarts and records the new tip before this session next
        starts. Keyed on another session, this move would go unreported."""
        repo = make_repo(self.tmp.name)
        self.run_hook(repo, session_id="alpha", owner_pid=os.getpid())
        new = commit(repo, "a move this session has not seen")

        ctx = self.context(self.run_hook(
            repo, session_id="alpha", source="resume", owner_pid=os.getpid(),
        ))
        self.assertIn(new[:8], ctx)
        self.assertEqual(self.session_rows()[-1]["signals"], ["moved"])

    def test_a_rewind_reports_the_commits_that_are_gone(self):
        repo = make_repo(self.tmp.name)
        base = git(repo, "rev-parse", "HEAD")
        commit(repo, "a commit about to be discarded")
        self.run_hook(repo, session_id="alpha", owner_pid=os.getpid())

        git(repo, "reset", "-q", "--hard", base)

        ctx = self.context(self.run_hook(repo, session_id="beta", owner_pid=os.getpid()))
        self.assertIn("1", ctx)
        self.assertIn("no longer", ctx.lower())
        self.assertIn(base[:8], ctx)

    def test_an_unreachable_prior_tip_degrades_to_naming_both_shas(self):
        repo = make_repo(self.tmp.name)
        head = git(repo, "rev-parse", "HEAD")
        self.write_ledger({
            "event": "session", "ts": "2001-01-01T00:00:00.000Z",
            "repo": self.repo_key(repo), "branch": "main", "head": "a" * 40,
            "session_id": "ghost", "cwd": repo,
        })

        ctx = self.context(self.run_hook(repo, session_id="beta", owner_pid=os.getpid()))
        self.assertIn(head[:8], ctx)
        self.assertIn("a" * 8, ctx)

    def repo_key(self, repo):
        common = git(repo, "rev-parse", "--git-common-dir")
        if not os.path.isabs(common):
            common = os.path.join(repo, common)
        return os.path.realpath(common)


# ---------------------------------------------------------------------------
# peer — "is another session's process still alive on this branch"
# ---------------------------------------------------------------------------

class PeerTests(BranchActivityTestCase):
    def test_a_live_owner_pid_within_the_ttl_is_a_peer(self):
        repo = make_repo(self.tmp.name)
        self.run_hook(repo, session_id="alpha", owner_pid=os.getpid())

        ctx = self.context(self.run_hook(
            repo, session_id="beta", owner_pid=reaped_pid(),
        ))
        self.assertIn("alpha", ctx)
        self.assertNotIn("->", ctx)
        self.assertNotIn("moved", ctx.lower())
        self.assertEqual(self.session_rows()[-1]["signals"], ["peer"])

    def test_the_same_owner_pid_is_never_a_peer(self):
        """`/clear` mints a new session_id inside the same process. Keyed on
        session_id, the operator is reported to themselves."""
        repo = make_repo(self.tmp.name)
        self.run_hook(repo, session_id="alpha", owner_pid=os.getpid())

        proc = self.run_hook(
            repo, session_id="beta-after-clear", source="clear", owner_pid=os.getpid(),
        )
        self.assertSilent(proc)
        self.assertEqual(self.session_rows()[-1]["signals"], [])

    def test_a_dead_owner_pid_is_not_a_peer(self):
        repo = make_repo(self.tmp.name)
        self.run_hook(repo, session_id="alpha", owner_pid=reaped_pid())

        proc = self.run_hook(repo, session_id="beta", owner_pid=os.getpid())
        self.assertSilent(proc)

    def test_a_dead_peer_still_yields_the_moved_warning(self):
        repo = make_repo(self.tmp.name)
        self.run_hook(repo, session_id="alpha", owner_pid=reaped_pid())
        commit(repo, "left behind by a session that quit")

        ctx = self.context(self.run_hook(repo, session_id="beta", owner_pid=os.getpid()))
        self.assertEqual(self.session_rows()[-1]["signals"], ["moved"])
        self.assertIn("left behind by a session that quit", ctx)

    def test_several_live_peers_are_listed(self):
        repo = make_repo(self.tmp.name)
        self.run_hook(repo, session_id="alpha", owner_pid=os.getpid())
        self.run_hook(repo, session_id="gamma", owner_pid=os.getppid())

        ctx = self.context(self.run_hook(repo, session_id="beta", owner_pid=reaped_pid()))
        self.assertIn("alpha", ctx)
        self.assertIn("gamma", ctx)

    def test_a_row_without_an_owner_pid_falls_back_to_session_id(self):
        repo = make_repo(self.tmp.name)
        head = git(repo, "rev-parse", "HEAD")
        self.write_ledger({
            "event": "session", "ts": _now_iso(), "repo": self.repo_key(repo),
            "branch": "main", "head": head, "session_id": "legacy", "cwd": repo,
        })

        ctx = self.context(self.run_hook(repo, session_id="beta", owner_pid=os.getpid()))
        self.assertIn("legacy", ctx)

    def test_a_stale_peer_is_silent(self):
        repo = make_repo(self.tmp.name)
        self.run_hook(repo, session_id="alpha", owner_pid=os.getpid())

        proc = self.run_hook(
            repo, session_id="beta", owner_pid=reaped_pid(),
            env={"BRANCH_ACTIVITY_PEER_TTL_SECONDS": "0"},
        )
        self.assertSilent(proc)
        self.assertEqual(self.session_rows()[-1]["signals"], [])

    def test_an_aged_out_prior_row_is_silent(self):
        repo = make_repo(self.tmp.name)
        head = git(repo, "rev-parse", "HEAD")
        self.write_ledger({
            "event": "session", "ts": "2001-01-01T00:00:00.000Z",
            "repo": self.repo_key(repo), "branch": "main", "head": head,
            "session_id": "ancient", "cwd": repo,
        })

        self.assertSilent(self.run_hook(repo, session_id="beta", owner_pid=os.getpid()))

    repo_key = MovedTests.repo_key


def _now_iso():
    from datetime import datetime, timezone
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


# ---------------------------------------------------------------------------
# Eligibility and degradation
# ---------------------------------------------------------------------------

class EligibilityTests(BranchActivityTestCase):
    repo_key = MovedTests.repo_key

    def test_compact_source_records_no_session_row(self):
        repo = make_repo(self.tmp.name)
        self.run_hook(repo, session_id="alpha", owner_pid=os.getpid())

        self.assertSilent(self.run_hook(repo, session_id="beta", source="compact"))
        self.assertEqual([r["session_id"] for r in self.session_rows()], ["alpha"])

    def test_fork_source_is_eligible(self):
        repo = make_repo(self.tmp.name)
        self.run_hook(repo, session_id="alpha", owner_pid=os.getpid())
        new = commit(repo, "a commit the fork has not seen")

        ctx = self.context(self.run_hook(
            repo, session_id="beta", source="fork", owner_pid=os.getpid(),
        ))
        self.assertIn(new[:8], ctx)
        self.assertEqual(self.session_rows()[-1]["source"], "fork")

    def test_subagent_records_no_session_row(self):
        repo = make_repo(self.tmp.name)
        self.run_hook(repo, session_id="alpha", owner_pid=os.getpid())

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

    def test_detached_head_is_silent_and_says_so(self):
        repo = make_repo(self.tmp.name)
        commit(repo, "second")
        git(repo, "checkout", "-q", "--detach", "HEAD")

        self.assertSilent(self.run_hook(repo, session_id="beta"))
        self.assertEqual(self.session_rows(), [])
        self.assertEqual(self.rows()[-1]["reason"], "detached HEAD")

    def test_an_unborn_branch_is_distinguished_from_a_detached_head(self):
        empty = os.path.join(self.tmp.name, "empty")
        os.makedirs(empty)
        git(empty, "init", "-q")

        self.assertSilent(self.run_hook(empty, session_id="alpha"))
        self.assertEqual(self.rows()[-1]["reason"], "no commits")

    def test_malformed_stdin_is_silent(self):
        proc = self.run_hook(self.tmp.name, raw_stdin="not json at all")
        self.assertSilent(proc)

    def test_a_naive_timestamp_neither_crashes_nor_suppresses_the_row(self):
        """A row whose ts carries no zone used to raise inside the age
        subtraction, and fail-open then swallowed the session row too — one
        bad row disabled the hook for that branch forever."""
        repo = make_repo(self.tmp.name)
        head = git(repo, "rev-parse", "HEAD")
        self.write_ledger({
            "event": "session", "ts": "2026-09-08T12:00:00.000",
            "repo": self.repo_key(repo), "branch": "main", "head": head,
            "session_id": "naive", "cwd": repo,
        })

        self.assertSilent(self.run_hook(repo, session_id="beta", owner_pid=os.getpid()))
        self.assertEqual(self.session_rows()[-1]["session_id"], "beta")
        self.assertEqual([r.get("event") for r in self.rows() if r.get("event") == "error"], [])

    def test_corrupt_ledger_does_not_crash_or_cross_attribute(self):
        repo = make_repo(self.tmp.name)
        head = git(repo, "rev-parse", "HEAD")
        self.write_ledger(
            "{not json",
            {
                "event": "session", "ts": "2999-01-01T00:00:00.000Z",
                "repo": "/somewhere/else", "branch": "main", "head": "0" * 40,
                "session_id": "other-repo", "cwd": "/somewhere/else",
            },
            {
                "event": "session", "ts": "2999-01-01T00:00:00.000Z",
                "repo": self.repo_key(repo), "branch": "other-branch",
                "head": "1" * 40, "session_id": "other-branch", "cwd": repo,
            },
            {
                "event": "session", "ts": "2999-01-01T00:00:00.000Z",
                "repo": self.repo_key(repo), "branch": "main", "head": "",
                "session_id": "blank-head", "cwd": repo,
            },
            '{"event": "session", "ts": "2999-01-0',
        )

        proc = self.run_hook(repo, session_id="beta", owner_pid=os.getpid())
        self.assertSilent(proc)
        self.assertEqual(self.session_rows()[-1]["head"], head)


class LedgerTailTests(BranchActivityTestCase):
    """The tail read drops the partial line after its seek. The two tests use
    the SAME row bytes: valid on their own line it fires, and as the tail of a
    longer line it must not — so removing the partial-line skip flips one of
    them."""

    repo_key = MovedTests.repo_key

    def _firing_row(self, repo):
        return json.dumps({
            "event": "session", "ts": _now_iso(), "repo": self.repo_key(repo),
            "branch": "main", "head": "a" * 40, "session_id": "torn", "cwd": repo,
        })

    def test_the_row_fires_when_it_is_a_whole_line(self):
        repo = make_repo(self.tmp.name)
        self.write_ledger(self._firing_row(repo))

        ctx = self.context(self.run_hook(repo, session_id="beta", owner_pid=os.getpid()))
        self.assertIn("a" * 8, ctx)

    def test_the_same_row_is_dropped_when_it_is_a_torn_line_tail(self):
        repo = make_repo(self.tmp.name)
        row = self._firing_row(repo)
        prefix = "X" * 64  # makes the whole line unparseable; the tail alone is not
        self.write_ledger(prefix + row)

        proc = self.run_hook(
            repo, session_id="beta", owner_pid=os.getpid(),
            env={"BRANCH_ACTIVITY_MAX_BYTES": str(len(row) + 1)},
        )
        self.assertSilent(proc)


class WorktreeTests(BranchActivityTestCase):
    def test_a_worktree_on_another_branch_does_not_trigger(self):
        repo = make_repo(self.tmp.name)
        side = os.path.join(self.tmp.name, "side")
        git(repo, "worktree", "add", "-q", "-b", "side", side)

        self.run_hook(repo, session_id="alpha", owner_pid=os.getpid())
        commit(repo, "a move on main only")

        proc = self.run_hook(side, session_id="beta", owner_pid=reaped_pid())
        self.assertSilent(proc)

        rows = self.session_rows()
        self.assertEqual(rows[-1]["branch"], "side")
        self.assertEqual(rows[-1]["repo"], rows[0]["repo"])


if __name__ == "__main__":
    unittest.main()
