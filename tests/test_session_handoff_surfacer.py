"""Tests for primitives-core/hooks/session-handoff-surfacer/hook.py.

Runs the hook as a subprocess (its real invocation shape: JSON on stdin, a
JSON line on stdout only when surfacing) against a hand-written
.claude/atelier.local.md activation file and candidate handoff files.
Stdlib-only; fixtures build into a tempdir per test, and the environment
passed to the subprocess is built from scratch with only PATH inherited.
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
    "session-handoff-surfacer", "hook.py",
)

_SEQ = itertools.count()


def _session_id():
    return f"handoff-surfacer-session-{next(_SEQ)}"


class SessionHandoffSurfacerOverrideTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = os.path.join(self.tmp.name, "cwd")
        os.makedirs(self.cwd, exist_ok=True)
        self.log_path = os.path.join(self.tmp.name, "logs", "handoff-surfacer.jsonl")

    # -- fixtures ------------------------------------------------------

    def _write_activation(self, raw_text=None, handoff=None):
        claude_dir = os.path.join(self.cwd, ".claude")
        os.makedirs(claude_dir, exist_ok=True)
        path = os.path.join(claude_dir, "atelier.local.md")
        if raw_text is None:
            lines = ["---"]
            if handoff is not None:
                lines.append("handoff: {0}".format(handoff))
            lines.append("---")
            raw_text = "\n".join(lines) + "\n"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(raw_text)
        return path

    def _write_file(self, relpath, content="content\n"):
        full = os.path.join(self.cwd, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
        return full

    def _payload(self, source="startup", session_id=None):
        return {
            "session_id": session_id or _session_id(),
            "hook_event_name": "SessionStart",
            "source": source,
            "cwd": self.cwd,
        }

    def _run_hook(self, payload):
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HANDOFF_SURFACER_LOG_PATH": self.log_path,
        }
        return subprocess.run(
            [sys.executable, HOOK_PATH],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )

    def _assert_silent(self, result):
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def _surfaced_relpath(self, result):
        self.assertEqual(result.returncode, 0)
        body = json.loads(result.stdout)
        msg = body["systemMessage"]
        # "atelier: surfaced project handoff (<relpath>)."
        return msg.split("(", 1)[1].rsplit(")", 1)[0]

    # -- tests -----------------------------------------------------------

    def test_override_absent_standard_search_unaffected(self):
        """No activation file at all: byte-identical to pre-override
        behavior -- the standard candidate-path search finds HANDOFF.md."""
        self._write_file("HANDOFF.md", "root handoff\n")
        result = self._run_hook(self._payload())
        self.assertEqual(self._surfaced_relpath(result), "HANDOFF.md")
        body = json.loads(result.stdout)
        self.assertEqual(
            body["hookSpecificOutput"]["additionalContext"],
            "A project handoff exists at HANDOFF.md — read it before starting. "
            "First lines:\nroot handoff",
        )

    def test_override_existing_file_wins_over_standard_candidate(self):
        self._write_file("_meta/HANDOFF.md", "meta handoff\n")  # highest-precedence trio candidate
        self._write_file("docs/HANDOFF.md", "override handoff\n")
        self._write_activation(handoff="docs/HANDOFF.md")
        result = self._run_hook(self._payload())
        self.assertEqual(self._surfaced_relpath(result), "docs/HANDOFF.md")
        self.assertIn("override handoff", result.stdout)

    def test_override_nonexistent_path_does_not_fall_back(self):
        self._write_file("HANDOFF.md", "root handoff\n")  # would be found by standard search
        self._write_activation(handoff="docs/HANDOFF.md")  # never created
        result = self._run_hook(self._payload())
        self._assert_silent(result)

    def test_override_outside_project_root_falls_back(self):
        self._write_file("HANDOFF.md", "root handoff\n")
        self._write_activation(handoff="/etc/hosts")  # exists, but outside project root
        result = self._run_hook(self._payload())
        self.assertEqual(self._surfaced_relpath(result), "HANDOFF.md")

    def test_unparseable_activation_falls_back(self):
        self._write_file("HANDOFF.md", "root handoff\n")
        self._write_activation(raw_text="not even yaml, just noise\n")
        result = self._run_hook(self._payload())
        self.assertEqual(self._surfaced_relpath(result), "HANDOFF.md")

    def test_activation_with_other_keys_not_handoff_falls_back(self):
        self._write_file("HANDOFF.md", "root handoff\n")
        self._write_activation(raw_text="---\nenforce: strict\n---\n")
        result = self._run_hook(self._payload())
        self.assertEqual(self._surfaced_relpath(result), "HANDOFF.md")

    def test_malformed_stdin_fails_open(self):
        result = subprocess.run(
            [sys.executable, HOOK_PATH],
            input="not json",
            capture_output=True,
            text=True,
            env={"PATH": os.environ.get("PATH", ""), "HANDOFF_SURFACER_LOG_PATH": self.log_path},
            timeout=30,
        )
        self._assert_silent(result)


if __name__ == "__main__":
    unittest.main()
