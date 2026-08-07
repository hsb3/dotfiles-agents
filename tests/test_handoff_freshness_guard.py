"""Tests for primitives-core/hooks/handoff-freshness-guard/hook.py.

Runs the hook as a subprocess (its real invocation shape: JSON on stdin, a
JSON line on stdout only on block or non-blocking guidance) against a
hand-written .claude/atelier.local.md activation file and candidate/override
handoff files. Stdlib-only; fixtures build into a tempdir per test, and the
environment passed to the subprocess is built from scratch with only PATH
inherited.
"""

import itertools
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

HOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "primitives-core", "hooks",
    "handoff-freshness-guard", "hook.py",
)

_SEQ = itertools.count()

STALE_SECONDS = 60 * 60  # well past the 30-minute default freshness window


def _session_id():
    return f"handoff-guard-session-{next(_SEQ)}"


class HandoffFreshnessGuardOverrideTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = os.path.join(self.tmp.name, "cwd")
        os.makedirs(self.cwd, exist_ok=True)
        self.log_path = os.path.join(self.tmp.name, "logs", "handoff-guard.jsonl")

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

    def _write_file(self, relpath, content="content\n", stale=False):
        full = os.path.join(self.cwd, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
        if stale:
            old = time.time() - STALE_SECONDS
            os.utime(full, (old, old))
        return full

    def _payload(self, trigger="manual", session_id=None):
        return {
            "session_id": session_id or _session_id(),
            "hook_event_name": "PreCompact",
            "trigger": trigger,
            "cwd": self.cwd,
        }

    def _run_hook(self, payload):
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HANDOFF_GUARD_LOG_PATH": self.log_path,
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

    def _assert_blocked(self, result):
        self.assertEqual(result.returncode, 0)
        body = json.loads(result.stdout)
        self.assertEqual(body["decision"], "block")
        return body

    # -- tests -----------------------------------------------------------

    def test_override_absent_missing_trio_blocks_manual_with_exact_message(self):
        """No activation file, no candidates at all: byte-identical to
        pre-override behavior -- blocks manual compaction naming the
        standard trio."""
        result = self._run_hook(self._payload(trigger="manual"))
        body = self._assert_blocked(result)
        self.assertEqual(
            body["reason"],
            "No handoff file found (_meta/HANDOFF.md, HANDOFF.md, or "
            ".claude/HANDOFF.md) — run /handoff first, then /compact.",
        )

    def test_override_absent_missing_trio_auto_never_blocks_exact_message(self):
        result = self._run_hook(self._payload(trigger="auto"))
        self.assertEqual(result.returncode, 0)
        body = json.loads(result.stdout)
        self.assertNotIn("decision", body)
        self.assertEqual(
            body["systemMessage"],
            "Auto-compaction is proceeding with a stale/missing handoff "
            "file. Run /handoff soon to avoid losing externalized state "
            "on the next compaction.",
        )

    def test_override_existing_file_wins_over_stale_standard_candidate(self):
        self._write_file("_meta/HANDOFF.md", stale=True)  # trio: stale, would block alone
        self._write_file("docs/HANDOFF.md")  # override: fresh
        self._write_activation(handoff="docs/HANDOFF.md")
        result = self._run_hook(self._payload(trigger="manual"))
        self._assert_silent(result)  # fresh override wins -> allowed silently

    def test_override_nonexistent_path_does_not_fall_back(self):
        self._write_file("HANDOFF.md")  # fresh trio candidate, would allow if searched
        self._write_activation(handoff="docs/HANDOFF.md")  # never created
        result = self._run_hook(self._payload(trigger="manual"))
        body = self._assert_blocked(result)
        self.assertIn("docs/HANDOFF.md", body["reason"])
        self.assertNotIn("_meta/HANDOFF.md, HANDOFF.md", body["reason"])

    def test_override_outside_project_root_falls_back(self):
        self._write_file("HANDOFF.md")  # fresh trio candidate
        self._write_activation(handoff="/etc/hosts")  # exists, outside project root
        result = self._run_hook(self._payload(trigger="manual"))
        self._assert_silent(result)  # falls back to trio search, which is fresh

    def test_unparseable_activation_falls_back(self):
        self._write_file("HANDOFF.md")
        self._write_activation(raw_text="not even yaml, just noise\n")
        result = self._run_hook(self._payload(trigger="manual"))
        self._assert_silent(result)

    def test_activation_with_other_keys_not_handoff_falls_back(self):
        self._write_file("HANDOFF.md")
        self._write_activation(raw_text="---\nenforce: strict\n---\n")
        result = self._run_hook(self._payload(trigger="manual"))
        self._assert_silent(result)

    def test_malformed_stdin_fails_open(self):
        result = subprocess.run(
            [sys.executable, HOOK_PATH],
            input="not json",
            capture_output=True,
            text=True,
            env={"PATH": os.environ.get("PATH", ""), "HANDOFF_GUARD_LOG_PATH": self.log_path},
            timeout=30,
        )
        self._assert_silent(result)


if __name__ == "__main__":
    unittest.main()
