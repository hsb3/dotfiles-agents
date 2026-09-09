"""check_catalog.py — the consumer-facing catalog drift guard.

Fixture repos are built under a tempdir (never under primitives-core/, per the roster
guard's orphan rule) and the module's REPO/README_PATH/MARKETPLACE/PLUGINS_DIR constants
are pointed at them for the duration of each test.

The fixture marketplace holds three plugins so both kinds and a name enumeration are
exercised: `alpha` is a bundle (2 skills + 1 agent + 1 hook), `beta` and `delta` are
one-skill standalones.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import check_catalog as C  # noqa: E402

ALPHA_DESC = "Alpha bundles two fixture skills, an agent, and a hook."
BETA_DESC = "Beta is a single fixture skill that stands on its own."
DELTA_DESC = "Delta is another single fixture skill used by the tests."
META_DESC = "3 plugins: alpha, beta, and delta — one multi-skill bundle and two standalone one-skill plugins."

ALPHA_ROW = "| [`alpha`](plugins/alpha/README.md) | bundle | Alpha does things. | 2 skills · 1 agent · 1 hook |\n"
BETA_ROW = "| [`beta`](plugins/beta/README.md) | standalone | Beta does other things. | 1 skill |\n"
DELTA_ROW = "| [`delta`](plugins/delta/README.md) | standalone | Delta does a third thing. | 1 skill |\n"

CATALOG_README = (
    """# fixture

A small fixture marketplace.

## Chooser

Not a catalog row: [alpha](plugins/alpha/README.md) is mentioned here without backticks
so it must not be misread as a catalog row.

## Catalog

| Plugin | Kind | What it does | Contents |
|---|---|---|---|
"""
    + ALPHA_ROW
    + BETA_ROW
    + DELTA_ROW
    + """
## Links

- [marketplace manifest](.claude-plugin/marketplace.json)
- [self](README.md)
- [anchor](#chooser)
- [external](https://example.com/docs)
"""
)


def fixture_plugins():
    """The marketplace `plugins` array the healthy fixture ships (fresh dicts each call)."""
    return [
        {"name": "alpha", "description": ALPHA_DESC},
        {"name": "beta", "description": BETA_DESC},
        {"name": "delta", "description": DELTA_DESC},
    ]


class CatalogGuard(unittest.TestCase):
    def setUp(self):
        self.fix = tempfile.mkdtemp(prefix="check-catalog-")
        self.saved = {k: getattr(C, k) for k in ("REPO", "README_PATH", "MARKETPLACE", "PLUGINS_DIR")}
        C.REPO = self.fix
        C.README_PATH = os.path.join(self.fix, "README.md")
        C.MARKETPLACE = os.path.join(self.fix, ".claude-plugin", "marketplace.json")
        C.PLUGINS_DIR = os.path.join(self.fix, "plugins")

        os.makedirs(os.path.join(self.fix, ".claude-plugin"))
        self._write_marketplace(fixture_plugins())
        self._write_plugin("alpha", ALPHA_DESC, skills=2, agents=1, hooks=1)
        self._write_plugin("beta", BETA_DESC)
        self._write_plugin("delta", DELTA_DESC)
        self._write_readme(CATALOG_README)
        # a repo-root file that exists on disk but is not on the published surface
        with open(os.path.join(self.fix, "Makefile"), "w") as fh:
            fh.write("check:\n\t@true\n")

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(C, k, v)
        shutil.rmtree(self.fix, ignore_errors=True)

    def _write_marketplace(self, plugins, metadata_description=META_DESC):
        entries = []
        for p in plugins:
            entry = dict(p)
            entry.setdefault("version", "0.0.1")
            entry.setdefault("source", "./plugins/%s" % entry.get("name", "?"))
            entries.append(entry)
        with open(C.MARKETPLACE, "w", encoding="utf-8") as fh:
            json.dump({"metadata": {"description": metadata_description}, "plugins": entries}, fh)

    def _write_plugin(self, pid, description, version="0.0.1", skills=1, agents=0, hooks=0,
                      commands=0, mcp_servers=0, mcp_body=None):
        """Write plugins/<pid>/ — manifest, README, and (additively) its assembly members."""
        pdir = os.path.join(self.fix, "plugins", pid, ".claude-plugin")
        os.makedirs(pdir, exist_ok=True)
        manifest = {"name": pid, "description": description}
        if version is not None:
            manifest["version"] = version
        with open(os.path.join(pdir, "plugin.json"), "w", encoding="utf-8") as fh:
            json.dump(manifest, fh)
        readme = os.path.join(self.fix, "plugins", pid, "README.md")
        if not os.path.isfile(readme):
            with open(readme, "w", encoding="utf-8") as fh:
                fh.write(f"# {pid}\n")
        base = os.path.join(self.fix, "plugins", pid)
        for i in range(skills):
            sdir = os.path.join(base, "skills", f"{pid}-skill-{i}")
            os.makedirs(sdir, exist_ok=True)
            with open(os.path.join(sdir, "SKILL.md"), "w", encoding="utf-8") as fh:
                fh.write("---\nname: x\n---\n")
        for i in range(agents):
            os.makedirs(os.path.join(base, "agents"), exist_ok=True)
            with open(os.path.join(base, "agents", f"{pid}-agent-{i}.md"), "w", encoding="utf-8") as fh:
                fh.write("# agent\n")
        for i in range(hooks):
            hdir = os.path.join(base, "hooks", f"{pid}-hook-{i}")
            os.makedirs(hdir, exist_ok=True)
            with open(os.path.join(hdir, "hook.py"), "w", encoding="utf-8") as fh:
                fh.write("# hook\n")
        if hooks:
            with open(os.path.join(base, "hooks", "hooks.json"), "w", encoding="utf-8") as fh:
                json.dump({"hooks": {}}, fh)
        for i in range(commands):
            os.makedirs(os.path.join(base, "commands"), exist_ok=True)
            with open(os.path.join(base, "commands", f"{pid}-command-{i}.md"), "w", encoding="utf-8") as fh:
                fh.write("---\ndescription: x\n---\ndo the thing\n")
        if mcp_servers or mcp_body is not None:
            body = mcp_body if mcp_body is not None else json.dumps(
                {"mcpServers": {f"{pid}-server-{i}": {"type": "http", "url": "${U}/mcp"}
                                for i in range(mcp_servers)}})
            with open(os.path.join(base, ".mcp.json"), "w", encoding="utf-8") as fh:
                fh.write(body)

    def _write_readme(self, text):
        with open(C.README_PATH, "w", encoding="utf-8") as fh:
            fh.write(text)

    def _row_with(self, row, kind=None, blurb=None, contents=None):
        """Rewrite one catalog row's Kind / blurb / Contents cell, keeping the plugin cell."""
        cells = [c for c in row.strip().strip("|").split("|")]
        if kind is not None:
            cells[1] = f" {kind} "
        if blurb is not None:
            cells[2] = f" {blurb} "
        if contents is not None:
            cells[3] = f" {contents} "
        new = "|" + "|".join(cells) + "|\n"
        self._write_readme(CATALOG_README.replace(row, new))

    # -- passing shape -----------------------------------------------------

    def test_healthy_fixture_is_clean(self):
        self.assertEqual(C.catalog_problems(), [])
        self.assertEqual(C.link_problems(), [])
        self.assertEqual(C.description_problems(), [])
        self.assertEqual(C.version_problems(), [])
        self.assertEqual(C.metadata_problems(), [])
        self.assertEqual(C.truncation_problems(), [])
        self.assertEqual(C.main(), 0)

    # -- check 1: catalog coverage ------------------------------------------

    def test_plugin_missing_from_catalog_is_red(self):
        self._write_readme(CATALOG_README.replace(BETA_ROW, ""))
        problems = C.catalog_problems()
        self.assertTrue(any("beta" in p and "missing" in p for p in problems), problems)

    def test_unknown_plugin_in_catalog_is_red(self):
        readme = CATALOG_README.replace(
            "## Links",
            "| [`gamma`](plugins/gamma/README.md) | bundle | Not a real plugin. | 1 skill |\n\n## Links",
        )
        self._write_readme(readme)
        problems = C.catalog_problems()
        self.assertTrue(any("gamma" in p and "not a plugin" in p for p in problems), problems)

    def test_duplicate_catalog_row_is_red(self):
        self._write_readme(CATALOG_README.replace(BETA_ROW, BETA_ROW + BETA_ROW))
        problems = C.catalog_problems()
        self.assertTrue(any("duplicate" in p and "beta" in p for p in problems), problems)

    def test_id_path_mismatch_is_red(self):
        self._write_readme(
            CATALOG_README.replace(BETA_ROW, BETA_ROW.replace("plugins/beta/README.md", "plugins/alpha/README.md"))
        )
        problems = C.catalog_problems()
        self.assertTrue(any("mismatch" in p for p in problems), problems)

    def test_second_catalog_heading_is_red(self):
        """A healthy decoy section followed by a second `## Catalog` must not pass."""
        readme = CATALOG_README.replace(
            "## Links",
            "## Catalog\n\n| Plugin | Kind | What it does | Contents |\n|---|---|---|---|\n"
            "| [`beta`](plugins/beta/README.md) | bundle |  | 99 skills |\n\n## Links",
        )
        self._write_readme(readme)
        problems = C.catalog_problems()
        self.assertTrue(any("'## Catalog' headings" in p for p in problems), problems)

    def test_fenced_catalog_table_is_red(self):
        """A table wrapped in a ``` fence renders as no catalog at all."""
        readme = CATALOG_README.replace("| Plugin | Kind", "```\n| Plugin | Kind").replace(
            DELTA_ROW, DELTA_ROW + "```\n"
        )
        self._write_readme(readme)
        problems = C.catalog_problems()
        self.assertTrue(any("holds no catalog rows" in p for p in problems), problems)

    def test_commented_out_catalog_table_is_red(self):
        """A table wrapped in an HTML comment renders as no catalog at all."""
        readme = CATALOG_README.replace("| Plugin | Kind", "<!--\n| Plugin | Kind").replace(
            DELTA_ROW, DELTA_ROW + "-->\n"
        )
        self._write_readme(readme)
        problems = C.catalog_problems()
        self.assertTrue(any("holds no catalog rows" in p for p in problems), problems)

    # -- check 2: catalog cell content ---------------------------------------

    def test_unknown_kind_label_is_red(self):
        self._row_with(BETA_ROW, kind="megabundle")
        problems = C.catalog_problems()
        self.assertTrue(
            any("`beta`" in p and "neither `bundle` nor `standalone`" in p for p in problems), problems
        )

    def test_kind_label_disagreeing_with_assembly_is_red(self):
        """beta is a one-skill assembly, so calling it a bundle is drift."""
        self._row_with(BETA_ROW, kind="bundle")
        problems = C.catalog_problems()
        self.assertTrue(
            any("`beta`" in p and "Kind cell 'bundle' disagrees with the assembly" in p for p in problems),
            problems,
        )

    def test_bundle_labelled_standalone_is_red(self):
        """alpha carries 2 skills + an agent + a hook, so `standalone` is drift."""
        self._row_with(ALPHA_ROW, kind="standalone")
        problems = C.catalog_problems()
        self.assertTrue(
            any("`alpha`" in p and "disagrees with the assembly" in p for p in problems), problems
        )

    def test_blank_blurb_is_red(self):
        self._row_with(BETA_ROW, blurb="")
        problems = C.catalog_problems()
        self.assertTrue(any("`beta`" in p and "cell is empty" in p for p in problems), problems)

    def test_overlong_blurb_is_red(self):
        self._row_with(BETA_ROW, blurb="Beta " + "does a great many things " * 6 + "indeed.")
        problems = C.catalog_problems()
        self.assertTrue(
            any("`beta`" in p and "the rule is at most 140" in p for p in problems), problems
        )

    def test_multi_sentence_blurb_is_red(self):
        self._row_with(BETA_ROW, blurb="Beta does other things. It also does more things.")
        problems = C.catalog_problems()
        self.assertTrue(any("`beta`" in p and "runs 2 sentences" in p for p in problems), problems)

    def test_unterminated_blurb_is_red(self):
        self._row_with(BETA_ROW, blurb="Beta does other things")
        problems = C.catalog_problems()
        self.assertTrue(
            any("`beta`" in p and "does not end in" in p for p in problems), problems
        )

    def test_contents_cell_count_drift_is_red(self):
        self._row_with(ALPHA_ROW, contents="47 skills · 12 agents")
        problems = C.catalog_problems()
        self.assertTrue(
            any("`alpha`" in p and "Contents cell" in p and "disagrees with the assembly" in p for p in problems),
            problems,
        )

    def test_contents_cell_missing_a_unit_is_red(self):
        """Dropping the agents/hooks half of alpha's contents is still drift."""
        self._row_with(ALPHA_ROW, contents="2 skills")
        problems = C.catalog_problems()
        self.assertTrue(
            any("`alpha`" in p and "disagrees with the assembly" in p for p in problems), problems
        )

    def test_unparseable_contents_cell_is_red(self):
        self._row_with(BETA_ROW, contents="lots of stuff")
        problems = C.catalog_problems()
        self.assertTrue(any("`beta`" in p and "is not a" in p for p in problems), problems)

    def test_command_counts_and_kind_and_contents_cell(self):
        """decision-010: commands join skills/agents/hooks in the assembly counters, tip an
        assembly into a bundle, and render/parse singular vs plural in the Contents cell."""
        self._write_plugin("omega", "Omega is a fixture plugin used only for command counting.",
                            skills=1, commands=1)
        counts = C._assembly_counts("omega")
        self.assertEqual(counts, (1, 0, 0, 1, 0))
        self.assertEqual(C._expected_kind(counts), "bundle")

        singular = C._contents_label({"skill": 1, "command": 1})
        self.assertEqual(singular, "1 skill · 1 command")
        self.assertEqual(C._parse_contents(singular), {"skill": 1, "command": 1})

        plural = C._contents_label({"command": 2})
        self.assertEqual(plural, "2 commands")
        self.assertEqual(C._parse_contents(plural), {"command": 2})

    def test_mcp_server_counts_and_contents_cell(self):
        """An MCP server is a `.mcp.json` at the plugin ROOT, not a subdirectory of members,
        so it needs its own counter — but it is still derived from the assembly on disk."""
        self._write_plugin("gamma", "Gamma is a fixture plugin used only for server counting.",
                           skills=1, mcp_servers=1)
        counts = C._assembly_counts("gamma")
        self.assertEqual(counts, (1, 0, 0, 0, 1))

        singular = C._contents_label({"skill": 1, "MCP server": 1})
        self.assertEqual(singular, "1 skill · 1 MCP server")
        self.assertEqual(C._parse_contents(singular), {"skill": 1, "MCP server": 1})

        plural = C._contents_label({"MCP server": 2})
        self.assertEqual(plural, "2 MCP servers")
        self.assertEqual(C._parse_contents(plural), {"MCP server": 2})

    def test_mcp_server_count_is_the_specs_server_entries_not_the_file(self):
        """One `.mcp.json` may declare several servers; the count is what it declares."""
        self._write_plugin("gamma", "Gamma is a fixture plugin used only for server counting.",
                           skills=1, mcp_servers=3)
        self.assertEqual(C._assembly_counts("gamma")[4], 3)

    def test_an_mcp_spec_that_declares_nothing_counts_zero(self):
        self._write_plugin("gamma", "Gamma is a fixture plugin used only for server counting.",
                           skills=1, mcp_body="{ not json at all")
        self.assertEqual(C._assembly_counts("gamma")[4], 0)

    def test_undeclared_mcp_server_is_red(self):
        self._write_plugin("alpha", ALPHA_DESC, skills=2, agents=1, hooks=1, mcp_servers=1)
        problems = C.catalog_problems()
        self.assertTrue(
            any("`alpha`" in p and "1 MCP server" in p for p in problems), problems
        )

    def test_declared_mcp_server_is_clean(self):
        self._write_plugin("alpha", ALPHA_DESC, skills=2, agents=1, hooks=1, mcp_servers=1)
        self._row_with(ALPHA_ROW, contents="2 skills · 1 agent · 1 hook · 1 MCP server")
        self.assertEqual(C.catalog_problems(), [])

    def test_an_mcp_server_alone_does_not_make_a_bundle(self):
        """Kind counts the units a user invokes; a server spec rides along with the skill
        that drives it, so a one-skill plugin registering a server stays standalone."""
        self._write_plugin("beta", BETA_DESC, skills=1, mcp_servers=1)
        self.assertEqual(C._expected_kind(C._assembly_counts("beta")), "standalone")

    # -- check 3: published-surface links ------------------------------------

    def test_relative_link_not_on_disk_is_red(self):
        readme = CATALOG_README.replace(
            "- [external](https://example.com/docs)",
            "- [external](https://example.com/docs)\n- [ghost](plugins/ghost/README.md)",
        )
        self._write_readme(readme)
        problems = C.link_problems()
        self.assertTrue(any("does not exist" in p for p in problems), problems)

    def test_link_outside_published_surface_is_red(self):
        readme = CATALOG_README.replace(
            "- [external](https://example.com/docs)",
            "- [external](https://example.com/docs)\n- [build](Makefile)",
        )
        self._write_readme(readme)
        problems = C.link_problems()
        self.assertTrue(any("published surface" in p for p in problems), problems)

    def test_claude_plugin_dir_link_is_red(self):
        """Only .claude-plugin/marketplace.json is lifted — not the directory itself."""
        readme = CATALOG_README.replace(
            "- [external](https://example.com/docs)",
            "- [external](https://example.com/docs)\n- [manifests](.claude-plugin)",
        )
        self._write_readme(readme)
        problems = C.link_problems()
        self.assertTrue(
            any("'.claude-plugin'" in p and "published surface" in p for p in problems), problems
        )

    def test_reference_style_link_off_the_published_surface_is_red(self):
        readme = CATALOG_README + "\n[r]: Makefile\n"
        self._write_readme(readme)
        problems = C.link_problems()
        self.assertTrue(
            any("reference-style link definition" in p and "published surface" in p for p in problems),
            problems,
        )

    def test_reference_style_link_not_on_disk_is_red(self):
        readme = CATALOG_README + "\n[r]: primitives-core.yaml\n"
        self._write_readme(readme)
        problems = C.link_problems()
        self.assertTrue(
            any("reference-style link definition" in p and "does not exist" in p for p in problems),
            problems,
        )

    def test_html_href_off_the_published_surface_is_red(self):
        readme = CATALOG_README.replace(
            "- [external](https://example.com/docs)",
            '- [external](https://example.com/docs)\n- <a href="Makefile">build</a>',
        )
        self._write_readme(readme)
        problems = C.link_problems()
        self.assertTrue(
            any("HTML href attribute" in p and "published surface" in p for p in problems), problems
        )

    def test_html_href_not_on_disk_is_red(self):
        readme = CATALOG_README.replace(
            "- [external](https://example.com/docs)",
            '- [external](https://example.com/docs)\n- <a href="backlog/decisions/">decisions</a>',
        )
        self._write_readme(readme)
        problems = C.link_problems()
        self.assertTrue(
            any("HTML href attribute" in p and "does not exist" in p for p in problems), problems
        )

    def test_link_inside_a_code_fence_is_ignored(self):
        """A path in a shell snippet is not a link — it must not be link-checked."""
        readme = CATALOG_README + "\n```sh\nsee [dev only](scripts/install.sh)\n```\n"
        self._write_readme(readme)
        self.assertEqual(C.link_problems(), [])

    # -- check 4: manifest parity (description + version) ---------------------

    def test_description_mismatch_is_red(self):
        self._write_plugin("beta", "Beta does completely different things now, honestly.")
        problems = C.description_problems()
        self.assertTrue(any("beta" in p and "drift" in p for p in problems), problems)

    def test_version_mismatch_is_red(self):
        self._write_plugin("beta", BETA_DESC, version="9.9.9")
        problems = C.version_problems()
        self.assertTrue(
            any("beta" in p and "version drift" in p and "9.9.9" in p for p in problems), problems
        )

    def test_codex_overlay_checks_release_and_required_handler(self):
        root = os.path.join(C.PLUGINS_DIR, 'alpha')
        os.makedirs(os.path.join(root, '.codex-plugin'))
        native = {'name': 'alpha', 'version': '0.0.1',
                  'skills': './skills', 'hooks': './hooks/codex-hooks.json'}
        manifest = os.path.join(root, '.codex-plugin/plugin.json')
        with open(manifest, 'w') as stream:
            json.dump(native, stream)
        handler = os.path.join(root, 'hooks/required.py')
        with open(handler, 'w') as stream:
            stream.write('pass\n')
        with open(os.path.join(root, 'hooks/codex-hooks.json'), 'w') as stream:
            json.dump({'hooks': {'PreToolUse': [{'hooks': [{
                'command': 'python3 "${CLAUDE_PLUGIN_ROOT}/hooks/required.py"'}]}]}}, stream)
        self.assertEqual(C.codex_problems(), [])
        os.unlink(handler)
        self.assertTrue(any('required.py' in p for p in C.codex_problems()))
        native['version'] = '9.9.9'
        with open(manifest, 'w') as stream:
            json.dump(native, stream)
        self.assertTrue(any('name/version' in p for p in C.codex_problems()))

    def test_missing_version_in_plugin_json_is_red(self):
        self._write_plugin("beta", BETA_DESC, version=None)
        problems = C.version_problems()
        self.assertTrue(any("beta" in p and "no `version` field" in p for p in problems), problems)

    # -- check 5: metadata.description claims ---------------------------------

    def test_metadata_plugin_count_drift_is_red(self):
        self._write_marketplace(
            fixture_plugins(),
            metadata_description="900 plugins: forty multi-skill bundles and two standalone plugins.",
        )
        problems = C.metadata_problems()
        self.assertTrue(any("claims 900 plugin(s)" in p for p in problems), problems)

    def test_metadata_bundle_count_word_drift_is_red(self):
        self._write_marketplace(
            fixture_plugins(),
            metadata_description="3 plugins: forty multi-skill bundles and two standalone plugins.",
        )
        problems = C.metadata_problems()
        self.assertTrue(any("claims 40 bundle(s)" in p for p in problems), problems)

    def test_metadata_standalone_count_drift_is_red(self):
        self._write_marketplace(
            fixture_plugins(),
            metadata_description="3 plugins: one multi-skill bundle and eleven standalone plugins.",
        )
        problems = C.metadata_problems()
        self.assertTrue(any("claims 11 standalone plugin(s)" in p for p in problems), problems)

    def test_metadata_enumerating_an_unknown_plugin_is_red(self):
        self._write_marketplace(
            fixture_plugins(),
            metadata_description="3 plugins: alpha, beta, and epsilon — one bundle and two standalone plugins.",
        )
        problems = C.metadata_problems()
        self.assertTrue(any("enumerates `epsilon`" in p for p in problems), problems)

    # -- check 6: description quality ------------------------------------------

    def test_truncated_plugin_description_is_red(self):
        self._write_plugin("alpha", "Alpha does things that go on and on and on and on…")
        problems = C.truncation_problems()
        self.assertTrue(any("alpha" in p and "ellipsis" in p for p in problems), problems)

    def test_truncated_marketplace_description_is_red(self):
        plugins = fixture_plugins()
        plugins[1]["description"] = "Beta does other things but then it just trails off..."
        self._write_marketplace(plugins)
        problems = C.truncation_problems()
        self.assertTrue(any("beta" in p and "ellipsis" in p for p in problems), problems)

    def test_truncated_metadata_description_is_red(self):
        self._write_marketplace(
            fixture_plugins(),
            metadata_description="A fixture marketplace of 3 plugins that trails off...",
        )
        problems = C.truncation_problems()
        self.assertTrue(any("metadata.description" in p and "ellipsis" in p for p in problems), problems)

    def test_ellipsis_followed_by_a_period_is_red(self):
        """`….` ends in a period, but it is still an ellipsis cutoff."""
        self._write_plugin("alpha", "Alpha does things that go on and on and on and on….")
        problems = C.truncation_problems()
        self.assertTrue(any("alpha" in p and "ellipsis" in p for p in problems), problems)

    def test_unterminated_description_is_red(self):
        """The shipped bug: a mid-word cutoff with no trailing ellipsis to detect."""
        self._write_plugin("alpha", "Stand up and operate a board sliced into ma")
        problems = C.truncation_problems()
        self.assertTrue(
            any("alpha" in p and "final sentence is unterminated" in p for p in problems), problems
        )

    def test_missing_description_key_is_red(self):
        pdir = os.path.join(self.fix, "plugins", "beta", ".claude-plugin")
        with open(os.path.join(pdir, "plugin.json"), "w", encoding="utf-8") as fh:
            json.dump({"name": "beta", "version": "0.0.1"}, fh)
        problems = C.truncation_problems()
        self.assertTrue(any("beta" in p and "no `description` key" in p for p in problems), problems)

    def test_empty_description_is_red(self):
        self._write_plugin("beta", "   ")
        problems = C.truncation_problems()
        self.assertTrue(any("beta" in p and "description is empty" in p for p in problems), problems)

    def test_stub_description_is_red(self):
        self._write_plugin("beta", "Beta.")
        problems = C.truncation_problems()
        self.assertTrue(any("beta" in p and "40-character floor" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
