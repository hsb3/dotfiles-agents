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

    def test_marketplace_lists_bundles_and_standalone(self):
        names = [p["name"] for p in self.market["plugins"]]
        # exactly the two bundles + the two standalone skills, sorted by name
        self.assertEqual(
            names,
            ["opencode-expertise", "private-fork", "project-workflow", "repo-standards"],
        )
        self.assertEqual(self.market["name"], "dotfiles-agents")

    def test_source_points_into_plugins_dir(self):
        by_name = {p["name"]: p for p in self.market["plugins"]}
        self.assertEqual(by_name["project-workflow"]["source"], "./plugins/project-workflow")
        self.assertEqual(by_name["private-fork"]["source"], "./plugins/private-fork")

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


class HookAssembly(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gen-marketplace-hooks-")
        G.build_marketplace(self.tmp)
        self.pw_hooks = os.path.join(self.tmp, "plugins", "project-workflow", "hooks")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_hook_maps_to_project_workflow(self):
        hooks = G.bundle_hooks(R.parse_roster(R.ROSTER))
        self.assertIn("context-watermark", hooks.get("project-workflow", []))
        self.assertIn("handoff-freshness-guard", hooks.get("project-workflow", []))

    def test_hook_body_assembled_byte_identical(self):
        built = os.path.join(self.pw_hooks, "context-watermark")
        src = os.path.join(G.REPO, "primitives-core", "hooks", "context-watermark")
        self.assertTrue(G._identical(src, built))

    def test_plugin_hooks_manifest_written(self):
        with open(os.path.join(self.pw_hooks, "hooks.json")) as fh:
            manifest = json.load(fh)
        self.assertIn("UserPromptSubmit", manifest["hooks"])
        self.assertIn("PreCompact", manifest["hooks"])
        cmd = manifest["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/hooks/context-watermark/hook.py", cmd)
        self.assertIn("CONTEXT_WATERMARK_SOFT=70000", cmd)

    def test_manifest_command_env_is_deterministic(self):
        # Sorted env keys -> HARD before SOFT, every build.
        m = G.build_hooks_manifest(
            ["context-watermark"],
            {"context-watermark": "primitives-core/hooks/context-watermark"},
        )
        cmd = m["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        self.assertTrue(cmd.index("CONTEXT_WATERMARK_HARD") < cmd.index("CONTEXT_WATERMARK_SOFT"))

    def test_bundle_without_hooks_has_no_hooks_dir(self):
        self.assertFalse(
            os.path.exists(os.path.join(self.tmp, "plugins", "repo-standards", "hooks"))
        )


class BundleReadmeAssembly(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gen-marketplace-readmes-")
        G.build_marketplace(self.tmp)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_project_workflow_readme_byte_identical_to_source(self):
        built = os.path.join(self.tmp, "plugins", "project-workflow", "README.md")
        src = os.path.join(G.BUNDLES_DIR, "project-workflow", "README.md")
        self.assertTrue(os.path.isfile(built))
        self.assertTrue(G._identical(src, built))

    def test_repo_standards_readme_byte_identical_to_source(self):
        built = os.path.join(self.tmp, "plugins", "repo-standards", "README.md")
        src = os.path.join(G.BUNDLES_DIR, "repo-standards", "README.md")
        self.assertTrue(os.path.isfile(built))
        self.assertTrue(G._identical(src, built))

    def test_missing_readme_source_is_tolerated(self):
        # A bundle with no primitives-core/bundles/<id>/README.md ships without one --
        # the copy step must be a no-op, never a hard failure.
        proot = os.path.join(self.tmp, "plugins", "no-such-bundle")
        os.makedirs(proot)
        G._copy_bundle_readme("no-such-bundle", proot)
        self.assertFalse(os.path.exists(os.path.join(proot, "README.md")))


class StandaloneAssembly(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gen-marketplace-standalone-")
        self.market = G.build_marketplace(self.tmp)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_standalone_wrapper_assembled(self):
        wrapper = os.path.join(self.tmp, "plugins", "private-fork")
        self.assertTrue(os.path.isdir(wrapper))
        with open(os.path.join(wrapper, ".claude-plugin", "plugin.json")) as fh:
            manifest = json.load(fh)
        self.assertEqual(manifest["name"], "private-fork")
        # exactly one skill folder, its own
        self.assertEqual(sorted(os.listdir(os.path.join(wrapper, "skills"))), ["private-fork"])

    def test_wrapped_body_byte_identical_to_source(self):
        built = os.path.join(self.tmp, "plugins", "private-fork", "skills", "private-fork")
        src = os.path.join(G.REPO, "primitives-core", "skills", "private-fork")
        self.assertTrue(G._identical(src, built))

    def test_standalone_entry_in_marketplace(self):
        by_name = {p["name"]: p for p in self.market["plugins"]}
        self.assertIn("private-fork", by_name)
        self.assertEqual(by_name["private-fork"]["source"], "./plugins/private-fork")

    def test_standalone_coexists_with_bundle(self):
        # private-fork ships BOTH as a standalone plugin and inside the repo-standards bundle.
        bundle_skill = os.path.join(
            self.tmp, "plugins", "repo-standards", "skills", "private-fork"
        )
        self.assertTrue(os.path.isdir(bundle_skill))


class CheckCommitted(unittest.TestCase):
    def test_check_passes_on_committed_tree(self):
        self.assertEqual(G.check(), [])


if __name__ == "__main__":
    unittest.main()
