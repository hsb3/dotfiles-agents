"""Tests for scripts/check_roster.py -- the roster<->disk drift guard.

Covers the parser, the on-disk scan (incl. the mcp/*.json scan added for the mcp primitives),
the entry-schema checks (origin/disposition/requires enums + the sourced-provenance rule), and
a clean-tree smoke of main(). Stdlib-only.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import check_roster as C  # noqa: E402


def _entry(**over):
    """A schema-valid parsed roster entry (values as parse_roster produces: raw strings)."""
    e = {
        "id": "fixture",
        "type": "skill",
        "source": "primitives-core/skills/fixture",
        "shelf": "core",
        "origin": "authored",
        "disposition": "untriaged",
        "vendor": "null",
        "targets": "[claude-code]",
        "plugins": "[]",
        "summary": '"ok"',
    }
    e.update(over)
    return e


def _problems(e):
    problems = []
    C.check_entry_schema(e, problems)
    return problems


class Constants(unittest.TestCase):
    def test_mcp_is_a_valid_type(self):
        self.assertIn("mcp", C.TYPES)

    def test_origin_enum_is_authored_sourced(self):
        self.assertEqual(C.ORIGINS, {"authored", "sourced"})

    def test_disposition_enum(self):
        self.assertEqual(
            C.DISPOSITIONS,
            {"qualified", "grandfathered-pending-use", "demoted", "untriaged"},
        )

    def test_capability_enum(self):
        self.assertEqual(C.CAPABILITIES, {"hooks", "local-mcp", "hosted-mcp"})

    def test_disposition_is_required(self):
        self.assertIn("disposition", C.REQUIRED)


class EntrySchema(unittest.TestCase):
    def test_valid_entry_clean(self):
        self.assertEqual(_problems(_entry()), [])

    def test_missing_disposition_names_id_and_field(self):
        e = _entry()
        del e["disposition"]
        problems = _problems(e)
        self.assertTrue(any("[fixture]" in p and "disposition" in p for p in problems))

    def test_bogus_origin_names_id_and_legal_values(self):
        problems = _problems(_entry(origin="bogus"))
        self.assertTrue(
            any(
                "[fixture]" in p and "authored" in p and "sourced" in p
                for p in problems
            )
        )

    def test_old_vocabulary_internal_rejected(self):
        self.assertTrue(
            any("origin" in p for p in _problems(_entry(origin="internal")))
        )

    def test_bogus_disposition_names_id_and_legal_values(self):
        problems = _problems(_entry(disposition="bogus"))
        self.assertTrue(
            any(
                "[fixture]" in p and "untriaged" in p and "qualified" in p
                for p in problems
            )
        )

    def test_bogus_requires_names_id_and_legal_values(self):
        problems = _problems(_entry(requires="[bogus]"))
        self.assertTrue(
            any(
                "[fixture]" in p and "hooks" in p and "local-mcp" in p for p in problems
            )
        )

    def test_empty_requires_is_legal(self):
        self.assertEqual(_problems(_entry(requires="[]")), [])

    def test_absent_requires_is_legal(self):
        self.assertEqual(_problems(_entry()), [])

    def test_known_requires_clean(self):
        self.assertEqual(
            _problems(_entry(requires="[hooks, local-mcp, hosted-mcp]")), []
        )

    def test_dependency_declarations_clean(self):
        # cli:<kebab> / env:<kebab> dependency grammar (issue #79)
        self.assertEqual(
            _problems(
                _entry(requires="[cli:graphviz, cli:speak_gemini, env:dotfiles]")
            ),
            [],
        )

    def test_malformed_dependency_declaration_rejected(self):
        problems = _problems(_entry(requires="[cli:Not-Kebab]"))
        self.assertTrue(any("[fixture]" in p and "cli:" in p for p in problems))

    def test_unknown_dependency_kind_rejected(self):
        problems = _problems(_entry(requires="[bin:graphviz]"))
        self.assertTrue(any("[fixture]" in p for p in problems))

    def test_sourced_without_upstream_and_ref_fails(self):
        problems = _problems(_entry(origin="sourced"))
        self.assertTrue(any("upstream" in p for p in problems))
        self.assertTrue(any("`ref`" in p for p in problems))

    def test_sourced_with_null_upstream_fails(self):
        problems = _problems(_entry(origin="sourced", upstream="null", ref="v1.2.3"))
        self.assertTrue(any("upstream" in p for p in problems))

    def test_sourced_with_upstream_and_ref_passes(self):
        e = _entry(
            origin="sourced",
            upstream="https://github.com/example/upstream",
            ref="abc1234",
        )
        self.assertEqual(_problems(e), [])


class ParserTolerance(unittest.TestCase):
    def test_new_keys_parse_without_parser_changes(self):
        text = (
            "version: 1\n\nprimitives:\n"
            "  - id: fixture\n"
            "    type: skill\n"
            "    origin: sourced\n"
            "    disposition: untriaged\n"
            "    requires: [local-mcp]\n"
            "    upstream: https://github.com/example/upstream\n"
            "    ref: abc1234\n"
        )
        p = os.path.join(tempfile.mkdtemp(), "roster.yaml")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        (e,) = C.parse_roster(p)
        self.assertEqual(e["disposition"], "untriaged")
        self.assertEqual(e["requires"], "[local-mcp]")
        self.assertEqual(e["upstream"], "https://github.com/example/upstream")
        self.assertEqual(e["ref"], "abc1234")


class ParseRoster(unittest.TestCase):
    def test_parses_real_roster(self):
        entries = C.parse_roster(C.ROSTER)
        self.assertTrue(entries)
        ids = {e.get("id") for e in entries}
        # one of each rostered type (mcp is empty since #79 demoted the unprovenanced specs)
        self.assertIn("comms", ids)  # a skill
        self.assertIn("board-analyst", ids)  # an agent
        self.assertIn("python-standards.Stop.stop", ids)  # a hook handler

    def test_required_fields_present_on_every_entry(self):
        for e in C.parse_roster(C.ROSTER):
            for k in C.REQUIRED:
                self.assertIn(k, e, f"{e.get('id')} missing {k}")


class DiskPrimitives(unittest.TestCase):
    def test_scans_mcp_specs(self):
        # No mcp primitive is rostered since #79; prove the mcp/*.json scan path on a fixture.
        import tempfile

        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "mcp"))
        with open(os.path.join(d, "mcp", "x.json"), "w", encoding="utf-8") as fh:
            fh.write("{}")
        old_pc, old_repo = C.PC, C.REPO
        C.PC, C.REPO = d, os.path.dirname(d)
        try:
            found = C.disk_primitives()
        finally:
            C.PC, C.REPO = old_pc, old_repo
        self.assertIn("mcp", {t for t, _src in found})


class CleanTree(unittest.TestCase):
    def test_main_returns_zero(self):
        self.assertEqual(C.main(), 0)


if __name__ == "__main__":
    unittest.main()
