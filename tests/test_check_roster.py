"""Tests for scripts/check_roster.py -- the roster<->disk drift guard.

Covers the entry-schema checks (origin/disposition/requires enums + the sourced-provenance
rule), the parser, and a clean-tree smoke of main() against the seeded scaffold roster.
Stdlib-only.
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
        "origin": "authored",
        "disposition": "untriaged",
        "targets": "[claude-code]",
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

    def test_origin_enum_includes_vendored(self):
        self.assertEqual(C.ORIGINS, {"authored", "sourced", "vendored"})

    def test_disposition_is_required(self):
        self.assertIn("disposition", C.REQUIRED)


class EntrySchema(unittest.TestCase):
    def test_valid_entry_clean(self):
        self.assertEqual(_problems(_entry()), [])

    def test_bogus_origin_names_id_and_legal_values(self):
        problems = _problems(_entry(origin="bogus"))
        self.assertTrue(
            any(
                "[fixture]" in p and "authored" in p and "sourced" in p
                for p in problems
            )
        )

    def test_bogus_disposition_rejected(self):
        problems = _problems(_entry(disposition="bogus"))
        self.assertTrue(any("[fixture]" in p and "qualified" in p for p in problems))

    def test_bogus_requires_rejected(self):
        problems = _problems(_entry(requires="[bogus]"))
        self.assertTrue(any("[fixture]" in p and "hooks" in p for p in problems))

    def test_dependency_declarations_clean(self):
        self.assertEqual(
            _problems(_entry(requires="[cli:graphviz, env:dotfiles]")), []
        )

    def test_sourced_without_upstream_and_ref_fails(self):
        problems = _problems(_entry(origin="sourced"))
        self.assertTrue(any("upstream" in p for p in problems))
        self.assertTrue(any("`ref`" in p for p in problems))

    def test_sourced_with_upstream_and_ref_passes(self):
        e = _entry(
            origin="sourced",
            upstream="https://github.com/example/upstream",
            ref="abc1234",
        )
        self.assertEqual(_problems(e), [])


class SeedRoster(unittest.TestCase):
    def test_parses_real_roster(self):
        entries = C.parse_roster(C.ROSTER)
        self.assertTrue(entries)
        self.assertIn("handoff", {e.get("id") for e in entries})

    def test_required_fields_present_on_every_entry(self):
        for e in C.parse_roster(C.ROSTER):
            for k in C.REQUIRED:
                self.assertIn(k, e, f"{e.get('id')} missing {k}")


class DiskPrimitives(unittest.TestCase):
    def test_scans_mcp_specs(self):
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

    def _hook_disk(self, spec):
        """Build a primitives-core/hooks/ tree from {name: has_hook_py} and scan it."""
        repo = tempfile.mkdtemp()
        d = os.path.join(repo, "primitives-core")
        for name, has_py in spec.items():
            hd = os.path.join(d, "hooks", name)
            os.makedirs(hd)
            if has_py:
                with open(os.path.join(hd, "hook.py"), "w") as fh:
                    fh.write("print(1)\n")
        old_pc, old_repo = C.PC, C.REPO
        C.PC, C.REPO = d, repo
        try:
            return {src for t, src in C.disk_primitives() if t == "hook"}, d
        finally:
            C.PC, C.REPO = old_pc, old_repo

    def test_discovers_ratified_layout_hook(self):
        found, _ = self._hook_disk({"context-watermark": True})
        self.assertIn("primitives-core/hooks/context-watermark", found)

    def test_ignores_hook_dir_without_hook_py(self):
        found, _ = self._hook_disk({"stub": False})
        self.assertEqual(found, set())

    def test_roster_and_hook_layout_agree(self):
        # Drift guard: a hook check_roster discovers must also pass check_hook_layout, and a
        # layout check_hook_layout bans (legacy .sh) must NOT be discovered as a hook.
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
        import check_hook_layout as HL

        found, d = self._hook_disk({"context-watermark": True})
        self.assertIn("primitives-core/hooks/context-watermark", found)
        self.assertEqual(HL.check_root(os.path.join(d, "hooks"), d), [])


class CleanTree(unittest.TestCase):
    def test_main_returns_zero(self):
        self.assertEqual(C.main(), 0)


if __name__ == "__main__":
    unittest.main()
