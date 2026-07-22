"""Tests for scripts/gen_marketplace.py -- the Claude Code marketplace assembler + drift guard.

Covers the plugins.yaml parser, membership mapping, a temp-dir build (manifest shape, plugin
name == bundle id, byte-identical skill bodies), determinism, and the committed-tree --check.
Stdlib-only, and never mutates the committed tree (every build targets a tempdir).
"""

import contextlib
import io
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
        self.assertIn("code-desk", ids)
        pw = next(p for p in plugins if p["id"] == "code-desk")
        self.assertTrue(pw.get("version"))
        self.assertTrue(pw.get("description"))


class PluginKindValidation(unittest.TestCase):
    """PR #145 review flag: `kind` is REQUIRED on every plugins.yaml entry. A missing kind
    used to silently default to "bundle" — a latent mislabeling risk for future kits; now the
    generator fails loudly (non-zero, naming the entry) on a missing or invalid kind."""

    def test_committed_entries_all_carry_valid_kind(self):
        _, plugins = G.parse_plugins_yaml(G.PLUGINS_YAML)
        self.assertEqual(G.plugin_meta_problems(plugins), [])
        for p in plugins:
            self.assertIn(p.get("kind"), G.PLUGIN_KINDS)

    def test_missing_kind_is_reported_naming_the_entry(self):
        problems = G.plugin_meta_problems([{"id": "future-kit", "version": "0.1.0"}])
        self.assertEqual(len(problems), 1)
        self.assertIn("future-kit", problems[0])
        self.assertIn("kind", problems[0])

    def test_invalid_kind_is_reported_naming_the_value(self):
        problems = G.plugin_meta_problems([{"id": "future-kit", "kind": "kit"}])
        self.assertEqual(len(problems), 1)
        self.assertIn("future-kit", problems[0])
        self.assertIn("'kit'", problems[0])

    def test_standalone_skill_is_not_a_plugins_yaml_kind(self):
        # "standalone skill" is assigned during assembly from skill-catalog.yaml, never
        # hand-authored in plugins.yaml.
        problems = G.plugin_meta_problems([{"id": "x", "kind": "standalone skill"}])
        self.assertEqual(len(problems), 1)

    def test_build_goes_red_when_a_kind_line_is_removed(self):
        # End-to-end red-ability: strip foreman-kit's `kind: plugin` line from a COPY of the
        # committed plugins.yaml, point the generator at it — the build must raise (naming
        # the entry) and the --check CLI lane (`make build-check` / `make ci`) must exit 1.
        # Restoring the real path goes green again (the surrounding suite proves that).
        with open(G.PLUGINS_YAML, encoding="utf-8") as fh:
            lines = fh.readlines()
        # Several entries carry `kind: plugin` now — strip only the one that immediately
        # follows foreman-kit's `- id:` line so the raised error names that entry.
        idx = next(
            i for i, ln in enumerate(lines) if ln.strip() == "- id: foreman-kit"
        )
        self.assertEqual(lines[idx + 1].strip(), "kind: plugin")
        stripped = lines[: idx + 1] + lines[idx + 2 :]
        self.assertEqual(len(stripped), len(lines) - 1)  # exactly one kind line removed
        tmpdir = tempfile.mkdtemp(prefix="gen-marketplace-kind-red-")
        bad_yaml = os.path.join(tmpdir, "plugins.yaml")
        with open(bad_yaml, "w", encoding="utf-8") as fh:
            fh.writelines(stripped)
        real = G.PLUGINS_YAML
        try:
            G.PLUGINS_YAML = bad_yaml
            with self.assertRaises(ValueError) as ctx:
                G.build_marketplace(os.path.join(tmpdir, "out"))
            self.assertIn("foreman-kit", str(ctx.exception))
            self.assertIn("kind", str(ctx.exception))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = G.main(["--check"])
            self.assertEqual(rc, 1)
            self.assertIn("foreman-kit", out.getvalue())
        finally:
            G.PLUGINS_YAML = real
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)


class Membership(unittest.TestCase):
    def test_handoff_maps_to_foreman_kit(self):
        # E3: handoff is re-homed to foreman-kit as its sole owner.
        members = G.bundle_members(R.parse_roster(R.ROSTER))
        self.assertIn("handoff", members.get("foreman-kit", []))

    def test_handoff_not_in_project_workflow(self):
        # E3 dedup: no primitive ships in both foreman-kit and a desk bundle.
        members = G.bundle_members(R.parse_roster(R.ROSTER))
        self.assertNotIn("handoff", members.get("code-desk", []))
        self.assertNotIn("handoff", members.get("exec-desk", []))
        # E4/E5/E6 recomposition: board-triage moved from project-workflow to exec-desk.
        self.assertIn("board-triage", members.get("exec-desk", []))


class Build(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gen-marketplace-test-")
        self.market = G.build_marketplace(self.tmp)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_marketplace_lists_bundles_and_standalone(self):
        names = [p["name"] for p in self.market["plugins"]]
        # two bundles (code-desk, exec-desk) + three kits (diagrams, foreman-kit,
        # obsidian-toolkit) + nine standalone skills (dataviz, deep-research,
        # github-project-board, opencode-expertise, owner-signoff, pptx-themes,
        # private-fork, project-memory, update-config), sorted by name
        self.assertEqual(
            names,
            [
                "code-desk",
                "dataviz",
                "deep-research",
                "diagrams",
                "exec-desk",
                "foreman-kit",
                "github-project-board",
                "obsidian-toolkit",
                "opencode-expertise",
                "owner-signoff",
                "pptx-themes",
                "private-fork",
                "project-memory",
                "update-config",
            ],
        )
        self.assertEqual(self.market["name"], "dotfiles-agents")

    def test_source_points_into_plugins_dir(self):
        by_name = {p["name"]: p for p in self.market["plugins"]}
        self.assertEqual(by_name["code-desk"]["source"], "./plugins/code-desk")
        self.assertEqual(by_name["private-fork"]["source"], "./plugins/private-fork")

    def test_plugin_name_equals_bundle_id(self):
        with open(
            os.path.join(
                self.tmp, "plugins", "code-desk", ".claude-plugin", "plugin.json"
            )
        ) as fh:
            manifest = json.load(fh)
        self.assertEqual(manifest["name"], "code-desk")

    def test_skill_body_is_byte_identical_to_source(self):
        built = os.path.join(
            self.tmp, "plugins", "exec-desk", "skills", "board-triage"
        )
        src = os.path.join(G.REPO, "primitives-core", "skills", "board-triage")
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
        # E3: the four hooks are re-homed to foreman-kit (sole owner).
        self.fk_hooks = os.path.join(self.tmp, "plugins", "foreman-kit", "hooks")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_hooks_map_to_foreman_kit(self):
        hooks = G.bundle_hooks(R.parse_roster(R.ROSTER))
        fk = hooks.get("foreman-kit", [])
        for hid in ("context-watermark", "handoff-freshness-guard",
                    "session-handoff-surfacer", "subagent-telemetry"):
            self.assertIn(hid, fk)
        # E3 dedup: hooks no longer ship in a desk bundle.
        self.assertEqual(hooks.get("code-desk", []), [])
        self.assertEqual(hooks.get("exec-desk", []), [])

    def test_hook_body_assembled_byte_identical(self):
        built = os.path.join(self.fk_hooks, "context-watermark")
        src = os.path.join(G.REPO, "primitives-core", "hooks", "context-watermark")
        self.assertTrue(G._identical(src, built))

    def test_plugin_hooks_manifest_written(self):
        with open(os.path.join(self.fk_hooks, "hooks.json")) as fh:
            manifest = json.load(fh)
        # All four hook events assemble into the one bundle manifest.
        for event in ("UserPromptSubmit", "PreCompact", "SessionStart", "SubagentStop"):
            self.assertIn(event, manifest["hooks"])
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
            os.path.exists(os.path.join(self.tmp, "plugins", "code-desk", "hooks"))
        )


class AgentAssembly(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gen-marketplace-agents-")
        G.build_marketplace(self.tmp)
        # E2: the four foreman-kit agents are the first real agent members.
        self.fk_agents = os.path.join(self.tmp, "plugins", "foreman-kit", "agents")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_agents_map_to_foreman_kit(self):
        agents = G.bundle_agents(R.parse_roster(R.ROSTER))
        fk = agents.get("foreman-kit", [])
        for aid in ("scout", "builder", "reviewer", "lead"):
            self.assertIn(aid, fk)
        # seed-agent removed: no agents ship in a desk bundle.
        self.assertEqual(agents.get("code-desk", []), [])
        self.assertEqual(agents.get("exec-desk", []), [])

    def test_agent_body_assembled_byte_identical(self):
        built = os.path.join(self.fk_agents, "scout.md")
        src = os.path.join(G.REPO, "primitives-core", "agents", "scout.md")
        self.assertTrue(os.path.isfile(built))
        self.assertTrue(G._identical(src, built))

    def test_bundle_without_agents_has_no_agents_dir(self):
        self.assertFalse(
            os.path.exists(os.path.join(self.tmp, "plugins", "code-desk", "agents"))
        )

    def test_agent_drift_is_red_able(self):
        # The roster<->generated-tree guard compares bytes (G._identical, what check() uses):
        # a freshly generated agent matches its source; a drifted one is caught; regenerating
        # (re-copying from source) restores the match. Mirrors the hook-member drift guard.
        built = os.path.join(self.fk_agents, "scout.md")
        src = os.path.join(G.REPO, "primitives-core", "agents", "scout.md")
        self.assertTrue(G._identical(src, built))  # green: generated tree == roster source
        with open(built, "a", encoding="utf-8") as fh:
            fh.write("\ndrift injected\n")
        self.assertFalse(G._identical(src, built))  # red: tree drifted from the roster
        import shutil

        shutil.copy2(src, built)
        self.assertTrue(G._identical(src, built))  # green again after regeneration


class AgentOnlyBundleAssembly(unittest.TestCase):
    """Fixture repo exercising two branches the committed roster can't reach today:
    (1) an AGENT-ONLY bundle (zero skills/hooks) hitting the skip-condition path, and
    (2) a member whose source filename stem != its roster id, proving the shipped file is
    keyed on the id (agents/<id>.md), not the source basename. Both are dormant in the real
    tree (both bundles have skills; the seed's id == its stem) but E2 ships foreman-kit as a
    standalone bundle whose members may be agent-only and renamed."""

    def setUp(self):
        import shutil

        self.fix = tempfile.mkdtemp(prefix="gen-marketplace-agent-only-fixture-")
        self.addCleanup(shutil.rmtree, self.fix, ignore_errors=True)
        pc_agents = os.path.join(self.fix, "primitives-core", "agents")
        os.makedirs(pc_agents)
        # id 'solo' deliberately != source filename stem 'solo-agent'.
        self.agent_src = os.path.join(pc_agents, "solo-agent.md")
        with open(self.agent_src, "w", encoding="utf-8") as fh:
            fh.write("---\nname: solo\ndescription: fixture agent.\n---\n\nbody\n")
        with open(os.path.join(self.fix, "primitives-core.yaml"), "w", encoding="utf-8") as fh:
            fh.write(
                "version: 1\nprimitives:\n"
                "  - id: solo\n"
                "    type: agent\n"
                "    source: primitives-core/agents/solo-agent.md\n"
                "    shelf: core\n"
                "    origin: authored\n"
                "    disposition: qualified\n"
                "    vendor: null\n"
                "    targets: [claude-code]\n"
                "    plugins: [solo-kit]\n"
                '    summary: "fixture"\n'
            )
        with open(os.path.join(self.fix, "plugins.yaml"), "w", encoding="utf-8") as fh:
            fh.write(
                'version: 1\nowner:\n  name: "Owner"\nplugins:\n'
                "  - id: solo-kit\n"
                "    kind: plugin\n"  # kind is now required on every entry — no silent default
                '    version: "0.0.1"\n'
                '    description: "agent-only fixture bundle"\n'
            )
        # Point the generator at the fixture; stub the standalone step (it reads the real
        # skill-catalog, out of scope here). These are module globals resolved at call time.
        # addCleanup (not tearDown) so a failure mid-setUp still restores — a leaked patch
        # would corrupt every later test class that reads the real roster.
        saved = {k: getattr(G, k) for k in ("REPO", "ROSTER", "PLUGINS_YAML", "BUNDLES_DIR")}
        saved_standalone = (
            G.gen_standalone.build_standalone,
            G.gen_standalone.standalone_entries,
        )

        def _restore():
            for k, v in saved.items():
                setattr(G, k, v)
            (
                G.gen_standalone.build_standalone,
                G.gen_standalone.standalone_entries,
            ) = saved_standalone

        self.addCleanup(_restore)
        G.REPO = self.fix
        G.ROSTER = os.path.join(self.fix, "primitives-core.yaml")
        G.PLUGINS_YAML = os.path.join(self.fix, "plugins.yaml")
        G.BUNDLES_DIR = os.path.join(self.fix, "bundles")
        G.gen_standalone.build_standalone = lambda out_root: None
        G.gen_standalone.standalone_entries = lambda: []

        self.out = tempfile.mkdtemp(prefix="gen-marketplace-agent-only-out-")
        self.addCleanup(shutil.rmtree, self.out, ignore_errors=True)
        G.build_marketplace(self.out)
        self.proot = os.path.join(self.out, "plugins", "solo-kit")

    def test_agent_only_bundle_ships(self):
        # skip condition: no skills, no hooks, but agents -> the bundle must still assemble.
        self.assertTrue(os.path.isdir(self.proot))
        self.assertTrue(
            os.path.isfile(os.path.join(self.proot, ".claude-plugin", "plugin.json"))
        )

    def test_shipped_agent_keyed_on_id_not_source_stem(self):
        by_id = os.path.join(self.proot, "agents", "solo.md")
        self.assertTrue(os.path.isfile(by_id))  # agents/<id>.md
        self.assertFalse(  # NOT agents/<source-stem>.md
            os.path.exists(os.path.join(self.proot, "agents", "solo-agent.md"))
        )
        self.assertTrue(G._identical(self.agent_src, by_id))  # byte-identical to source

    def test_agent_only_bundle_has_no_skill_or_hook_dirs(self):
        self.assertFalse(os.path.exists(os.path.join(self.proot, "skills")))
        self.assertFalse(os.path.exists(os.path.join(self.proot, "hooks")))


class BundleReadmeAssembly(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gen-marketplace-readmes-")
        G.build_marketplace(self.tmp)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_code_desk_readme_byte_identical_to_source(self):
        built = os.path.join(self.tmp, "plugins", "code-desk", "README.md")
        src = os.path.join(G.BUNDLES_DIR, "code-desk", "README.md")
        self.assertTrue(os.path.isfile(built))
        self.assertTrue(G._identical(src, built))

    def test_exec_desk_readme_byte_identical_to_source(self):
        built = os.path.join(self.tmp, "plugins", "exec-desk", "README.md")
        src = os.path.join(G.BUNDLES_DIR, "exec-desk", "README.md")
        self.assertTrue(os.path.isfile(built))
        self.assertTrue(G._identical(src, built))

    def test_missing_readme_source_is_tolerated(self):
        # A bundle with no bundles/<id>/README.md ships without one --
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
        # private-fork ships BOTH as a standalone plugin and inside the code-desk bundle.
        bundle_skill = os.path.join(
            self.tmp, "plugins", "code-desk", "skills", "private-fork"
        )
        self.assertTrue(os.path.isdir(bundle_skill))


class CheckCommitted(unittest.TestCase):
    def test_check_passes_on_committed_tree(self):
        self.assertEqual(G.check(), [])


class PluginsMd(unittest.TestCase):
    """Tests for the PLUGINS.md generated inventory (issue #144, D1)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gen-marketplace-plugins-md-")
        self.market = G.build_marketplace(self.tmp)
        with open(os.path.join(self.tmp, "PLUGINS.md"), encoding="utf-8") as fh:
            self.md = fh.read()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_written_alongside_marketplace_json(self):
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "PLUGINS.md")))

    def test_marked_generated(self):
        self.assertIn("do not hand-edit", self.md)
        self.assertIn("make build", self.md)

    def test_every_plugin_has_a_section(self):
        for entry in self.market["plugins"]:
            self.assertIn(f"## {entry['name']}", self.md)

    def test_kind_bundle_vs_plugin_vs_standalone(self):
        # code-desk/exec-desk are desk bundles; foreman-kit is a kit (plugin), not a desk
        # bundle; the four one-skill wrappers are standalone skills (skill-catalog.yaml).
        by_section = self.md.split("## ")
        sections = {s.split("\n", 1)[0]: s for s in by_section[1:]}
        self.assertIn("**Kind:** bundle", sections["code-desk"])
        self.assertIn("**Kind:** bundle", sections["exec-desk"])
        self.assertIn("**Kind:** plugin", sections["foreman-kit"])
        self.assertIn("**Kind:** standalone skill", sections["private-fork"])

    def test_install_command_uses_marketplace_name(self):
        self.assertIn("claude plugin install code-desk@dotfiles-agents", self.md)
        self.assertIn("claude plugin install private-fork@dotfiles-agents", self.md)

    def test_contents_summary_lists_members(self):
        self.assertIn("repo-compliance-audit", self.md)  # a code-desk member skill
        self.assertIn("context-watermark", self.md)  # a foreman-kit member hook
        self.assertIn("scout", self.md)  # a foreman-kit member agent

    def test_deterministic(self):
        other = tempfile.mkdtemp(prefix="gen-marketplace-plugins-md-2-")
        try:
            G.build_marketplace(other)
            with open(os.path.join(other, "PLUGINS.md"), encoding="utf-8") as fh:
                other_md = fh.read()
            self.assertEqual(self.md, other_md)
        finally:
            import shutil

            shutil.rmtree(other, ignore_errors=True)

    def test_committed_plugins_md_matches_regenerated(self):
        with open(G.PLUGINS_MD, encoding="utf-8") as fh:
            committed = fh.read()
        self.assertEqual(committed, self.md)


class ReadmeCoverage(unittest.TestCase):
    """D3 (issue #144): every distributed plugin must ship plugins/<id>/README.md."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gen-marketplace-readme-coverage-")
        self.market = G.build_marketplace(self.tmp)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_clean_tree_has_no_coverage_problems(self):
        self.assertEqual(G.readme_coverage_problems(self.tmp, self.market), [])

    def test_all_seven_plugins_ship_a_readme(self):
        for entry in self.market["plugins"]:
            readme = os.path.join(self.tmp, "plugins", entry["name"], "README.md")
            self.assertTrue(os.path.isfile(readme), f"missing {readme}")

    def test_removing_one_readme_is_red_able(self):
        # Red: delete a real, already-shipped README from the freshly built tree.
        victim = os.path.join(self.tmp, "plugins", "private-fork", "README.md")
        self.assertTrue(os.path.isfile(victim))
        os.remove(victim)
        problems = G.readme_coverage_problems(self.tmp, self.market)
        self.assertEqual(len(problems), 1)
        self.assertIn("private-fork", problems[0])

    def test_check_fails_when_a_readme_source_is_removed(self):
        # End-to-end red-ability: with a README SOURCE temporarily removed, check() (the
        # `make build-check` / `make ci` lane) must report the gap, and restoring the source
        # must make it green again.
        src = os.path.join(
            G.REPO, "primitives-core", "standalone-readmes", "private-fork", "README.md"
        )
        with open(src, encoding="utf-8") as fh:
            saved = fh.read()
        try:
            os.remove(src)
            problems = G.check()
            self.assertTrue(
                any("private-fork" in p and "README" in p for p in problems),
                problems,
            )
        finally:
            with open(src, "w", encoding="utf-8") as fh:
                fh.write(saved)
        self.assertEqual(G.check(), [])  # green again once the source is restored


class StandaloneByteIdentityStillRedAble(unittest.TestCase):
    """Issue #144: proves the wrapper-root README addition (D2) did NOT weaken the pre-existing
    skills/ byte-identity drift guard for a standalone wrapper — a real skill-source mutation
    is still caught by check(), the same mechanism AgentAssembly.test_agent_drift_is_red_able
    proves for bundle-assembled agents."""

    def setUp(self):
        self.src = os.path.join(G.REPO, "primitives-core", "skills", "private-fork", "SKILL.md")
        with open(self.src, encoding="utf-8") as fh:
            self.saved = fh.read()

    def tearDown(self):
        with open(self.src, "w", encoding="utf-8") as fh:
            fh.write(self.saved)

    def test_skill_source_mutation_is_caught_by_check(self):
        self.assertEqual(G.check(), [])  # green before mutation
        with open(self.src, "a", encoding="utf-8") as fh:
            fh.write("\ndrift injected by test\n")
        problems = G.check()
        self.assertTrue(
            any("plugins/" in p and "drift" in p for p in problems), problems
        )
        with open(self.src, "w", encoding="utf-8") as fh:
            fh.write(self.saved)
        self.assertEqual(G.check(), [])  # green again after restoring


if __name__ == "__main__":
    unittest.main()
