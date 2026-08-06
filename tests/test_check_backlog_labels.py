"""Tests for scripts/check_backlog_labels.py -- the closed two-axis label vocabulary.

Proves the check is red-able on every violation shape (unknown label, zero areas, two
areas, two signals, config/script vocabulary drift in both directions) and green on a
conforming card. The real board is checked separately by `make backlog-labels`; these
fixtures are tempdirs, never files under backlog/.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import check_backlog_labels as L  # noqa: E402


def _card(labels):
    """Render a task file with the given labels in block form."""
    body = "\n".join(f"  - {x}" for x in labels) if labels else ""
    return f"---\nid: TASK-1\nstatus: To Do\nlabels:\n{body}\ndependencies: []\n---\n\nBody.\n"


def _board(cards):
    """Build a board from {filename: [labels]} and return its check problems."""
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "tasks"))
    for name, labels in cards.items():
        with open(os.path.join(d, "tasks", name), "w", encoding="utf-8") as fh:
            fh.write(_card(labels))
    return L.check_board(d, d)


class RedAble(unittest.TestCase):
    def test_unknown_label_flagged(self):
        probs = _board({"a.md": ["gates", "tech-debt"]})
        self.assertTrue(any("unknown label 'tech-debt'" in p for p in probs))

    def test_no_area_flagged(self):
        probs = _board({"a.md": ["decision"]})
        self.assertTrue(any("no area label" in p for p in probs))

    def test_empty_labels_flagged(self):
        probs = _board({"a.md": []})
        self.assertTrue(any("no area label" in p for p in probs))

    def test_two_areas_flagged(self):
        probs = _board({"a.md": ["gates", "primitives"]})
        self.assertTrue(any("2 area labels" in p for p in probs))

    def test_two_signals_flagged(self):
        probs = _board({"a.md": ["gates", "decision", "on-hold"]})
        self.assertTrue(any("2 signal labels" in p for p in probs))

    def test_config_declares_label_the_script_does_not_know(self):
        probs = L.check_vocabulary("labels:\n" + "\n".join(f"  - {x}" for x in sorted(L.AREAS | L.SIGNALS) + ["surprise"]))
        self.assertTrue(any("'surprise'" in p and "neither AREAS nor SIGNALS" in p for p in probs))

    def test_config_omits_a_label_the_script_knows(self):
        keep = sorted(L.AREAS | L.SIGNALS)[1:]
        probs = L.check_vocabulary("labels:\n" + "\n".join(f"  - {x}" for x in keep))
        self.assertTrue(any("does not declare it" in p for p in probs))


class Green(unittest.TestCase):
    def test_area_only_is_clean(self):
        self.assertEqual(_board({"a.md": ["gates"]}), [])

    def test_area_plus_one_signal_is_clean(self):
        self.assertEqual(_board({"a.md": ["primitives", "decision"]}), [])

    def test_readme_is_skipped(self):
        self.assertEqual(_board({"README.md": []}), [])

    def test_matching_vocabulary_is_clean(self):
        text = "labels:\n" + "\n".join(f"  - {x}" for x in sorted(L.AREAS | L.SIGNALS))
        self.assertEqual(L.check_vocabulary(text), [])

    def test_axes_are_disjoint(self):
        self.assertEqual(L.AREAS & L.SIGNALS, frozenset())


class Parsing(unittest.TestCase):
    def test_inline_list_form(self):
        self.assertEqual(L.parse_config_labels('labels: ["a", "b"]'), ["a", "b"])

    def test_block_form_ignores_trailing_comment(self):
        self.assertEqual(L.parse_config_labels("labels:\n  - a  # why\n  - b\n"), ["a", "b"])

    def test_block_form_skips_interleaved_comments(self):
        self.assertEqual(L.parse_config_labels("labels:\n  # area\n  - a\n  # signal\n  - b\n"), ["a", "b"])

    def test_stops_at_next_key(self):
        self.assertEqual(L.parse_config_labels("labels:\n  - a\ntypes: [\"bug\"]\n"), ["a"])

    def test_missing_key_is_empty(self):
        self.assertEqual(L.parse_config_labels("statuses: [\"To Do\"]"), [])

    def test_real_config_parses_to_the_declared_vocabulary(self):
        with open(L.CONFIG, encoding="utf-8") as fh:
            self.assertEqual(set(L.parse_config_labels(fh.read())), set(L.AREAS | L.SIGNALS))


if __name__ == "__main__":
    unittest.main()
