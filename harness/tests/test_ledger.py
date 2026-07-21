"""Results ledger — append + resume-skip with the extended harness|model key."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_harness.ledger import (  # noqa: E402
    append_row,
    load_done,
    read_rows,
    row_key,
)


class TestResultsLedger(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.path = os.path.join(self.tmp, "results.jsonl")

    def _row(self, trial, **over):
        row = {
            "harness": "claude",
            "model": "default",
            "candidate": "c",
            "case": "k",
            "config": "with",
            "trial": trial,
            "passed": True,
        }
        row.update(over)
        return row

    def test_row_key_includes_harness_and_model(self):
        # Campaign defaults to "" (empty first segment) for rows without the field.
        self.assertEqual(
            row_key(self._row(2, model="claude-sonnet-5")),
            "|claude|claude-sonnet-5|c|k|with|2",
        )

    def test_row_key_prepends_campaign(self):
        self.assertEqual(
            row_key(self._row(2, campaign="skillfix", model="claude-sonnet-5")),
            "skillfix|claude|claude-sonnet-5|c|k|with|2",
        )

    def test_campaign_is_a_resume_dimension(self):
        append_row(self.path, self._row(0))  # unlabeled (campaign "")
        done = load_done(self.path)
        self.assertIn(row_key(self._row(0)), done)
        # a labeled re-run of the same cell is a DISTINCT key, not a resume-skip.
        self.assertNotIn(row_key(self._row(0, campaign="skillfix")), done)

    def test_legacy_row_without_campaign_reads_as_empty(self):
        # A pre-campaign row on disk (no field) must still load + key cleanly.
        legacy = self._row(0)
        legacy.pop("campaign", None)  # _row has none anyway; explicit for intent
        append_row(self.path, legacy)
        done = load_done(self.path)
        self.assertIn("|claude|default|c|k|with|0", done)

    def test_append_then_resume_skip(self):
        append_row(self.path, self._row(0))
        append_row(self.path, self._row(1))
        done = load_done(self.path)
        self.assertIn(row_key(self._row(0)), done)
        self.assertIn(row_key(self._row(1)), done)
        self.assertNotIn(row_key(self._row(2)), done)

    def test_harness_and_model_are_resume_dimensions(self):
        append_row(self.path, self._row(0))
        done = load_done(self.path)
        # same key -> resume-skip
        self.assertIn(row_key(self._row(0)), done)
        # different harness -> distinct cell, NOT skipped
        self.assertNotIn(row_key(self._row(0, harness="opencode")), done)
        # different model -> distinct cell, NOT skipped
        self.assertNotIn(row_key(self._row(0, model="claude-sonnet-5")), done)

    def test_read_rows_filters_candidate(self):
        append_row(self.path, self._row(0))
        append_row(self.path, self._row(0, candidate="other"))
        rows = read_rows(self.path, "c")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["candidate"], "c")

    def test_corrupt_lines_ignored(self):
        append_row(self.path, self._row(0))
        with open(self.path, "a") as fh:
            fh.write("garbage\n")
        self.assertEqual(len(load_done(self.path)), 1)


if __name__ == "__main__":
    unittest.main()
