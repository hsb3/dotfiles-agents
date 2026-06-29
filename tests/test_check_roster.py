"""Tests for scripts/check_roster.py -- the roster<->disk drift guard.

Covers the parser, the on-disk scan (incl. the mcp/*.json scan added for the mcp primitives), and
a clean-tree smoke of main(). Stdlib-only.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import check_roster as C  # noqa: E402


class Constants(unittest.TestCase):
    def test_mcp_is_a_valid_type(self):
        self.assertIn("mcp", C.TYPES)


class ParseRoster(unittest.TestCase):
    def test_parses_real_roster(self):
        entries = C.parse_roster(C.ROSTER)
        self.assertTrue(entries)
        ids = {e.get("id") for e in entries}
        self.assertIn("agent-bus", ids)  # an mcp primitive

    def test_required_fields_present_on_every_entry(self):
        for e in C.parse_roster(C.ROSTER):
            for k in C.REQUIRED:
                self.assertIn(k, e, f"{e.get('id')} missing {k}")


class DiskPrimitives(unittest.TestCase):
    def test_scans_mcp_specs(self):
        found = C.disk_primitives()
        types = {t for t, _src in found}
        self.assertIn("mcp", types)  # the mcp/*.json scan
        self.assertIn(("mcp", "primitives-core/mcp/agent-bus.json"), found)


class CleanTree(unittest.TestCase):
    def test_main_returns_zero(self):
        self.assertEqual(C.main(), 0)


if __name__ == "__main__":
    unittest.main()
