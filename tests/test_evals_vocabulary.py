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


def select_values(schema_module, name):
    extenders = next(
        spec
        for spec in schema_module.collection_specs(defaultdict(str))
        if spec["name"] == "extenders"
    )
    return next(field["values"] for field in extenders["fields"] if field["name"] == name)


class TestEvalsVocabulary(unittest.TestCase):
    def assert_roster_selects_match(self, schema_module):
        self.assertEqual(set(select_values(schema_module, "origin")), roster.ORIGINS | {"external"})
        self.assertEqual(set(select_values(schema_module, "disposition")), roster.DISPOSITIONS)

    def test_roster_selects_match_the_roster_gate(self):
        self.assert_roster_selects_match(schema)


if __name__ == "__main__":
    unittest.main()
