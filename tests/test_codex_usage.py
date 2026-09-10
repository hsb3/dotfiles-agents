"""Real Codex token_count fields become replayable delta observations."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

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
            "input_tokens": total - 40, "cached_input_tokens": max(0, total - 60),
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
        self.assertEqual(codex_usage.events(self.path, {"session_id": "root"})[0]["counter_state"], "pending")

    def test_future_and_inherited_histories_never_become_observed(self):
        self.write({"type": "session_meta", "payload": {"id": "parent", "timestamp": "2026-09-10T00:00:00Z"}},
                   *self.count(100), {"v": 3}, *self.count(200))
        rows = codex_usage.events(self.path, {"session_id": "root", "agent_id": "child"})
        self.assertIn("unsupported-future-schema", [row["counter_state"] for row in rows])
        self.assertNotIn("observed", [row["counter_state"] for row in rows])

    def test_counter_before_native_start_is_not_billed(self):
        counter = self.count(100)[0]
        counter["timestamp"] = "2026-09-09T23:59:59Z"
        self.write({"type": "session_meta", "payload": {"id": "root", "timestamp": "2026-09-10T00:00:00Z"}}, counter)
        self.assertEqual(codex_usage.events(self.path, {"session_id": "root"})[-1]["counter_state"],
                         "inherited-baseline-unknown")

    def test_pre_start_baseline_is_quarantined_but_next_delta_is_exact(self):
        first, second = self.count(100)[0], self.count(120)[0]
        first["timestamp"], second["timestamp"] = "2026-09-10T00:00:01Z", "2026-09-10T00:00:11Z"
        self.write(first, {"type": "session_meta", "payload": {"id": "root", "timestamp": "2026-09-10T00:00:10Z"}}, second)
        rows = codex_usage.events(self.path, {"session_id": "root"})
        self.assertEqual(rows[0]["counter_state"], "inherited-baseline-unknown")
        self.assertEqual(rows[-1]["tokens"]["total"], 20)

    def test_late_conflicting_metadata_scrubs_earlier_counter(self):
        self.write({"type": "session_meta", "payload": {"id": "root"}},
                   *self.count(100), {"type": "session_meta", "payload": {"id": "other"}}, *self.count(200))
        self.assertNotIn("observed", [row["counter_state"] for row in
                                      codex_usage.events(self.path, {"session_id": "root"})])

    def test_missing_metadata_marks_all_counters_unknown(self):
        self.write(*self.count(100))
        self.assertEqual(codex_usage.events(self.path, {"session_id": "root"})[-1]["counter_state"],
                         "inherited-baseline-unknown")

    def test_late_fork_marker_quarantines_earlier_counters(self):
        self.write(*self.count(100), {"type": "session_meta", "payload": {
            "id": "root", "forked_from_id": "parent"}})
        rows = codex_usage.events(self.path, {"session_id": "root"})
        self.assertTrue(all(row["tokens"] is None for row in rows))

    def test_unknown_record_invalidates_model_attribution(self):
        for unknown in ({"v": 3, "type": "turn_context", "payload": {"model": "gpt-b"}}, [],
                        {"type": "event_msg", "payload": {"type": "token_count", "info": {}}}):
            self.write({"type": "session_meta", "payload": {"id": "root"}},
                       *self.count(100, "gpt-a"), unknown, *self.count(120))
            row = codex_usage.events(self.path, {"session_id": "root"})[-1]
            self.assertEqual(row["tokens"]["total"], 20)
            self.assertIsNone(row["model"])
            self.assertIsNone(row["effort"])

    def test_partial_counter_reset_does_not_rebill_lifetime_total(self):
        counters = [self.count(total)[0] for total in (100, 120, 140)]
        for row, cached in zip(counters, (40, 20, 30)):
            row["payload"]["info"]["total_token_usage"]["cached_input_tokens"] = cached
        self.write({"type": "session_meta", "payload": {"id": "root"}}, *counters)
        rows = codex_usage.events(self.path, {"session_id": "root"})
        self.assertEqual([r["tokens"]["total"] for r in rows if r["tokens"]], [100, 20])
        self.assertIn("reset", [r["counter_state"] for r in rows])

    def test_naive_timestamp_has_unknown_not_negative_timing(self):
        counter = self.count(100)[0]
        counter["timestamp"] = "2026-09-10T00:00:01"
        self.write({"type": "session_meta", "payload": {"id": "root", "timestamp": "2026-09-10T00:00:00Z"}}, counter)
        row = codex_usage.events(self.path, {"session_id": "root"})[-1]
        self.assertEqual(row["counter_state"], "observed")
        self.assertIsNone(row["timing"]["lifetime_ms"])

    def test_repo_is_resolved_once_and_fake_profile_is_not_claimed(self):
        self.write({"type": "session_meta", "payload": {"id": "root"}},
                   *self.count(100), *self.count(200))
        with patch.object(codex_usage, "_git_root", return_value="/repo") as resolver:
            rows = codex_usage.events(self.path, {"session_id": "root", "cwd": "/work",
                                                  "profile_path": "/does-not-exist"})
        self.assertEqual(resolver.call_count, 1)
        self.assertEqual({row["source_repo"] for row in rows}, {"/repo"})
        self.assertEqual(rows[-1]["profile_path"], None)
        self.assertEqual(rows[-1]["profile_hash"], None)
        self.assertTrue(rows[-1]["package_path"].endswith("primitives-core"))


if __name__ == "__main__":
    unittest.main()
