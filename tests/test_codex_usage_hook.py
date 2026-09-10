"""The telemetry hook keeps v1 lifecycle behavior while emitting Codex v2 usage."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "primitives-core/hooks/subagent-telemetry/hook.py"


def load_hook():
    spec = importlib.util.spec_from_file_location("usage_hook_test", HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rollout(identity, total):
    return "\n".join(json.dumps(row) for row in [
        {"type": "session_meta", "payload": {"id": identity, "session_id": "root",
         "timestamp": "2026-09-10T00:00:00Z"}},
        {"type": "event_msg", "timestamp": "2026-09-10T00:00:01Z", "payload": {
            "type": "token_count", "info": {
                "total_token_usage": {"input_tokens": total - 40, "cached_input_tokens": 0,
                    "output_tokens": 40, "reasoning_output_tokens": 10, "total_tokens": total},
                "last_token_usage": {"total_tokens": total},
                "model_context_window": 258400}}}])


class UsageHookTests(unittest.TestCase):
    def test_root_and_child_use_their_own_native_rollouts_and_keep_v1(self):
        module = load_hook()
        with tempfile.TemporaryDirectory() as directory:
            root, child = Path(directory) / "root.jsonl", Path(directory) / "child.jsonl"
            root.write_text(rollout("root", 999))
            child.write_text(rollout("child", 100))
            record = {"session_id": "root", "agent_id": "child", "agent_type": "atelier-builder",
                      "transcript_path": str(child), "repo": "/repo"}
            statuses, rows = [], []
            workers = SimpleNamespace(lookup=lambda payload: record, records=lambda payload: [],
                                      set_status=lambda payload, value: statuses.append(value))
            def append(stream, row, *args):
                rows.append((stream, row, args))
            with patch.dict(sys.modules, codex_workers=workers), \
                 patch.object(module.agentlog, "append", side_effect=append):
                module._codex_stop({"session_id": "root", "agent_id": "child",
                                    "cwd": directory, "transcript_path": str(root)})
                module._codex_stop({"session_id": "root", "cwd": directory,
                                    "transcript_path": str(root)})
            child_v2 = [entry for entry in rows if entry[0] == "codex-usage" and entry[1]["native_id"] == "child"]
            root_v2 = [entry for entry in rows if entry[0] == "codex-usage" and entry[1]["native_id"] == "root"]
            self.assertEqual(child_v2[-1][1]["tokens"]["total"], 100)
            self.assertEqual(root_v2[-1][1]["tokens"]["total"], 999)
            self.assertEqual(child_v2[-1][2][-1], 2)
            v1 = [entry for entry in rows if entry[0] == "delegation"]
            self.assertEqual(v1[-1][2][-1], module.LOG_PATH_ENV)
            self.assertEqual(statuses, ["stopped"])

    def test_usage_error_does_not_skip_v1_or_status(self):
        module = load_hook()
        record = {"session_id": "root", "agent_id": "child", "agent_type": "atelier-builder",
                  "transcript_path": "/missing"}
        rows, statuses = [], []
        workers = SimpleNamespace(lookup=lambda payload: record, records=lambda payload: [],
                                  set_status=lambda payload, value: statuses.append(value))
        with patch.dict(sys.modules, codex_workers=workers), \
             patch.object(module.codex_usage, "events", side_effect=OSError("bad usage")), \
             patch.object(module.agentlog, "append", side_effect=lambda stream, row, *args: rows.append(stream)):
            module._codex_stop({"session_id": "root", "agent_id": "child", "cwd": "/"})
        self.assertIn("delegation", rows)
        self.assertEqual(statuses, ["stopped"])


if __name__ == "__main__":
    unittest.main()
