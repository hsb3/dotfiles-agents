"""Real Codex token_count fields become replayable delta observations."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "primitives-core/hooks/_lib"))
import codex_usage


class UsageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "rollout.jsonl"

    def write(self, *rows):
        self.path.write_text("\n".join(json.dumps(row) for row in rows))

    def count(self, total, model=None):
        row = {"type": "event_msg", "timestamp": "2026-09-10T00:00:01Z", "payload": {"type": "token_count", "info": {"total_token_usage": {
            "input_tokens": max(20, total - 40), "cached_input_tokens": max(0, total - 60),
            "output_tokens": 40, "reasoning_output_tokens": 10, "total_tokens": total}}}}
        return ([{"type": "turn_context", "payload": {"model": model, "effort": "high"}}] if model else []) + [row]

    def test_real_fields_delta_reset_and_model_segments(self):
        self.write({"type": "session_meta", "payload": {"id": "child", "session_id": "root",
                    "parent_thread_id": "manager", "agent_role": "atelier-builder",
                    "thread_source": "subagent", "timestamp": "2026-09-10T00:00:00Z"}},
                   *self.count(100, "gpt-a"), *self.count(200, "gpt-b"), *self.count(50, "gpt-b"))
        rows = codex_usage.events(self.path, {"session_id": "root", "agent_id": "child",
                                               "repo": "/source", "cwd": "/tree"})
        observed = [row for row in rows if row["counter_state"] == "observed"]
        self.assertEqual([row["tokens"]["total"] for row in observed], [100, 100, 50])
        self.assertEqual([row["model"] for row in observed], ["gpt-a", "gpt-b", "gpt-b"])
        self.assertEqual(rows[-2]["counter_state"], "reset")
        self.assertEqual((observed[0]["native_id"], observed[0]["parent_id"], observed[0]["role"],
                          observed[0]["source_repo"], observed[0]["effort"]), ("child", "manager",
                          "atelier-builder", "/source", "high"))

    def test_ids_do_not_collapse_siblings_or_errors(self):
        self.write(*self.count(100, "gpt"))
        left = codex_usage.events(self.path, {"session_id": "root", "agent_id": "left"})[-1]
        right = codex_usage.events(self.path, {"session_id": "root", "agent_id": "right"})[-1]
        self.assertNotEqual(left["observation_id"], right["observation_id"])
        self.path.write_text("not json")
        self.assertEqual(codex_usage.events(self.path, {"session_id": "root"})[0]["counter_state"], "malformed-json")

    def test_missing_and_oserror_are_explicit(self):
        self.assertEqual(codex_usage.events(None, {"session_id": "root"})[0]["counter_state"], "error")
        self.write({"type": "session_meta", "payload": {"id": "root"}})
        self.assertEqual(codex_usage.events(self.path, {"session_id": "root"})[0]["counter_state"], "missing")


if __name__ == "__main__":
    unittest.main()
