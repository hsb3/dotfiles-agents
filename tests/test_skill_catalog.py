"""Tests for scripts/check_skill_catalog.py -- standalone eligibility + drift guard (D4).

Proves the committed catalog (private-fork + opencode-expertise) is clean and that each
eligibility/drift rule is demonstrably red-able on a seeded bad entry. Stdlib-only; fixtures
build tiny in-memory roster/catalog dicts, no filesystem roster edits.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import check_skill_catalog as C  # noqa: E402


def _roster_entry(**over):
    e = {
        "id": "private-fork",
        "type": "skill",
        "origin": "authored",
        "targets": "[claude-code]",
        "source": "primitives-core/skills/private-fork",
    }
    e.update(over)
    return e


def _cat_entry(**over):
    e = {
        "id": "private-fork",
        "standalone": "true",
        "clients": ["claude-code"],
        "depends_on_skills": [],
        "prerequisites": [],
        "provenance": "authored",
    }
    e.update(over)
    return e


def _check(cat, roster, bundle_ids=frozenset()):
    problems = []
    roster_by_id = {e["id"]: e for e in roster}
    all_ids = {e["id"] for e in roster if e.get("type") == "skill"}
    C.check_entry(cat, roster_by_id, all_ids, set(bundle_ids), problems)
    return problems


class Clean(unittest.TestCase):
    def test_committed_catalog_clean(self):
        problems, n = C.run_checks()
        self.assertEqual(problems, [])
        self.assertGreaterEqual(n, 1)

    def test_catalog_lists_exactly_the_shipped_standalone_skills(self):
        ids = [e["id"] for e in C.parse_catalog(C.CATALOG)]
        self.assertEqual(ids, ["private-fork", "opencode-expertise"])

    def test_valid_entry_has_no_problems(self):
        self.assertEqual(_check(_cat_entry(), [_roster_entry()]), [])


class RedAble(unittest.TestCase):
    def test_missing_roster_entry_flagged(self):
        self.assertTrue(any("no roster entry" in p for p in _check(_cat_entry(), [])))

    def test_sourced_origin_flagged(self):
        r = [_roster_entry(origin="sourced")]
        self.assertTrue(any("not authored" in p for p in _check(_cat_entry(), r)))

    def test_provenance_drift_flagged(self):
        r = [_roster_entry(origin="authored")]
        probs = _check(_cat_entry(provenance="sourced"), r)
        self.assertTrue(any("provenance" in p for p in probs))

    def test_disqualifying_requires_flagged(self):
        r = [_roster_entry(requires="[hooks]")]
        self.assertTrue(any("requires" in p for p in _check(_cat_entry(), r)))

    def test_non_subset_client_flagged(self):
        probs = _check(_cat_entry(clients=["opencode"]), [_roster_entry()])
        self.assertTrue(any("opencode" in p for p in probs))

    def test_bundle_namespace_clash_flagged(self):
        probs = _check(_cat_entry(), [_roster_entry()], bundle_ids={"private-fork"})
        self.assertTrue(any("clashes with bundle id" in p for p in probs))

    def test_nonempty_depends_on_flagged(self):
        probs = _check(_cat_entry(depends_on_skills=["handoff"]), [_roster_entry()])
        self.assertTrue(any("depends_on_skills" in p for p in probs))


if __name__ == "__main__":
    unittest.main()
