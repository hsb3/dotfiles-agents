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
        self.assertEqual(
            row_key(self._row(2, model="claude-sonnet-5")),
            "claude|claude-sonnet-5|c|k|with|2",
        )

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
