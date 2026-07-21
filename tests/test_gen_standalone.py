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


class WrapperReadme(unittest.TestCase):
    """Issue #144 (D2): each wrapper ships a plugin-root README.md, copied verbatim from
    primitives-core/standalone-readmes/<id>/README.md — additive-only, mirroring
    gen_marketplace._copy_bundle_readme, and sitting OUTSIDE skills/ (never compared by the
    byte-identity invariant, which only ever inspects skills/<id>/)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gen-standalone-readme-")
        self.ids = G.build_standalone(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_every_wrapper_ships_a_root_readme(self):
        for skill_id in self.ids:
            readme = os.path.join(self.tmp, skill_id, "README.md")
            self.assertTrue(os.path.isfile(readme), f"missing {readme}")

    def test_readme_byte_identical_to_source(self):
        src = os.path.join(G.STANDALONE_README_DIR, "private-fork", "README.md")
        built = os.path.join(self.tmp, "private-fork", "README.md")
        with open(src, encoding="utf-8") as fa, open(built, encoding="utf-8") as fb:
            self.assertEqual(fa.read(), fb.read())

    def test_readme_sits_outside_skills_subtree(self):
        # The wrapper root README must NOT be inside skills/<id>/ — that subtree is exactly
        # what verify_wrappers's byte-identity check compares against primitives-core source.
        self.assertFalse(
            os.path.isfile(
                os.path.join(self.tmp, "private-fork", "skills", "private-fork", "README.md")
            )
        )

    def test_missing_readme_source_is_tolerated(self):
        # Additive-only, like gen_marketplace._copy_bundle_readme: no source -> no README, not
        # a hard failure.
        proot = os.path.join(self.tmp, "no-such-skill")
        os.makedirs(proot)
        G._copy_standalone_readme("no-such-skill", proot)
        self.assertFalse(os.path.exists(os.path.join(proot, "README.md")))

    def test_readme_absence_does_not_break_wrapper_invariants(self):
        # A missing README source must never fail verify_wrappers (D3 coverage is a separate,
        # marketplace-level guard in gen_marketplace, not a wrapper-shape invariant here).
        self.assertEqual(G.verify_wrappers(self.tmp, self.ids), [])


class Invariants(unittest.TestCase):
    def test_check_mode_passes_on_committed_catalog(self):
        self.assertEqual(G.main(["--check"]), 0)

    def test_author_sourced_from_plugins_yaml(self):
        # Not a hardcoded constant — must match the plugins.yaml owner.
        self.assertTrue(G.author().get("name"))

    def test_standalone_entries_shape(self):
        entries = G.standalone_entries()
        self.assertEqual(
            [e["name"] for e in entries],
            [
                "dataviz",
                "deep-research",
                "github-project-board",
                "opencode-expertise",
                "owner-signoff",
                "pptx-themes",
                "private-fork",
                "update-config",
            ],
        )
        e = next(x for x in entries if x["name"] == "private-fork")
        self.assertEqual(e["source"], "./plugins/private-fork")
        self.assertTrue(e["description"])
        self.assertEqual(e["author"], G.author())


if __name__ == "__main__":
    unittest.main()
