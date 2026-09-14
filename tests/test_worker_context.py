"""Tests for primitives-core/hooks/worker-context/hook.py.

Runs the hook as a subprocess (its real invocation shape: JSON on stdin, a
JSON line on stdout only when enforcement is active) against a hand-written
.claude/atelier.local.md activation file. Stdlib-only; fixtures build into a
tempdir per test, and the environment passed to the subprocess is built from
scratch with only PATH inherited.
"""

import itertools
import json
import os
import subprocess
import sys
import tempfile
import unittest

# Sibling helper: `tests/` is on sys.path under `discover -s tests` but not
# under `-t .`, so prime the path the same way the hooks prime `_lib`.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from worktree_fixture import make_worktree, require_git  # noqa: E402

HOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "primitives-core", "hooks",
    "worker-context", "hook.py",
)

_SEQ = itertools.count()


def _session_id():
    return f"worker-context-session-{next(_SEQ)}"


class WorkerContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = os.path.join(self.tmp.name, "cwd")
        os.makedirs(self.cwd, exist_ok=True)

    # -- fixtures ------------------------------------------------------

    def _write_activation(self, mode=None, raw_text=None, project_dir=None):
        project_dir = project_dir or self.cwd
        claude_dir = os.path.join(project_dir, ".claude")
        os.makedirs(claude_dir, exist_ok=True)
        path = os.path.join(claude_dir, "atelier.local.md")
        if raw_text is None:
            lines = ["---"]
            if mode is not None:
                lines.append("enforce: {0}".format(mode))
            lines.append("---")
            raw_text = "\n".join(lines) + "\n"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(raw_text)
        return path

    def _payload(self, cwd=None, agent_id="agent-1", session_id=None):
        return {
            "session_id": session_id or _session_id(),
            "hook_event_name": "SubagentStart",
            "agent_id": agent_id,
            "agent_type": "builder",
            "cwd": self.cwd if cwd is None else cwd,
        }

    def _run_hook(self, stdin_text):
        env = {"PATH": os.environ.get("PATH", "")}
        return subprocess.run(
            [sys.executable, HOOK_PATH],
            input=stdin_text,
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )

    # -- tests -----------------------------------------------------------

    def test_strict_injects_tool_layer_clause(self):
        self._write_activation(mode="strict")
        result = self._run_hook(json.dumps(self._payload()))
        self.assertEqual(result.returncode, 0)
        body = json.loads(result.stdout)
        hso = body["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], "SubagentStart")
        self.assertIn("blocked at the tool layer", hso["additionalContext"])

    def test_advisory_injects_without_tool_layer_clause(self):
        self._write_activation(mode="advisory")
        result = self._run_hook(json.dumps(self._payload()))
        self.assertEqual(result.returncode, 0)
        body = json.loads(result.stdout)
        context = body["hookSpecificOutput"]["additionalContext"]
        self.assertTrue(context)
        self.assertNotIn("blocked at the tool layer", context)

    def test_covenant_clause_2_is_worktree_not_no_mutating_git(self):
        self._write_activation(mode="advisory")
        result = self._run_hook(json.dumps(self._payload()))
        self.assertEqual(result.returncode, 0)
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn(
            "(2) Work in your own worktree and commit there as you go — that "
            "branch is yours. Never push, merge, or touch any branch, worktree, "
            "or repo state outside it; integration belongs to the orchestrating "
            "session.",
            context,
        )
        self.assertNotIn("Never run mutating git", context)

    def test_off_is_silent(self):
        self._write_activation(mode="off")
        result = self._run_hook(json.dumps(self._payload()))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_activation_absent_is_silent(self):
        bare_cwd = os.path.join(self.tmp.name, "bare")
        os.makedirs(bare_cwd, exist_ok=True)
        result = self._run_hook(json.dumps(self._payload(cwd=bare_cwd)))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_garbage_activation_fails_open(self):
        self._write_activation(raw_text="not even yaml, just noise\n")
        result = self._run_hook(json.dumps(self._payload()))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_malformed_stdin_fails_open_and_writes_nothing(self):
        result = self._run_hook("not json")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

        found = []
        for root, _dirs, files in os.walk(self.tmp.name):
            found.extend(os.path.join(root, f) for f in files)
        self.assertEqual(found, [])

    # -- worktree resolution ---------------------------------------------

    def test_linked_worktree_follows_main_checkout_activation(self):
        """A worker started with its cwd in a linked worktree still gets the
        covenant the main checkout armed."""
        require_git()
        base = os.path.join(self.tmp.name, "repo")
        os.makedirs(base, exist_ok=True)
        _main_dir, worktree_dir = make_worktree(
            base, files={".claude/atelier.local.md": "---\nenforce: strict\n---\n"},
        )
        result = self._run_hook(json.dumps(self._payload(cwd=worktree_dir)))
        self.assertEqual(result.returncode, 0)
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("blocked at the tool layer", context)

    def test_worktrees_own_tracked_activation_wins(self):
        """Resolution is lazy: a tracked activation file in the worktree is
        read at its committed version, not replaced by the main checkout's."""
        require_git()
        base = os.path.join(self.tmp.name, "repo")
        os.makedirs(base, exist_ok=True)
        main_dir, worktree_dir = make_worktree(
            base, tracked={".claude/atelier.local.md": "---\nenforce: off\n---\n"},
        )
        self._write_activation(mode="strict", project_dir=main_dir)
        result = self._run_hook(json.dumps(self._payload(cwd=worktree_dir)))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
