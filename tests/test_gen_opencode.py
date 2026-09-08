"""gen_opencode unit tests (install-time laydown, ADR 0017).

Covers the matrix-driven agent frontmatter transform (decision-009: every field, tool and
model alias is either declared in translation.yaml or a build problem — never a silent
drop), the opencode skill-name/description validators, the exclusion-vs-roster conflict
guard, build determinism against the real roster (two temp builds must be byte-identical),
the --out CLI contract, and check_roster's matrix-completeness gate.
"""

import copy
import json
import os
import shutil
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import check_roster as CR  # noqa: E402
import gen_opencode as G  # noqa: E402
from check_roster import parse_roster  # noqa: E402

#: The real matrix — these tests pin the shipped declarations, not a hand-made stand-in.
TR = CR.parse_translation(os.path.join(REPO, "translation.yaml"))

CC_AGENT = """---
name: scout
description: Read-only recon.
model: haiku
effort: low
maxTurns: 15
tools: Read, Grep, Glob
color: cyan
---

Body text survives verbatim.
"""


class TestTransformAgent(unittest.TestCase):
    def _t(self, text=CC_AGENT, agent_id="scout"):
        return G.transform_agent(text, TR, agent_id)

    def test_mapping_rules(self):
        out, problems, _ = self._t()
        self.assertEqual(problems, [])
        fm, body = G.split_frontmatter(out)
        self.assertNotIn("name", fm)  # filename carries identity
        self.assertEqual(fm["mode"], "subagent")
        self.assertEqual(fm["model"], "anthropic/claude-haiku-4-5")
        self.assertEqual(fm["steps"], "15")
        self.assertNotIn("effort", fm)  # CC-only knob dropped
        self.assertIn("Body text survives verbatim.", body)

    def test_permission_inversion(self):
        read_only, _, _ = self._t()
        self.assertIn("write: deny", read_only)
        self.assertIn("bash: deny", read_only)
        self.assertIn("read: allow", read_only)
        builder, _, _ = self._t(
            CC_AGENT.replace("tools: Read, Grep, Glob", "tools: Read, Edit, Write, Bash"))
        self.assertIn("write: allow", builder)
        self.assertIn("bash: allow", builder)

    def test_read_bucket_is_derived_not_hardcoded(self):
        """`read: allow` used to be a constant line; with no read-capable tool it is deny."""
        out, problems, _ = self._t(CC_AGENT.replace("tools: Read, Grep, Glob", "tools: Bash"))
        self.assertEqual(problems, [])
        self.assertIn("read: deny", out)
        self.assertIn("bash: allow", out)

    def test_provider_prefixed_model_passes_through(self):
        out, problems, _ = self._t(CC_AGENT.replace("model: haiku", "model: openai/gpt-5"))
        self.assertEqual(problems, [])
        self.assertIn("model: openai/gpt-5", out)

    def test_unknown_model_alias_is_a_problem(self):
        """Replaces the old silent-drop pin: an unrecognized alias fails the build
        (decision-009 AC #7 — never a silent omission)."""
        _, problems, _ = self._t(CC_AGENT.replace("model: haiku", "model: mystery"))
        self.assertTrue(any("mystery" in p and "scout" in p for p in problems), problems)

    def test_unsupported_model_alias_is_a_notice(self):
        out, problems, notices = self._t(CC_AGENT.replace("model: haiku", "model: inherit"))
        self.assertEqual(problems, [])
        self.assertTrue(any("inherit" in n for n in notices), notices)
        self.assertNotIn("model:", out.split("---")[1])

    def test_unknown_tool_is_a_problem(self):
        _, problems, _ = self._t(
            CC_AGENT.replace("tools: Read, Grep, Glob", "tools: Read, Telepathy"))
        self.assertTrue(any("Telepathy" in p for p in problems), problems)

    def test_unknown_frontmatter_key_is_a_problem(self):
        _, problems, _ = self._t(CC_AGENT.replace("effort: low", "vibes: high"))
        self.assertTrue(any("vibes" in p for p in problems), problems)

    def test_color_and_effort_are_notices_not_silence(self):
        out, problems, notices = self._t()
        self.assertEqual(problems, [])
        for field in ("color", "effort"):
            self.assertTrue(any(field in n and "scout" in n for n in notices), notices)
            self.assertNotIn(f"{field}:", out.split("---")[1])

    def test_delegate_tools_notice_and_grant_no_bucket(self):
        """`Agent`/`SendMessage` used to fall through to an implicit `read: allow` with no
        signal; they now say so out loud and contribute to no permission bucket."""
        out, problems, notices = self._t(
            CC_AGENT.replace("tools: Read, Grep, Glob", "tools: Agent, SendMessage"),
            agent_id="manager")
        self.assertEqual(problems, [])
        for tool in ("Agent", "SendMessage"):
            self.assertTrue(any(tool in n and "manager" in n for n in notices), notices)
        self.assertIn("read: deny", out)
        self.assertIn("write: deny", out)
        self.assertIn("bash: deny", out)

    def test_mcp_tool_matches_the_prefix_row(self):
        _, problems, notices = self._t(
            CC_AGENT.replace("tools: Read, Grep, Glob",
                             "tools: Read, mcp__plugin_widget_widget__whoami"),
            agent_id="widget-manager")
        self.assertEqual(problems, [])  # the declared `prefix: mcp__` blanket covers it
        self.assertTrue(any("mcp__plugin_widget_widget__whoami" in n for n in notices), notices)

    def test_notices_are_deterministic(self):
        self.assertEqual(self._t()[2], self._t()[2])


class TestEveryDeclaredRowTravels(unittest.TestCase):
    """A declared `map` row that the emitter has no branch for used to validate clean and
    then vanish — a silent drop wearing a passing gate, which is what tdx3 exists to kill."""

    def _with_row(self, **row):
        tr = copy.deepcopy(TR)
        tr["field_treatments"].append(row)
        return tr

    def test_map_row_outside_the_known_emitters_is_emitted(self):
        tr = self._with_row(field="temperature", treatment="map", opencode="temperature")
        out, problems, notices = G.transform_agent(
            CC_AGENT.replace("effort: low", "temperature: 0.7"), tr, "scout")
        self.assertEqual(problems, [])
        self.assertIn("temperature: 0.7", out)

    def test_map_row_with_no_target_key_is_a_problem(self):
        tr = self._with_row(field="temperature", treatment="map")
        _, problems, _ = G.transform_agent(
            CC_AGENT.replace("effort: low", "temperature: 0.7"), tr, "scout")
        self.assertTrue(any("temperature" in p for p in problems), problems)

    def test_pinned_keys_keep_their_positions(self):
        """description / mode / model / steps order is load-bearing; an extra map row
        appends after them rather than shuffling the block."""
        tr = self._with_row(field="temperature", treatment="map", opencode="temperature")
        out, _, _ = G.transform_agent(
            CC_AGENT.replace("effort: low", "temperature: 0.7"), tr, "scout")
        head = out.split("---")[1].strip().splitlines()
        self.assertEqual(head[:4], ["description: Read-only recon.", "mode: subagent",
                                    "model: anthropic/claude-haiku-4-5", "steps: 15"])
        self.assertEqual(head[4], "temperature: 0.7")

    def test_empty_mapped_value_is_not_silence(self):
        _, problems, _ = G.transform_agent(
            CC_AGENT.replace("description: Read-only recon.", "description:"), TR, "scout")
        self.assertTrue(any("description" in p for p in problems), problems)


class TestFrontmatterParser(unittest.TestCase):
    """split_frontmatter feeds BOTH the transform and the completeness gate, so a shape it
    misreads is a wrong answer in two places at once."""

    BLOCK = """---
name: scout
description: Read-only recon.
model: haiku
tools:
  - Read
  - Bash
---

Body.
"""

    def test_block_sequence_tools_are_parsed_not_read_as_empty(self):
        fm, _ = CR.split_frontmatter(self.BLOCK)
        self.assertEqual(fm["tools"], "Read, Bash")

    def test_block_sequence_tools_reach_the_permission_map(self):
        out, problems, _ = G.transform_agent(self.BLOCK, TR, "scout")
        self.assertEqual(problems, [])
        self.assertIn("read: allow", out)
        self.assertIn("bash: allow", out)
        self.assertIn("write: deny", out)

    def test_block_sequence_tools_are_gated(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        with open(os.path.join(d, "drifter.md"), "w", encoding="utf-8") as fh:
            fh.write(self.BLOCK.replace("  - Bash", "  - Telepathy"))
        problems = CR.check_matrix_completeness(agents_dir=d)
        self.assertTrue(any("Telepathy" in p for p in problems), problems)

    def test_key_with_a_digit_is_not_invisible(self):
        fm, _ = CR.split_frontmatter(CC_AGENT.replace("effort: low", "model2: opus"))
        self.assertIn("model2", fm)

    def test_key_with_a_digit_reaches_the_transform(self):
        _, problems, _ = G.transform_agent(
            CC_AGENT.replace("effort: low", "model2: opus"), TR, "scout")
        self.assertTrue(any("model2" in p for p in problems), problems)

    def test_key_with_a_digit_reaches_the_gate(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        with open(os.path.join(d, "drifter.md"), "w", encoding="utf-8") as fh:
            fh.write(CC_AGENT.replace("effort: low", "model2: opus"))
        problems = CR.check_matrix_completeness(agents_dir=d)
        self.assertTrue(any("model2" in p for p in problems), problems)


class TestSkillValidators(unittest.TestCase):
    def _skill(self, name, desc):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        src = os.path.join(d, name)
        os.makedirs(src)
        with open(os.path.join(src, "SKILL.md"), "w") as fh:
            fh.write(f"---\nname: {name}\ndescription: {desc}\n---\nbody\n")
        return src

    def test_bad_name_flagged(self):
        src = self._skill("Bad_Name", "fine")
        self.assertTrue(any("regex" in p for p in G.skill_problems("Bad_Name", src)))

    def test_long_description_flagged(self):
        src = self._skill("fine-name", "x" * 1100)
        self.assertTrue(any("1024" in p for p in G.skill_problems("fine-name", src)))

    def test_clean_skill_passes(self):
        src = self._skill("fine-name", "a normal description")
        self.assertEqual(G.skill_problems("fine-name", src), [])


class TestExclusionConflict(unittest.TestCase):
    def test_excluded_id_with_opencode_target_is_a_problem(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        translation = {
            "matrix": [{"type": "skill", "target": "opencode", "treatment": "native"}],
            "model_aliases": [],
            "tool_capabilities": [],
            "field_treatments": [],
            "exclusions": [{"id": "update-config", "reason": "cc-specific"}],
        }
        entries = [{
            "id": "update-config", "type": "skill",
            "source": "primitives-core/skills/update-config",
            "targets": "[claude-code, opencode]",
        }]
        problems, _ = G.build(d, entries, translation)
        self.assertTrue(any("resolve the disagreement" in p for p in problems))


class TestCommandExclusion(unittest.TestCase):
    """decision-010: a roster `type: command` entry must reach the exclusions manifest with
    the matrix's reason, not be silently skipped (the pre-change treatment loop never
    reached the type at all, so it left no trace in the generated README)."""

    def test_command_lands_in_exclusions_with_matrix_reason(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        reason = "commands need a per-command authoring pass"
        translation = {
            "matrix": [
                {"type": "command", "target": "opencode", "treatment": "unsupported", "reason": reason},
            ],
            "model_aliases": [],
            "tool_capabilities": [],
            "field_treatments": [],
            "exclusions": [],
        }
        entries = [{
            "id": "activate", "type": "command",
            "source": "primitives-core/commands/activate.md",
            "targets": "[claude-code]",
        }]
        problems, _ = G.build(d, entries, translation)
        self.assertEqual(problems, [])
        with open(os.path.join(d, "README.md"), encoding="utf-8") as fh:
            readme = fh.read()
        self.assertIn(f"| `activate` | command | {reason} |", readme)


class TestMcpRender(unittest.TestCase):
    """A `treatment: render` mcp entry targeting opencode must leave a trace.

    The roster alone cannot prove this: both rostered mcp entries are `targets:
    [claude-code]`, so a synthetic entry is the only subject. Before the fix such an entry
    entered neither `shipped` nor `excluded` and vanished from the generated README.
    """

    MATRIX = {
        "matrix": [{"type": "mcp", "target": "opencode", "treatment": "render"}],
        "model_aliases": [],
        "tool_capabilities": [],
        "field_treatments": [],
        "exclusions": [],
    }

    def _spec(self, body):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        path = os.path.join(d, "server.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
        return path

    def _out(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        return d

    def _fragment(self, out):
        with open(os.path.join(out, "opencode.jsonc"), encoding="utf-8") as fh:
            text = fh.read()
        body = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("//"))
        return json.loads(body)

    def _readme(self, out):
        with open(os.path.join(out, "README.md"), encoding="utf-8") as fh:
            return fh.read()

    def test_remote_server_renders_into_the_fragment(self):
        spec = self._spec(json.dumps({"mcpServers": {"demo": {
            "type": "http", "url": "${DEMO_URL}/mcp",
            "headers": {"Authorization": "Bearer ${DEMO_TOKEN}"}}}}))
        out = self._out()
        entries = [{"id": "demo-server", "type": "mcp", "source": spec, "targets": "[opencode]"}]
        self.assertEqual(G.build(out, entries, self.MATRIX)[0], [])
        self.assertEqual(self._fragment(out)["mcp"], {"demo": {
            "type": "remote", "url": "{env:DEMO_URL}/mcp",
            "headers": {"Authorization": "Bearer {env:DEMO_TOKEN}"}}})

    def test_local_server_renders_as_a_command(self):
        spec = self._spec(json.dumps({"mcpServers": {"fs": {
            "type": "stdio", "command": "npx", "args": ["-y", "server-fs"],
            "env": {"KEY": "${MY_KEY}"}}}}))
        out = self._out()
        entries = [{"id": "fs-server", "type": "mcp", "source": spec, "targets": "[opencode]"}]
        self.assertEqual(G.build(out, entries, self.MATRIX)[0], [])
        self.assertEqual(self._fragment(out)["mcp"], {"fs": {
            "type": "local", "command": ["npx", "-y", "server-fs"],
            "environment": {"KEY": "{env:MY_KEY}"}}})

    def test_rendered_server_is_named_in_the_lane_readme(self):
        spec = self._spec(json.dumps({"mcpServers": {"demo": {
            "type": "http", "url": "https://mcp.example.com/mcp"}}}))
        out = self._out()
        entries = [{"id": "demo-server", "type": "mcp", "source": spec, "targets": "[opencode]"}]
        self.assertEqual(G.build(out, entries, self.MATRIX)[0], [])
        readme = self._readme(out)
        self.assertIn("1 MCP server", readme)
        self.assertIn("`demo-server`", readme)  # the trace back to the roster entry

    def test_claude_code_only_mcp_entry_stays_a_recorded_exclusion(self):
        spec = self._spec(json.dumps({"mcpServers": {"demo": {"type": "http", "url": "x"}}}))
        out = self._out()
        entries = [{"id": "demo-server", "type": "mcp", "source": spec,
                    "targets": "[claude-code]"}]
        self.assertEqual(G.build(out, entries, self.MATRIX)[0], [])
        self.assertIn(
            "| `demo-server` | mcp | roster targets do not include opencode |",
            self._readme(out))
        self.assertNotIn("mcp", self._fragment(out))

    def test_unrenderable_spec_is_a_problem_never_a_silent_drop(self):
        out = self._out()
        entries = [{"id": "broken-server", "type": "mcp", "source": self._spec("{ nope"),
                    "targets": "[opencode]"}]
        problems, _ = G.build(out, entries, self.MATRIX)
        self.assertTrue(any("broken-server" in p for p in problems), problems)

    def test_server_with_no_transport_is_a_problem(self):
        spec = self._spec(json.dumps({"mcpServers": {"demo": {"type": "carrier-pigeon"}}}))
        out = self._out()
        entries = [{"id": "odd-server", "type": "mcp", "source": spec, "targets": "[opencode]"}]
        problems, _ = G.build(out, entries, self.MATRIX)
        self.assertTrue(any("odd-server" in p and "demo" in p for p in problems), problems)

    def test_spec_declaring_no_servers_is_a_problem(self):
        out = self._out()
        entries = [{"id": "empty-server", "type": "mcp",
                    "source": self._spec(json.dumps({"mcpServers": {}})),
                    "targets": "[opencode]"}]
        problems, _ = G.build(out, entries, self.MATRIX)
        self.assertTrue(any("empty-server" in p for p in problems), problems)

    def test_a_colliding_server_name_is_a_problem(self):
        """opencode's `mcp` block is one flat namespace; a second `demo` would overwrite."""
        spec = json.dumps({"mcpServers": {"demo": {"type": "http", "url": "x"}}})
        out = self._out()
        entries = [
            {"id": "one-server", "type": "mcp", "source": self._spec(spec),
             "targets": "[opencode]"},
            {"id": "two-server", "type": "mcp", "source": self._spec(spec),
             "targets": "[opencode]"},
        ]
        problems, _ = G.build(out, entries, self.MATRIX)
        self.assertTrue(any("collides" in p and "two-server" in p for p in problems), problems)

    def test_fragment_is_stable_regardless_of_entry_order(self):
        a = self._spec(json.dumps({"mcpServers": {"zed": {"type": "http", "url": "z"}}}))
        b = self._spec(json.dumps({"mcpServers": {"abe": {"type": "http", "url": "a"}}}))
        first, second = self._out(), self._out()
        mk = lambda p, i: {"id": i, "type": "mcp", "source": p, "targets": "[opencode]"}  # noqa: E731
        self.assertEqual(
            G.build(first, [mk(a, "z-server"), mk(b, "a-server")], self.MATRIX)[0], [])
        self.assertEqual(
            G.build(second, [mk(b, "a-server"), mk(a, "z-server")], self.MATRIX)[0], [])
        with open(os.path.join(first, "opencode.jsonc"), encoding="utf-8") as fh:
            one = fh.read()
        with open(os.path.join(second, "opencode.jsonc"), encoding="utf-8") as fh:
            two = fh.read()
        self.assertEqual(one, two)


class TestOutMode(unittest.TestCase):
    """The install-time CLI contract (ADR 0017): --out builds the laydown, never clobbers."""

    def test_out_builds_full_laydown(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        out = os.path.join(d, "lane")
        self.assertEqual(G.main(["--out", out]), 0)
        for expected in ("install.sh", "opencode.jsonc", "README.md", "skills", "agents"):
            self.assertTrue(os.path.exists(os.path.join(out, expected)), expected)
        self.assertTrue(os.access(os.path.join(out, "install.sh"), os.X_OK))

    def test_out_refuses_non_empty_dir(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        with open(os.path.join(d, "occupied.txt"), "w") as fh:
            fh.write("x")
        self.assertEqual(G.main(["--out", d]), 1)

    def test_agent_color_is_dropped(self):
        # opencode 1.18 rejects CC named colors at config load (verified live) — the
        # transform must not emit `color:` at all.
        out, _, _ = G.transform_agent(CC_AGENT, TR, "scout")
        fm, _ = G.split_frontmatter(out)
        self.assertNotIn("color", fm)


class TestDeterminism(unittest.TestCase):
    def test_two_builds_identical(self):
        entries = parse_roster(os.path.join(REPO, "primitives-core.yaml"))
        a = tempfile.mkdtemp()
        b = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, a, True)
        self.addCleanup(shutil.rmtree, b, True)
        first = G.build(a, entries, TR)
        second = G.build(b, entries, TR)
        self.assertEqual(first[0], [])
        self.assertEqual(first, second)  # notices are part of the deterministic output
        self.assertTrue(G._identical(a, b))


class TestMatrixCompleteness(unittest.TestCase):
    """check_roster's completeness gate (decision-009): what catches matrix drift is a check,
    not a version stamp. It lives in check_roster.py because gen_opencode imports from it."""

    AGENT = """---
name: drifter
description: An agent the matrix does not fully describe.
model: haiku
tools: Read, Telepathy
vibes: high
---

Body.
"""

    def _agents_dir(self, text):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        with open(os.path.join(d, "drifter.md"), "w", encoding="utf-8") as fh:
            fh.write(text)
        return d

    def _clean_agent(self):
        return (self.AGENT.replace("tools: Read, Telepathy", "tools: Read")
                          .replace("vibes: high\n", ""))

    def test_real_tree_is_green(self):
        self.assertEqual(CR.check_matrix_completeness(), [])

    def test_undeclared_tool_and_field_go_red(self):
        problems = CR.check_matrix_completeness(agents_dir=self._agents_dir(self.AGENT))
        self.assertTrue(any("Telepathy" in p for p in problems), problems)
        self.assertTrue(any("vibes" in p for p in problems), problems)

    def test_clean_fixture_agent_is_green(self):
        self.assertEqual(
            CR.check_matrix_completeness(agents_dir=self._agents_dir(self._clean_agent())), [])

    def test_unpinned_model_goes_red(self):
        agent = self._clean_agent().replace("model: haiku", "model: mystery")
        problems = CR.check_matrix_completeness(agents_dir=self._agents_dir(agent))
        self.assertTrue(any("mystery" in p for p in problems), problems)

    def test_family_readme_is_not_an_agent(self):
        d = self._agents_dir(self._clean_agent())
        with open(os.path.join(d, "README.md"), "w", encoding="utf-8") as fh:
            fh.write("# agents\n")
        self.assertEqual(CR.check_matrix_completeness(agents_dir=d), [])

    def test_bad_vocabulary_in_the_matrix_goes_red(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        path = os.path.join(d, "translation.yaml")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("tool_capabilities:\n  - tool: Read\n    capability: telekinesis\n"
                     "    opencode: read\nfield_treatments:\n  - field: name\n"
                     "    treatment: launder\n")
        problems = CR.check_matrix_completeness(
            agents_dir=self._agents_dir(self._clean_agent()), translation_path=path)
        self.assertTrue(any("telekinesis" in p for p in problems), problems)
        self.assertTrue(any("launder" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
