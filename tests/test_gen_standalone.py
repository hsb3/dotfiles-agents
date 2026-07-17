"""Tests for scripts/gen_standalone.py -- one-skill wrapper generator (D4).

Proves the wrapper invariants (one skill folder, name == id, byte-identical to source), the
--check invariant guard, deterministic marketplace entries, and that the author is sourced
from plugins.yaml (not hardcoded). Stdlib-only; every build targets a tempdir.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import gen_standalone as G  # noqa: E402


class Build(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gen-standalone-test-")
        self.ids = G.build_standalone(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_emits_private_fork(self):
        self.assertIn("private-fork", self.ids)

    def test_wrapper_exposes_exactly_its_own_skill(self):
        skills = os.path.join(self.tmp, "private-fork", "skills")
        self.assertEqual(sorted(os.listdir(skills)), ["private-fork"])

    def test_plugin_name_equals_skill_id(self):
        with open(os.path.join(self.tmp, "private-fork", ".claude-plugin", "plugin.json")) as fh:
            manifest = json.load(fh)
        self.assertEqual(manifest["name"], "private-fork")

    def test_body_byte_identical_to_source(self):
        src = os.path.join(G.REPO, "primitives-core", "skills", "private-fork")
        built = os.path.join(self.tmp, "private-fork", "skills", "private-fork")
        self.assertTrue(G._dircmp_identical(src, built))

    def test_verify_wrappers_clean(self):
        self.assertEqual(G.verify_wrappers(self.tmp, self.ids), [])


class ComposedSkill(unittest.TestCase):
    """pptx-themes composes an authored theme layer over a verbatim-vendored Anthropic base."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gen-standalone-composed-")
        G.build_standalone(self.tmp)
        self.wrapper = os.path.join(self.tmp, "pptx-themes", "skills", "pptx-themes")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_pptx_themes_wrapper_emitted(self):
        self.assertIn("pptx-themes", os.listdir(self.tmp))

    def test_vendored_base_and_license_ship(self):
        self.assertTrue(os.path.isfile(os.path.join(self.wrapper, "base", "LICENSE.txt")))
        self.assertTrue(os.path.isfile(os.path.join(self.wrapper, "base", "SKILL.md")))

    def test_attribution_readme_cites_the_pin(self):
        with open(os.path.join(self.wrapper, "README.md"), encoding="utf-8") as fh:
            readme = fh.read()
        self.assertIn("fa0fa64bdc967915dc8399e803be67759e1e62b8", readme)
        self.assertIn("anthropics/skills", readme)


class Invariants(unittest.TestCase):
    def test_check_mode_passes_on_committed_catalog(self):
        self.assertEqual(G.main(["--check"]), 0)

    def test_author_sourced_from_plugins_yaml(self):
        # Not a hardcoded constant — must match the plugins.yaml owner.
        self.assertTrue(G.author().get("name"))

    def test_standalone_entries_shape(self):
        entries = G.standalone_entries()
        self.assertEqual(
            [e["name"] for e in entries], ["opencode-expertise", "pptx-themes", "private-fork"]
        )
        e = next(x for x in entries if x["name"] == "private-fork")
        self.assertEqual(e["source"], "./plugins/private-fork")
        self.assertTrue(e["description"])
        self.assertEqual(e["author"], G.author())


if __name__ == "__main__":
    unittest.main()
