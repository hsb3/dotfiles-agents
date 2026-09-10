"""Codex v2 usage observations are cumulative snapshots, never summed."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import os

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "primitives-core/hooks/_lib"))
import codex_usage
import agentlog


class CodexUsageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "rollout.jsonl"

    def write(self, *rows):
        self.path.write_text("\n".join(json.dumps(row) for row in rows))

    def count(self, total=100, model="gpt-6-astra", **usage):
        values = {"input_tokens": 60, "cached_input_tokens": 20,
                  "output_tokens": 40, "reasoning_tokens": 10, "total_tokens": total}
        values.update(usage)
        return {"type": "event_msg", "payload": {"type": "token_count", "info": {
            "total_token_usage": values, "model_context_window": 258400}}}

    def test_cumulative_snapshot_and_replay_have_exact_totals(self):
        self.write({"type": "session_meta", "payload": {"id": "root", "timestamp": "2026-09-10T00:00:00Z"}},
                   {"type": "turn_context", "payload": {"model": "gpt-6-astra"}},
                   self.count(), self.count())
        row = codex_usage.observe(self.path, {"session_id": "root", "cwd": "/repo"}, "root")
        self.assertEqual(row["tokens"], {"input": 60, "cached_input": 20, "output": 40,
                                         "reasoning": 10, "total": 100})
        self.assertEqual(row["observation_id"], codex_usage.observe(
            self.path, {"session_id": "root", "cwd": "/repo"}, "root")["observation_id"])
        self.assertEqual(row["model"], "gpt-6-astra")
        self.assertEqual(row["kind"], "cumulative")

    def test_missing_malformed_and_reset_are_explicit(self):
        self.write(self.count(100), {"type": "event_msg", "payload": {"type": "token_count", "info": {
            "total_token_usage": {"total_tokens": 50}}}})
        row = codex_usage.observe(self.path, {"session_id": "root"}, "root")
        self.assertEqual(row["counter_state"], "reset")
        self.assertIsNone(row["tokens"])
        self.path.write_text("not json")
        self.assertEqual(codex_usage.observe(self.path, {"session_id": "root"}, "root")["counter_state"],
                         "missing")
        self.write({"type": "event_msg", "payload": {"type": "token_count", "info": {}}})
        self.assertEqual(codex_usage.observe(self.path, {"session_id": "root"}, "root")["counter_state"],
                         "malformed")

    def test_child_dimensions_and_future_schema_rejected(self):
        self.write({"v": 99, "type": "event_msg", "payload": {"type": "token_count", "info": {}}})
        row = codex_usage.observe(self.path, {"session_id": "parent", "agent_id": "child",
                                               "agent_type": "atelier-builder", "cwd": "/tree",
                                               "original_cwd": "/source"}, "child")
        self.assertEqual((row["counter_state"], row["parent_id"], row["role"],
                          row["source_repo"], row["effective_cwd"]),
                         ("unsupported-future-schema", "parent", "atelier-builder", "/source", "/tree"))

    def test_second_ingest_does_not_append_duplicate(self):
        self.write(self.count())
        old = os.environ.get("XDG_DATA_HOME")
        os.environ["XDG_DATA_HOME"] = self.tmp.name
        self.addCleanup(lambda: os.environ.__setitem__("XDG_DATA_HOME", old) if old else os.environ.pop("XDG_DATA_HOME", None))
        row = codex_usage.observe(self.path, {"session_id": "root"}, "root")
        agentlog.append_once("codex-usage", row, row["observation_id"], version=2)
        agentlog.append_once("codex-usage", row, row["observation_id"], version=2)
        path = Path(agentlog.stream_path("codex-usage"))
        self.assertEqual(len(path.read_text().splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
