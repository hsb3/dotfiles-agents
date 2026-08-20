"""Tests for primitives-core/hooks/delegation-watermark/hook.py.

Runs the hook as a subprocess (its real invocation shape: JSON on stdin, JSON
line on stdout, env-configured knobs) against generated JSONL transcripts.
Stdlib-only; fixtures build into a tempdir per test.
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
    "delegation-watermark", "hook.py",
)

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "primitives-core", "hooks", "_lib")
)
import agentlog  # noqa: E402  (path must be primed before this import)

_SEQ = itertools.count()


def _session_id():
    return f"test-session-{next(_SEQ)}"


def _record(tool_name, sidechain=False):
    rec = {
        "type": "assistant",
        "message": {"content": [{"type": "tool_use", "name": tool_name, "input": {}}]},
    }
    if sidechain:
        rec["isSidechain"] = True
    return rec


def _write_transcript(path, records):
    with open(path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


def _sandbox_env(state_dir, log_path):
    """Environment for one hook run, with the partitioned log root contained.

    HOME and XDG_DATA_HOME are set even though LOG_PATH is: a run that ever
    loses its override must not append synthetic rows to the real
    ~/.local/share/agent-logs ledger, and expanduser("~") falls back to the
    passwd entry when HOME is merely unset. The sandbox is derived from the
    caller's log_path, which always lives in the test's own tempdir.
    """
    sandbox = os.path.join(os.path.dirname(os.path.dirname(log_path)), "sandbox")
    return {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.path.join(sandbox, "home"),
        "XDG_DATA_HOME": os.path.join(sandbox, "xdg"),
        "DELEGATION_WATERMARK_STATE_DIR": state_dir,
        "DELEGATION_WATERMARK_LOG_PATH": log_path,
        "DELEGATION_WATERMARK_SOFT": "25",
        "DELEGATION_WATERMARK_REFIRE_EVERY": "15",
    }


def _run_hook(payload, state_dir, log_path, extra_env=None):
    env = _sandbox_env(state_dir, log_path)
    # CLAUDE_PROJECT_DIR deliberately absent -> no scatter if LOG_PATH override
    # were ever missing.
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        [sys.executable, HOOK_PATH],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    return result


def _last_log_row(log_path):
    with open(log_path, encoding="utf-8") as fh:
        lines = [ln for ln in fh.read().splitlines() if ln.strip()]
    return json.loads(lines[-1])


class DelegationWatermarkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = os.path.join(self.tmp.name, "cwd")
        self.state_dir = os.path.join(self.tmp.name, "state")
        self.log_path = os.path.join(self.tmp.name, "logs", "delegation-watermark.jsonl")
        os.makedirs(self.cwd, exist_ok=True)

    def _payload(self, transcript_records, session_id=None, agent_id=None):
        session_id = session_id or _session_id()
        transcript_path = os.path.join(self.tmp.name, f"{session_id}.jsonl")
        _write_transcript(transcript_path, transcript_records)
        payload = {
            "session_id": session_id,
            "transcript_path": transcript_path,
            "cwd": self.cwd,
            "tool_name": "Edit",
        }
        if agent_id:
            payload["agent_id"] = agent_id
        return payload

    def test_fires_at_watermark(self):
        payload = self._payload([_record("Edit") for _ in range(30)])
        result = _run_hook(payload, self.state_dir, self.log_path)
        self.assertEqual(result.returncode, 0)
        self.assertIn("hookSpecificOutput", result.stdout)
        self.assertIn("PostToolUse", result.stdout)

    def test_dispatch_resets_streak(self):
        records = [_record("Edit") for _ in range(30)]
        records.append(_record("Task"))
        records += [_record("Edit") for _ in range(5)]
        payload = self._payload(records)
        result = _run_hook(payload, self.state_dir, self.log_path)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_sidechain_ignored(self):
        records = [_record("Edit", sidechain=True) for _ in range(30)]
        payload = self._payload(records)
        result = _run_hook(payload, self.state_dir, self.log_path)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_bookkeeping_neither_counts_nor_resets(self):
        records = [_record("TodoWrite") for _ in range(30)]
        records += [_record("Edit") for _ in range(3)]
        payload = self._payload(records)
        result = _run_hook(payload, self.state_dir, self.log_path)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_subagent_guard(self):
        records = [_record("Edit") for _ in range(30)]
        payload = self._payload(records, agent_id="worker-1")
        result = _run_hook(payload, self.state_dir, self.log_path)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")
        self.assertFalse(os.path.exists(self.state_dir))
        self.assertFalse(os.path.exists(self.log_path))

    def test_anti_nag_then_refire_on_growth(self):
        session_id = _session_id()
        records_30 = [_record("Edit") for _ in range(30)]

        payload_1 = self._payload(records_30, session_id=session_id)
        result_1 = _run_hook(payload_1, self.state_dir, self.log_path)
        self.assertIn("hookSpecificOutput", result_1.stdout)

        payload_2 = self._payload(records_30, session_id=session_id)
        result_2 = _run_hook(payload_2, self.state_dir, self.log_path)
        self.assertEqual(result_2.stdout.strip(), "")

        records_45 = [_record("Edit") for _ in range(45)]
        payload_3 = self._payload(records_45, session_id=session_id)
        result_3 = _run_hook(payload_3, self.state_dir, self.log_path)
        self.assertIn("hookSpecificOutput", result_3.stdout)

    def test_fail_open_on_garbage_stdin(self):
        env = _sandbox_env(self.state_dir, self.log_path)
        result = subprocess.run(
            [sys.executable, HOOK_PATH],
            input="not json",
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_fail_open_on_missing_transcript(self):
        session_id = _session_id()
        payload = {
            "session_id": session_id,
            "transcript_path": os.path.join(self.tmp.name, "does-not-exist.jsonl"),
            "cwd": self.cwd,
            "tool_name": "Edit",
        }
        result = _run_hook(payload, self.state_dir, self.log_path)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")
        row = _last_log_row(self.log_path)
        self.assertIn("error", row)

    def test_no_stray_writes_outside_configured_paths(self):
        # Fixture layout keeps the payload cwd empty and separate from the
        # transcript/state/log paths (all elsewhere under self.tmp.name), so
        # any write landing in cwd is necessarily a stray write by the hook.
        payload = self._payload([_record("Edit") for _ in range(30)])
        result = _run_hook(payload, self.state_dir, self.log_path)
        self.assertIn("hookSpecificOutput", result.stdout)

        cwd_contents = []
        for root, _dirs, files in os.walk(self.cwd):
            cwd_contents.extend(os.path.join(root, f) for f in files)
        self.assertEqual(cwd_contents, [])

    def test_ledger_row_shape(self):
        payload = self._payload([_record("Edit") for _ in range(30)])
        result = _run_hook(payload, self.state_dir, self.log_path)
        self.assertIn("hookSpecificOutput", result.stdout)
        row = _last_log_row(self.log_path)
        self.assertIn("streak", row)
        self.assertIn("dispatches", row)
        self.assertIn("delegable_total", row)
        self.assertEqual(row["fired"], True)


if __name__ == "__main__":
    unittest.main()
