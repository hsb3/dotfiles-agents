"""Tests for scripts/gen_marketplace.py -- the Claude Code marketplace assembler + drift guard.

Covers the plugins.yaml parser, membership mapping, a temp-dir build (manifest shape, plugin
name == bundle id, byte-identical skill bodies), determinism, and the committed-tree --check.
Stdlib-only, and never mutates the committed tree (every build targets a tempdir).
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import check_roster as R  # noqa: E402
import gen_marketplace as G  # noqa: E402


class PluginsYaml(unittest.TestCase):
    def test_parses_owner_and_bundles(self):
        owner, plugins = G.parse_plugins_yaml(G.PLUGINS_YAML)
        self.assertTrue(owner)
        ids = {p["id"] for p in plugins}
        self.assertIn("project-workflow", ids)
        pw = next(p for p in plugins if p["id"] == "project-workflow")
        self.assertTrue(pw.get("version"))
        self.assertTrue(pw.get("description"))


class Membership(unittest.TestCase):
    def test_handoff_maps_to_project_workflow(self):
        members = G.bundle_members(R.parse_roster(R.ROSTER))
        self.assertIn("handoff", members.get("project-workflow", []))


class Build(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gen-marketplace-test-")
        self.market = G.build_marketplace(self.tmp)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_marketplace_lists_bundle(self):
        names = [p["name"] for p in self.market["plugins"]]
        self.assertEqual(names, ["project-workflow"])
        self.assertEqual(self.market["name"], "dotfiles-agents")

    def test_source_points_into_plugins_dir(self):
        pw = self.market["plugins"][0]
        self.assertEqual(pw["source"], "./plugins/project-workflow")

    def test_plugin_name_equals_bundle_id(self):
        with open(
            os.path.join(
                self.tmp, "plugins", "project-workflow", ".claude-plugin", "plugin.json"
            )
        ) as fh:
            manifest = json.load(fh)
        self.assertEqual(manifest["name"], "project-workflow")

    def test_skill_body_is_byte_identical_to_source(self):
        built = os.path.join(
            self.tmp, "plugins", "project-workflow", "skills", "handoff"
        )
        src = os.path.join(G.REPO, "primitives-core", "skills", "handoff")
        self.assertTrue(G._identical(src, built))

    def test_build_is_deterministic(self):
        other = tempfile.mkdtemp(prefix="gen-marketplace-test2-")
        try:
            G.build_marketplace(other)
            a = os.path.join(self.tmp, ".claude-plugin", "marketplace.json")
            b = os.path.join(other, ".claude-plugin", "marketplace.json")
            with open(a) as fa, open(b) as fb:
                self.assertEqual(fa.read(), fb.read())
        finally:
            import shutil

            shutil.rmtree(other, ignore_errors=True)


class CheckCommitted(unittest.TestCase):
    def test_check_passes_on_committed_tree(self):
        self.assertEqual(G.check(), [])


if __name__ == "__main__":
    unittest.main()
