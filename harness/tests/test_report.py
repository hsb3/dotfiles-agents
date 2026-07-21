"""Aggregation — per (harness, model, case, config) cells + within-cell deltas."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_harness.report import deltas, summarize  # noqa: E402


def _row(harness, model, config, trial, passed, cost):
    return {
        "harness": harness,
        "model": model,
        "case": "k",
        "config": config,
        "trial": trial,
        "passed": passed,
        "cost_usd": cost,
        "duration_ms": 1000 + trial,
    }


class TestAggregation(unittest.TestCase):
    def _rows(self):
        return [
            _row("claude", "default", "with", 0, True, 0.10),
            _row("claude", "default", "with", 1, True, 0.20),
            _row("claude", "default", "with", 2, False, 0.30),
            _row("claude", "default", "baseline", 0, False, 0.10),
            _row("claude", "default", "baseline", 1, False, 0.10),
            _row("claude", "default", "baseline", 2, True, 0.10),
        ]

    def test_summarize_per_cell(self):
        s = summarize(self._rows())
        w = s[("claude", "default", "k", "with")]
        self.assertEqual(w["n"], 3)
        self.assertAlmostEqual(w["pass_rate"], 2 / 3, places=3)
        self.assertTrue(w["pass_any"])
        self.assertFalse(w["pass_all"])
        self.assertAlmostEqual(w["cost_mean"], 0.2, places=3)

    def test_deltas_within_cell(self):
        d = deltas(summarize(self._rows()))
        self.assertAlmostEqual(d[("claude", "default", "k")], (2 / 3) - (1 / 3), places=3)

    def test_harness_and_model_are_separate_cells(self):
        rows = [
            _row("claude", "default", "with", 0, True, 0.1),
            _row("opencode", "anthropic/claude", "with", 0, False, 0.1),
            _row("claude", "claude-sonnet-5", "with", 0, True, 0.1),
        ]
        s = summarize(rows)
        self.assertIn(("claude", "default", "k", "with"), s)
        self.assertIn(("opencode", "anthropic/claude", "k", "with"), s)
        self.assertIn(("claude", "claude-sonnet-5", "k", "with"), s)
        self.assertEqual(len(s), 3)

    def test_single_trial_stdev_is_zero(self):
        s = summarize([_row("claude", "default", "with", 0, True, 0.1)])
        self.assertEqual(s[("claude", "default", "k", "with")]["cost_stdev"], 0.0)

    def test_skip_rows_excluded_from_stats(self):
        rows = [
            _row("claude", "default", "with", 0, True, 0.1),
            _row("claude", "default", "with", 1, None, None),  # unsupported/skip
        ]
        s = summarize(rows)
        self.assertEqual(s[("claude", "default", "k", "with")]["n"], 1)


if __name__ == "__main__":
    unittest.main()
