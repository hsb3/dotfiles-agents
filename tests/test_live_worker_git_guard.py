"""Tests for primitives-core/hooks/live-worker-git-guard/hook.py.

Runs the hook as a subprocess (its real invocation shape: JSON on stdin, a
JSON line on stdout only on deny/override, env-configured ledger paths)
against a fixture that mirrors Claude Code's real on-disk layout:

    <projects>/<slug>/<session_id>.jsonl                            parent transcript
    <projects>/<slug>/<session_id>/subagents/agent-<id>.meta.json   sidecar
    <projects>/<slug>/<session_id>/subagents/agent-<id>.jsonl       subagent transcript

The pending set is the same one subagent-telemetry computes for its stall
rows: sidecars present minus the agent_ids the delegation ledger has already
settled. Stdlib-only; fixtures build into a tempdir per test, and the
subprocess environment is built from scratch with only PATH inherited.
"""

import itertools
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

HOOKS_ROOT = os.path.join(
    os.path.dirname(__file__), "..", "primitives-core", "hooks")
HOOK_PATH = os.path.join(HOOKS_ROOT, "live-worker-git-guard", "hook.py")

sys.path.insert(0, os.path.join(HOOKS_ROOT, "_lib"))
import pending  # noqa: E402  (path must be primed before this import)

_SEQ = itertools.count()


def _session_id():
    return "git-guard-session-{0}".format(next(_SEQ))


def _read_rows(log_path):
    if not os.path.exists(log_path):
        return []
    with open(log_path, encoding="utf-8") as fh:
        return [json.loads(ln) for ln in fh.read().splitlines() if ln.strip()]


class LiveWorkerGitGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = os.path.join(self.tmp.name, "cwd")
        os.makedirs(self.cwd, exist_ok=True)
        self.session_id = _session_id()
        self.projects = os.path.join(self.tmp.name, "projects", "-slug")
        self.transcript_path = os.path.join(
            self.projects, "{0}.jsonl".format(self.session_id))
        self.subagents_dir = os.path.join(
            self.projects, self.session_id, "subagents")
        os.makedirs(self.projects, exist_ok=True)
        with open(self.transcript_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"type": "assistant"}) + "\n")
        # The delegation ledger the guard READS (subagent-telemetry writes it)
        # and the guard's OWN ledger. Both sandboxed into the tempdir.
        self.delegation_log = os.path.join(self.tmp.name, "logs", "delegation.jsonl")
        self.guard_log = os.path.join(
            self.tmp.name, "logs", "live-worker-git-guard.jsonl")

    # -- fixtures ------------------------------------------------------

    def _sidecar(self, agent_id, agent_type="atelier:builder",
                 description="Do a bounded slice", worktree_path=None):
        """A started delegation: its sidecar, as Claude Code writes it."""
        os.makedirs(self.subagents_dir, exist_ok=True)
        meta = {
            "agentType": agent_type,
            "description": description,
            "toolUseId": "toolu_{0}".format(agent_id),
            "spawnDepth": 1,
        }
        if worktree_path is not None:
            meta["worktreePath"] = worktree_path
            meta["worktreeBranch"] = "agent/{0}".format(agent_id)
        path = os.path.join(
            self.subagents_dir, "agent-{0}.meta.json".format(agent_id))
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(meta))
        return agent_id

    def _settle(self, agent_id):
        """A delegation row in the ledger — the agent stopped."""
        os.makedirs(os.path.dirname(self.delegation_log), exist_ok=True)
        with open(self.delegation_log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "v": 1, "plugin": "atelier", "harness": "claude-code",
                "stream": "delegation", "ts": "2026-08-20T15:37:08.666Z",
                "project": self.cwd, "session_id": self.session_id,
                "agent_id": agent_id, "agent_type": "atelier:builder",
                "model": "claude-sonnet-5", "ctx_tokens": 1234,
            }) + "\n")

    def _payload(self, command, tool_name="Bash", transcript_path=None,
                 agent_id=None):
        payload = {
            "session_id": self.session_id,
            "transcript_path": self.transcript_path
            if transcript_path is None else transcript_path,
            "cwd": self.cwd,
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "tool_input": {"command": command},
        }
        if agent_id is not None:
            # Present only when the call comes from inside a subagent.
            payload["agent_id"] = agent_id
            payload["agent_type"] = "atelier:manager"
        return payload

    def _run(self, payload, stdin_text=None, extra_env=None):
        env = {
            "PATH": os.environ.get("PATH", ""),
            # HOME as well as XDG_DATA_HOME: expanduser("~") falls back to the
            # passwd entry when HOME is unset, so unsetting alone does not
            # contain a write to the real ~/.local/share/agent-logs ledger.
            "HOME": os.path.join(self.tmp.name, "home"),
            "XDG_DATA_HOME": os.path.join(self.tmp.name, "xdg"),
            "SUBAGENT_TELEMETRY_LOG_PATH": self.delegation_log,
            "LIVE_WORKER_GIT_GUARD_LOG_PATH": self.guard_log,
        }
        if extra_env:
            env.update(extra_env)
        result = subprocess.run(
            [sys.executable, HOOK_PATH],
            input=json.dumps(payload) if stdin_text is None else stdin_text,
            capture_output=True, text=True, env=env, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def _assert_silent(self, result):
        self.assertEqual(result.stdout.strip(), "", result.stdout)
        self.assertEqual(_read_rows(self.guard_log), [], "silent paths log nothing")
        return result

    def _assert_denied(self, result):
        payload = json.loads(result.stdout)
        hso = payload["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], "PreToolUse")
        self.assertEqual(hso["permissionDecision"], "deny")
        return hso["permissionDecisionReason"]

    # -- the guard fires on mutating git while a worker is live -----------

    def test_commit_with_one_pending_child_is_denied_and_names_the_agent(self):
        self._sidecar("a1111111111111111", agent_type="atelier:builder",
                      description="Rewrite the roster guard")
        reason = self._assert_denied(
            self._run(self._payload('git commit -m "wip"')))
        self.assertIn("commit", reason)
        self.assertIn("a1111111111111111", reason)
        self.assertIn("atelier:builder", reason)
        self.assertIn("Rewrite the roster guard", reason)

    def test_reason_explains_the_shared_tree_and_the_override(self):
        self._sidecar("a2222222222222222")
        reason = self._assert_denied(
            self._run(self._payload("git commit -am wip")))
        self.assertIn("ATELIER_GIT_GUARD_OVERRIDE=1", reason)
        # The stopgap's known failure mode: a blocked agent stashes by hand and
        # reintroduces the exact window the guard closes.
        self.assertIn("stash", reason.lower())

    def test_pull_checkout_and_stash_are_denied(self):
        self._sidecar("a3333333333333333")
        for command, verb in (
            ("git pull --ff-only origin dev", "pull"),
            ("git checkout dev", "checkout"),
            ("git stash", "stash"),
            ("git switch dev", "switch"),
            ("git rebase origin/dev", "rebase"),
            ("git reset --hard origin/dev", "reset"),
            ("git restore Makefile", "restore"),
            ("git -C /repo commit -m x", "commit"),
            # An absolute path is the same program: matching the bare word
            # only would put the guard one `/usr/bin/` away from off.
            ("/usr/bin/git commit -m x", "commit"),
        ):
            with self.subTest(command=command):
                reason = self._assert_denied(self._run(self._payload(command)))
                self.assertIn(verb, reason)

    def test_compound_command_is_denied_on_its_first_mutating_verb(self):
        self._sidecar("a4444444444444444")
        reason = self._assert_denied(
            self._run(self._payload("git checkout dev && git pull --ff-only")))
        self.assertIn("checkout", reason)

    def test_up_to_four_agents_are_named(self):
        for index in range(6):
            self._sidecar("b{0}".format(index) * 8,
                          description="slice {0}".format(index))
        reason = self._assert_denied(self._run(self._payload("git commit")))
        named = sum(1 for index in range(6)
                    if "b{0}".format(index) * 8 in reason)
        self.assertEqual(named, 4, reason)
        self.assertIn("6", reason)  # the total is still stated

    # -- when it must stay out of the way ---------------------------------

    def test_read_only_git_is_silent_even_with_a_pending_child(self):
        self._sidecar("c1111111111111111")
        for command in (
            "git status --short",
            "git diff --cached",
            "git log --oneline -5",
            "git show HEAD",
            "git branch",
            "git rev-list --count origin/dev..HEAD",
            "git rev-parse HEAD",
            "git ls-files",
            "git fetch origin",
        ):
            with self.subTest(command=command):
                self._assert_silent(self._run(self._payload(command)))

    def test_settled_child_no_longer_blocks(self):
        self._sidecar("c2222222222222222")
        self._settle("c2222222222222222")
        self._assert_silent(self._run(self._payload("git commit -m done")))

    def test_worktree_isolated_child_never_blocks(self):
        self._sidecar("c3333333333333333",
                      worktree_path="/tmp/worktrees/agent-c3333333333333333")
        self._assert_silent(self._run(self._payload("git commit -m x")))

    def test_no_children_at_all_is_silent(self):
        os.makedirs(self.subagents_dir, exist_ok=True)
        self._assert_silent(self._run(self._payload("git commit -m x")))

    def test_non_bash_tool_is_silent(self):
        self._sidecar("c4444444444444444")
        payload = self._payload("git commit -m x", tool_name="Edit")
        self._assert_silent(self._run(payload))

    def test_missing_subagents_dir_is_silent(self):
        self._assert_silent(self._run(self._payload("git commit -m x")))

    def test_no_transcript_path_is_silent(self):
        self._sidecar("c5555555555555555")
        payload = self._payload("git commit -m x")
        del payload["transcript_path"]
        self._assert_silent(self._run(payload))

    def test_malformed_stdin_is_silent(self):
        self._sidecar("c6666666666666666")
        self._assert_silent(self._run(None, stdin_text="{not json"))
        self._assert_silent(self._run(None, stdin_text=""))
        self._assert_silent(self._run(None, stdin_text="[1, 2, 3]"))

    def test_a_quoted_git_word_is_not_a_git_call(self):
        self._sidecar("c7777777777777777")
        self._assert_silent(self._run(self._payload(
            'echo "remember to git commit when the builder reports"')))
        # The second form needs real quote handling, not a whitespace split:
        # split on spaces, `"cleanup;` ends in a separator and the next token
        # reads as a command in position.
        self._assert_silent(self._run(self._payload(
            'echo "cleanup; git commit -m x"')))
        self._assert_silent(self._run(self._payload(
            "man git commit")))

    def test_unreadable_ledger_fails_open_rather_than_blocking(self):
        # An unreadable ledger makes the settled set unknowable, not empty.
        # Rendering it as empty would report every agent this session ever
        # started as live and deny on all of them; the hook stays silent.
        self._sidecar("c8888888888888888")
        self._settle("c8888888888888888")
        os.chmod(self.delegation_log, 0o000)
        self.addCleanup(os.chmod, self.delegation_log, 0o644)
        if os.access(self.delegation_log, os.R_OK):
            self.skipTest("running as a user that ignores file modes")
        self._assert_silent(self._run(self._payload("git commit -m x")))

    # -- when the caller is itself a subagent ------------------------------

    def test_a_delegating_subagent_is_guarded_against_its_own_children(self):
        # A manager holding live builders is the same shared-tree hazard as a
        # root session holding them.
        self._sidecar("f1111111111111111", agent_type="atelier:manager")
        self._sidecar("f2222222222222222", agent_type="atelier:builder")
        reason = self._assert_denied(self._run(self._payload(
            "git commit -m wave", agent_id="f1111111111111111")))
        self.assertIn("f2222222222222222", reason)
        # ...but it is never named as live to itself.
        self.assertNotIn("f1111111111111111", reason)

    def test_the_caller_alone_pending_is_silent(self):
        self._sidecar("f3333333333333333", agent_type="atelier:manager")
        self._assert_silent(self._run(self._payload(
            "git commit -m x", agent_id="f3333333333333333")))

    def test_a_caller_in_its_own_worktree_is_exempt(self):
        # It is not looking at this tree, so this tree's occupants are not its
        # problem — even though a non-isolated sibling is live here.
        self._sidecar("f4444444444444444", agent_type="atelier:builder",
                      worktree_path="/tmp/worktrees/agent-f4444444444444444")
        self._sidecar("f5555555555555555")
        self._assert_silent(self._run(self._payload(
            "git commit -m x", agent_id="f4444444444444444")))

    # -- the override ------------------------------------------------------

    def test_override_lets_the_command_through_with_a_system_message(self):
        self._sidecar("d1111111111111111", agent_type="atelier:scout")
        result = self._run(self._payload(
            'ATELIER_GIT_GUARD_OVERRIDE=1 git commit -m "unrelated work"'))
        payload = json.loads(result.stdout)
        self.assertNotIn("hookSpecificOutput", payload)
        message = payload["systemMessage"]
        self.assertIn("ATELIER_GIT_GUARD_OVERRIDE", message)
        self.assertIn("d1111111111111111", message)

    def test_override_without_pending_children_is_silent(self):
        os.makedirs(self.subagents_dir, exist_ok=True)
        self._assert_silent(self._run(self._payload(
            "ATELIER_GIT_GUARD_OVERRIDE=1 git commit -m x")))

    def test_override_after_the_git_word_does_not_count(self):
        self._sidecar("d2222222222222222")
        self._assert_denied(self._run(self._payload(
            "git commit -m ATELIER_GIT_GUARD_OVERRIDE=1")))

    def test_override_prefix_on_an_earlier_command_does_not_count(self):
        self._sidecar("d3333333333333333")
        self._assert_denied(self._run(self._payload(
            "ATELIER_GIT_GUARD_OVERRIDE=1 echo hi && git commit -m x")))

    def test_read_only_forms_of_mutating_verbs_are_silent(self):
        self._sidecar("d4444444444444444")
        for command in ("git stash list", "git stash show -p stash@{0}",
                        "git apply --check fix.diff", "git apply --stat fix.diff"):
            result = self._run(self._payload(command))
            self.assertEqual(result.returncode, 0, command)
            self.assertEqual(result.stdout, "", command)

    def test_write_forms_of_those_verbs_still_deny(self):
        self._sidecar("d5555555555555555")
        for command in ("git stash", "git stash pop", "git stash list && git stash",
                        "git apply fix.diff"):
            with self.subTest(command=command):
                self._assert_denied(self._run(self._payload(command)))

    # -- the ledger --------------------------------------------------------

    def test_deny_writes_one_ledger_row(self):
        self._sidecar("e1111111111111111")
        self._sidecar("e2222222222222222")
        self._run(self._payload("git pull"))
        rows = _read_rows(self.guard_log)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["stream"], "live-worker-git-guard")
        self.assertEqual(row["decision"], "deny")
        self.assertEqual(row["verb"], "pull")
        self.assertEqual(sorted(row["pending"]),
                         ["e1111111111111111", "e2222222222222222"])
        self.assertEqual(row["session_id"], self.session_id)

    def test_override_writes_one_ledger_row(self):
        self._sidecar("e3333333333333333")
        self._run(self._payload("ATELIER_GIT_GUARD_OVERRIDE=1 git merge dev"))
        rows = _read_rows(self.guard_log)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["decision"], "override")
        self.assertEqual(rows[0]["verb"], "merge")
        self.assertEqual(rows[0]["pending"], ["e3333333333333333"])


class SharedLedgerTests(unittest.TestCase):
    """The guard reads the ledger subagent-telemetry writes.

    Each hook binds its own stream name as a literal (the agentlog gate wants
    it bound where it is claimed), so `_lib/pending.py` and the telemetry hook
    hold two copies of one string. Nothing else notices if they drift: the
    guard would read an empty ledger, see every delegation as pending, and deny
    forever.
    """

    def _bound(self, name):
        path = os.path.join(HOOKS_ROOT, "subagent-telemetry", "hook.py")
        with open(path, encoding="utf-8") as fh:
            found = re.findall(
                r'^{0} = "([^"]+)"'.format(name), fh.read(), re.M)
        self.assertEqual(len(found), 1, "{0} bound {1} time(s)".format(
            name, len(found)))
        return found[0]

    def test_stream_the_guard_reads_is_the_one_telemetry_writes(self):
        self.assertEqual(self._bound("LOG_STREAM"), pending.LEDGER_STREAM)

    def test_path_override_the_guard_reads_is_the_one_telemetry_writes(self):
        self.assertEqual(self._bound("LOG_PATH_ENV"), pending.LEDGER_PATH_ENV)


if __name__ == "__main__":
    unittest.main()
