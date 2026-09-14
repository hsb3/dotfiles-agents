"""Tests for scripts/check_provenance.py -- provenance/externals conformance (D6 floor check 3).

Proves the authored-placement invariant (no origin: sourced body under primitives-core/) is
red-able, the externals-intent check is red-able (activated in D5), the externals parser reads
a fixture, and the real tree is clean. Stdlib-only.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import check_provenance as P  # noqa: E402


def _roster(**over):
    e = {
        "id": "fixture",
        "type": "skill",
        "source": "primitives-core/skills/fixture",
        "origin": "authored",
    }
    e.update(over)
    return e


class AuthoredPlacement(unittest.TestCase):
    def test_sourced_under_primitives_core_flagged(self):
        probs = P.authored_placement_violations([_roster(origin="sourced")])
        self.assertTrue(any("fixture" in p and "sourced" in p for p in probs))

    def test_authored_under_primitives_core_clean(self):
        self.assertEqual(P.authored_placement_violations([_roster()]), [])

    def test_sourced_outside_primitives_core_clean(self):
        # A sourced entry referenced elsewhere (externals) is fine — placement rule only.
        e = _roster(origin="sourced", source="externals/skills/thing")
        self.assertEqual(P.authored_placement_violations([e]), [])


class ExternalsIntent(unittest.TestCase):
    def test_null_intent_flagged(self):
        entries = [{"id": "up", "upstream": "null", "ref": ""}]
        probs = P.externals_intent_violations(entries)
        self.assertTrue(any("upstream" in p for p in probs))
        self.assertTrue(any("ref" in p for p in probs))

    def test_recorded_intent_clean(self):
        entries = [{"id": "up", "upstream": "https://example/x", "ref": "abc123"}]
        self.assertEqual(P.externals_intent_violations(entries), [])

    def test_parse_externals_reads_entries(self):
        d = tempfile.mkdtemp()
        fp = os.path.join(d, "externals.yaml")
        with open(fp, "w", encoding="utf-8") as fh:
            fh.write("version: 1\n\nexternals:\n  - id: foo\n    kind: skill\n    upstream: null\n    ref: null\n")
        entries = P.parse_externals(fp)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["id"], "foo")


class RealTree(unittest.TestCase):
    def test_shipped_tree_provenance_clean(self):
        self.assertEqual(P.main(), 0)


if __name__ == "__main__":
    unittest.main()
