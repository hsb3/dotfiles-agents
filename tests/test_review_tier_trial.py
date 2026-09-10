"""Contract tests for the bounded native review-tier trial helper."""
import importlib.util
import json
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("review_tier_trial", ROOT / "evals/review_tier_trial.py")
T = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(T)


class UsageTests(unittest.TestCase):
    def test_turn_completed_usage_is_incremental_and_ignores_other_events(self):
        events = [
            {"type": "turn.completed", "usage": {"input_tokens": 100, "cached_input_tokens": 30, "output_tokens": 5}},
            {"type": "other", "usage": {"input_tokens": 900}},
            {"type": "turn.completed", "usage": {"input_tokens": 12, "output_tokens": 3}},
        ]
        self.assertEqual(T.parse_usage(events), {"input_tokens": 112, "cached_input_tokens": 30, "output_tokens": 8})

    def test_unknown_usage_is_not_silently_zero(self):
        self.assertEqual(T.parse_usage([{"type": "turn.completed", "usage": None}]),
                         {"input_tokens": None, "cached_input_tokens": None, "output_tokens": None})


class FindingTests(unittest.TestCase):
    def test_bad_json_is_an_explicit_parse_failure(self):
        findings, error = T.parse_findings("not json")
        self.assertEqual(findings, [])
        self.assertIn("parse failure", error)


class PrepareTests(unittest.TestCase):
    def test_fixtures_execute_planted_failures_and_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            T.prepare(root)
            usage = runpy.run_path(root / "cases/usage/usage.py")
            snapshots = [{"input_tokens": 100}, {"input_tokens": 100}, {"input_tokens": 130}, {"input_tokens": 12}]
            self.assertEqual(usage["total_usage"](snapshots), 342)  # planted defect; contract says 142
            self.assertEqual(usage["uncached_input"]({"input_tokens": 100, "cached_input_tokens": 30}), 70)
            roles = runpy.run_path(root / "cases/roles/roles.py")
            self.assertEqual(roles["resolve_role"]("global", "local"), "global")  # planted defect
            changed, missing = root / "changed", root / "missing"
            changed.write_text("changed")
            roles["write_managed"](changed, "new", "expected")
            roles["write_managed"](missing, "new", "expected")
            self.assertEqual(changed.read_text(), "new")  # planted overwrite defect
            self.assertEqual(missing.read_text(), "new")  # control: creation works
            oracle = json.loads((root / "oracle.json").read_text())
            self.assertIn("explanation", oracle["usage"]["findings"][0])
            self.assertEqual(oracle["roles"]["controls"], ["write_managed creates a missing file"])
            self.assertFalse(any(path.name == "oracle.json" for path in (root / "cases").rglob("*")))


class ArtifactTests(unittest.TestCase):
    def test_existing_report_is_refused_and_timeout_bytes_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            T.prepare(root)
            run_dir = root / "runs"
            run_dir.mkdir()
            stem = "usage-gpt-5.6-terra"
            (run_dir / f"{stem}.json").write_text("old")
            with self.assertRaises(FileExistsError):
                T.run_case("usage", "gpt-5.6-terra", root)
            (run_dir / f"{stem}.json").unlink()
            (run_dir / f"{stem}.last-message.txt").write_text('{"findings":[]}')

            def timeout(*args, **kwargs):
                raise subprocess.TimeoutExpired(args[0], 300, output=b'{"type":"turn.completed","usage":{"input_tokens":2}}\n', stderr=b"late")

            report = T.run_case("usage", "gpt-5.6-terra", root, runner=timeout)
            self.assertTrue(report["timed_out"])
            self.assertIn("parse failure", report["parse_error"])
            self.assertNotIn("grade", report)
            self.assertEqual((run_dir / f"{stem}.stderr").read_text(), "late")


if __name__ == "__main__":
    unittest.main()
