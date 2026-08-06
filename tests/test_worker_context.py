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


if __name__ == "__main__":
    unittest.main()
