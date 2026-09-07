"""gen_opencode unit tests (install-time laydown, ADR 0017).

Covers the agent frontmatter transform (the real mapping rules, not just shape), the
opencode skill-name/description validators, the exclusion-vs-roster conflict guard,
build determinism against the real roster (two temp builds must be byte-identical),
and the --out CLI contract (builds a full laydown; refuses a non-empty target).
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import gen_opencode as G  # noqa: E402
from check_roster import parse_roster  # noqa: E402

ALIASES = {"haiku": "anthropic/claude-haiku-4-5", "opus": "anthropic/claude-opus-4-8"}

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
    def test_mapping_rules(self):
        out = G.transform_agent(CC_AGENT, ALIASES)
        fm, body = G.split_frontmatter(out)
        self.assertNotIn("name", fm)  # filename carries identity
        self.assertEqual(fm["mode"], "subagent")
        self.assertEqual(fm["model"], "anthropic/claude-haiku-4-5")
        self.assertEqual(fm["steps"], "15")
        self.assertNotIn("effort", fm)  # CC-only knob dropped
        self.assertIn("Body text survives verbatim.", body)

    def test_permission_inversion(self):
        read_only = G.transform_agent(CC_AGENT, ALIASES)
        self.assertIn("write: deny", read_only)
        self.assertIn("bash: deny", read_only)
        self.assertIn("read: allow", read_only)
        builder = G.transform_agent(
            CC_AGENT.replace("tools: Read, Grep, Glob", "tools: Read, Edit, Write, Bash"),
            ALIASES,
        )
        self.assertIn("write: allow", builder)
        self.assertIn("bash: allow", builder)

    def test_unmapped_bare_model_is_dropped(self):
        out = G.transform_agent(CC_AGENT.replace("model: haiku", "model: mystery"), {})
        fm, _ = G.split_frontmatter(out)
        self.assertNotIn("model", fm)  # bare alias with no pin: drop, never ship unprefixed


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
            "exclusions": [{"id": "update-config", "reason": "cc-specific"}],
        }
        entries = [{
            "id": "update-config", "type": "skill",
            "source": "primitives-core/skills/update-config",
            "targets": "[claude-code, opencode]",
        }]
        problems = G.build(d, entries, translation)
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
            "exclusions": [],
        }
        entries = [{
            "id": "activate", "type": "command",
            "source": "primitives-core/commands/activate.md",
            "targets": "[claude-code]",
        }]
        problems = G.build(d, entries, translation)
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
        self.assertEqual(G.build(out, entries, self.MATRIX), [])
        self.assertEqual(self._fragment(out)["mcp"], {"demo": {
            "type": "remote", "url": "{env:DEMO_URL}/mcp",
            "headers": {"Authorization": "Bearer {env:DEMO_TOKEN}"}}})

    def test_local_server_renders_as_a_command(self):
        spec = self._spec(json.dumps({"mcpServers": {"fs": {
            "type": "stdio", "command": "npx", "args": ["-y", "server-fs"],
            "env": {"KEY": "${MY_KEY}"}}}}))
        out = self._out()
        entries = [{"id": "fs-server", "type": "mcp", "source": spec, "targets": "[opencode]"}]
        self.assertEqual(G.build(out, entries, self.MATRIX), [])
        self.assertEqual(self._fragment(out)["mcp"], {"fs": {
            "type": "local", "command": ["npx", "-y", "server-fs"],
            "environment": {"KEY": "{env:MY_KEY}"}}})

    def test_rendered_server_is_named_in_the_lane_readme(self):
        spec = self._spec(json.dumps({"mcpServers": {"demo": {
            "type": "http", "url": "https://mcp.example.com/mcp"}}}))
        out = self._out()
        entries = [{"id": "demo-server", "type": "mcp", "source": spec, "targets": "[opencode]"}]
        self.assertEqual(G.build(out, entries, self.MATRIX), [])
        readme = self._readme(out)
        self.assertIn("1 MCP server", readme)
        self.assertIn("`demo-server`", readme)  # the trace back to the roster entry

    def test_claude_code_only_mcp_entry_stays_a_recorded_exclusion(self):
        spec = self._spec(json.dumps({"mcpServers": {"demo": {"type": "http", "url": "x"}}}))
        out = self._out()
        entries = [{"id": "demo-server", "type": "mcp", "source": spec,
                    "targets": "[claude-code]"}]
        self.assertEqual(G.build(out, entries, self.MATRIX), [])
        self.assertIn(
            "| `demo-server` | mcp | roster targets do not include opencode |",
            self._readme(out))
        self.assertNotIn("mcp", self._fragment(out))

    def test_unrenderable_spec_is_a_problem_never_a_silent_drop(self):
        out = self._out()
        entries = [{"id": "broken-server", "type": "mcp", "source": self._spec("{ nope"),
                    "targets": "[opencode]"}]
        problems = G.build(out, entries, self.MATRIX)
        self.assertTrue(any("broken-server" in p for p in problems), problems)

    def test_server_with_no_transport_is_a_problem(self):
        spec = self._spec(json.dumps({"mcpServers": {"demo": {"type": "carrier-pigeon"}}}))
        out = self._out()
        entries = [{"id": "odd-server", "type": "mcp", "source": spec, "targets": "[opencode]"}]
        problems = G.build(out, entries, self.MATRIX)
        self.assertTrue(any("odd-server" in p and "demo" in p for p in problems), problems)

    def test_fragment_is_stable_regardless_of_entry_order(self):
        a = self._spec(json.dumps({"mcpServers": {"zed": {"type": "http", "url": "z"}}}))
        b = self._spec(json.dumps({"mcpServers": {"abe": {"type": "http", "url": "a"}}}))
        first, second = self._out(), self._out()
        mk = lambda p, i: {"id": i, "type": "mcp", "source": p, "targets": "[opencode]"}  # noqa: E731
        self.assertEqual(G.build(first, [mk(a, "z-server"), mk(b, "a-server")], self.MATRIX), [])
        self.assertEqual(G.build(second, [mk(b, "a-server"), mk(a, "z-server")], self.MATRIX), [])
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
        out = G.transform_agent(CC_AGENT, ALIASES)
        fm, _ = G.split_frontmatter(out)
        self.assertNotIn("color", fm)


class TestDeterminism(unittest.TestCase):
    def test_two_builds_identical(self):
        entries = parse_roster(os.path.join(REPO, "primitives-core.yaml"))
        translation = G.parse_translation(os.path.join(REPO, "translation.yaml"))
        a = tempfile.mkdtemp()
        b = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, a, True)
        self.addCleanup(shutil.rmtree, b, True)
        self.assertEqual(G.build(a, entries, translation), [])
        self.assertEqual(G.build(b, entries, translation), [])
        self.assertTrue(G._identical(a, b))


if __name__ == "__main__":
    unittest.main()
