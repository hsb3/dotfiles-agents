"""Small contract tests for the native review-tier trial helper."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("review_tier_trial", ROOT / "evals/review_tier_trial.py")
T = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(T)


class UsageTests(unittest.TestCase):
    def test_cumulative_snapshots_deduplicate_and_reset(self):
        snapshots = [
            {"input_tokens": 100, "output_tokens": 50, "cached_input_tokens": 20},
            {"input_tokens": 100, "output_tokens": 50, "cached_input_tokens": 20},
            {"input_tokens": 130, "output_tokens": 70, "cached_input_tokens": 30},
            {"input_tokens": 12, "output_tokens": 3, "cached_input_tokens": 2},
        ]
        self.assertEqual(T.aggregate_usage(snapshots), {
            "input_tokens": 142, "output_tokens": 73, "cached_input_tokens": 32,
        })

    def test_unknown_usage_is_not_silently_zero(self):
        self.assertIsNone(T.aggregate_usage([{"input_tokens": None}]))

    def test_cached_input_cannot_exceed_input(self):
        self.assertIsNone(T.aggregate_usage([{"input_tokens": 5, "cached_input_tokens": 6}]))


class FindingTests(unittest.TestCase):
    def test_bad_json_is_an_explicit_parse_failure(self):
        findings, error = T.parse_findings("not json")
        self.assertEqual(findings, [])
        self.assertIn("parse failure", error)

    def test_oracle_counts_found_missed_and_false_positive(self):
        oracle = {"usage": [{"id": "sum", "location": "usage.py:8"}]}
        report = T.grade_findings("usage", [
            {"location": "usage.py:8", "explanation": "adds cumulative snapshots"},
            {"location": "usage.py:99", "explanation": "unrelated"},
        ], oracle)
        self.assertEqual(report, {"found": 1, "missed": 0, "false_positive": 1})


class PrepareTests(unittest.TestCase):
    def test_prepare_keeps_oracle_outside_model_case_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            T.prepare(root)
            self.assertTrue((root / "oracle.json").is_file())
            self.assertFalse(any(path.name == "oracle.json" for path in (root / "cases").rglob("*")))
            self.assertIn("sum deltas", (root / "cases/usage/CONTRACT.md").read_text())
            self.assertIn("local", (root / "cases/roles/CONTRACT.md").read_text())


if __name__ == "__main__":
    unittest.main()
