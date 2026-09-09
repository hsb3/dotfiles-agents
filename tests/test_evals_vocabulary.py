"""Keep evals' roster-backed select fields aligned with the roster gate."""

import os
import sys
import unittest
from collections import defaultdict

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "evals"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import check_roster as roster  # noqa: E402
import schema  # noqa: E402


def select_values(name):
    extenders = next(
        spec
        for spec in schema.collection_specs(defaultdict(str))
        if spec["name"] == "extenders"
    )
    return next(field["values"] for field in extenders["fields"] if field["name"] == name)


class TestEvalsVocabulary(unittest.TestCase):
    def test_roster_selects_match_the_roster_gate(self):
        self.assertEqual(set(select_values("origin")), roster.ORIGINS | {"external"})
        self.assertEqual(set(select_values("disposition")), roster.DISPOSITIONS)


if __name__ == "__main__":
    unittest.main()
