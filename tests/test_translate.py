"""Unit tests for the pure render/transform/parse logic in scripts/translate.py.

These cover the CORRECTNESS the drift guards cannot: the drift guard only proves committed
targets/ equals a fresh rebuild, never that the rebuild is right. A bug in mcp_to_opencode (say)
emits wrong-but-consistent output that `make ci` passes clean -- these tests catch that.

Stdlib-only (unittest), so `make test` runs in CI with zero install. Run: python3 -m unittest.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import translate as T  # noqa: E402


def _write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


class ListHelper(unittest.TestCase):
    def test_bracketed(self):
        self.assertEqual(
            T._list("[claude-code, opencode]"), ["claude-code", "opencode"]
        )

    def test_empty_bracket_and_blank(self):
        self.assertEqual(T._list("[]"), [])
        self.assertEqual(T._list(""), [])

    def test_scalar(self):
        self.assertEqual(T._list("core"), ["core"])


class McpRenderStdio(unittest.TestCase):
    SPEC = {
        "name": "agent-bus",
        "transport": "stdio",
        "command": "agent-bus",
        "args": ["serve"],
        "env": {},
    }

    def test_claude(self):
        out = T.mcp_to_claude(self.SPEC)["mcpServers"]["agent-bus"]
        self.assertEqual(out["type"], "stdio")
        self.assertEqual(out["command"], "agent-bus")
        self.assertEqual(out["args"], ["serve"])
        self.assertEqual(out["env"], {})

    def test_opencode_command_is_one_array(self):
        out = T.mcp_to_opencode(self.SPEC)["mcp"]["agent-bus"]
        self.assertEqual(out["type"], "local")
        # command + args collapse into a single array -- the regression this asserts against
        self.assertEqual(out["command"], ["agent-bus", "serve"])
        self.assertTrue(out["enabled"])
        # empty env => no `environment` key
        self.assertNotIn("environment", out)

    def test_opencode_env_becomes_environment(self):
        spec = dict(
            self.SPEC,
            env={"GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"},
        )
        out = T.mcp_to_opencode(spec)["mcp"]["agent-bus"]
        self.assertEqual(
            out["environment"],
            {"GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"},
        )


class McpRenderHttp(unittest.TestCase):
    SPEC = {
        "name": "claude_design",
        "transport": "http",
        "url": "https://api.anthropic.com/v1/design/mcp",
        "headers": {},
    }

    def test_claude(self):
        out = T.mcp_to_claude(self.SPEC)["mcpServers"]["claude_design"]
        self.assertEqual(out, {"type": "http", "url": self.SPEC["url"]})

    def test_opencode(self):
        out = T.mcp_to_opencode(self.SPEC)["mcp"]["claude_design"]
        self.assertEqual(
            out, {"type": "remote", "url": self.SPEC["url"], "enabled": True}
        )

    def test_cma_remote(self):
        out = T.mcp_to_cma(self.SPEC)
        self.assertEqual(
            out,
            {
                "mcp_servers": [
                    {"type": "url", "url": self.SPEC["url"], "name": "claude_design"}
                ]
            },
        )

    def test_headers_passed_through_when_present(self):
        spec = dict(self.SPEC, headers={"X-Auth": "${TOKEN}"})
        self.assertEqual(
            T.mcp_to_claude(spec)["mcpServers"]["claude_design"]["headers"],
            {"X-Auth": "${TOKEN}"},
        )
        self.assertEqual(
            T.mcp_to_opencode(spec)["mcp"]["claude_design"]["headers"],
            {"X-Auth": "${TOKEN}"},
        )


class AgentTransforms(unittest.TestCase):
    AGENT = (
        "---\n"
        "name: board-analyst\n"
        "model: sonnet\n"
        "color: blue\n"
        "description: >-\n"
        "  Line one.\n"
        "  Line two with <example> literal.\n"
        "---\n"
        "You are a board analyst.\n\nDo the thing.\n"
    )

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "board-analyst.md")
        _write(self.path, self.AGENT)

    def test_opencode_drops_fields_and_adds_mode(self):
        out = T.transform_agent_opencode(self.path)
        self.assertIn("mode: subagent", out)
        self.assertNotIn("name: board-analyst", out)
        self.assertNotIn("model: sonnet", out)
        self.assertNotIn("color: blue", out)

    def test_opencode_preserves_description_verbatim(self):
        out = T.transform_agent_opencode(self.path)
        # the multi-line description (with its literal <example>) survives byte-for-byte
        self.assertIn("Line two with <example> literal.", out)

    def test_agent_system_strips_frontmatter(self):
        sysmsg = T.agent_system(self.path)
        self.assertTrue(sysmsg.startswith("You are a board analyst."))
        self.assertNotIn("---", sysmsg)
        self.assertNotIn("name: board-analyst", sysmsg)


class SkillDisplayTitle(unittest.TestCase):
    def test_extracts_name(self):
        d = tempfile.mkdtemp()
        _write(
            os.path.join(d, "SKILL.md"),
            "---\nname: api-server-design\ndescription: x\n---\n# body\n",
        )
        self.assertEqual(T.skill_display_title(d), "api-server-design")

    def test_falls_back_to_dirname(self):
        d = tempfile.mkdtemp()
        _write(os.path.join(d, "SKILL.md"), "# no frontmatter\n")
        self.assertEqual(T.skill_display_title(d), os.path.basename(d))


class Sha256Path(unittest.TestCase):
    def test_dir_hash_is_order_independent_and_excludes_dsstore(self):
        a, b = tempfile.mkdtemp(), tempfile.mkdtemp()
        # same content, written in different order, plus a .DS_Store only in one
        _write(os.path.join(a, "z.txt"), "zed")
        _write(os.path.join(a, "a.txt"), "aye")
        _write(os.path.join(b, "a.txt"), "aye")
        _write(os.path.join(b, "z.txt"), "zed")
        _write(os.path.join(b, ".DS_Store"), "junk")
        self.assertEqual(T.sha256_path(a), T.sha256_path(b))

    def test_content_change_changes_hash(self):
        a = tempfile.mkdtemp()
        _write(os.path.join(a, "f.txt"), "one")
        h1 = T.sha256_path(a)
        _write(os.path.join(a, "f.txt"), "two")
        self.assertNotEqual(h1, T.sha256_path(a))


class Parsers(unittest.TestCase):
    """Round-trip the REAL repo files -- these break if a parser regresses against live data."""

    def test_roster_has_mcp_primitives(self):
        roster = T.parse_roster(T.ROSTER)
        by_id = {e["id"]: e for e in roster}
        self.assertIn("agent-bus", by_id)
        self.assertEqual(by_id["agent-bus"]["type"], "mcp")
        self.assertEqual(by_id["agent-bus"]["targets"], ["claude-code", "opencode"])

    def test_externals_has_kind_mcp(self):
        ext = {e["id"]: e for e in T.parse_externals(T.EXTERNALS)}
        self.assertEqual(ext["github"]["kind"], "mcp")
        self.assertEqual(ext["github"]["spec"], "externals/mcp/github.json")
        self.assertIn("claude-agents", ext["claude_design"]["targets"])

    def test_capabilities_matrix(self):
        caps = T.parse_capabilities(T.CONFIG)
        self.assertEqual(caps["mcp"]["claude-code"], "render")
        self.assertEqual(caps["skill"]["claude-code"], "native")
        self.assertEqual(caps["hook"]["opencode"], "unsupported")

    def test_cma_default_model_present(self):
        opts = T.parse_cma_options(T.CONFIG)
        self.assertTrue(opts.get("default_model"))

    def test_plugins_parse(self):
        meta = T.parse_plugins(T.PLUGINS_YAML)
        self.assertIsInstance(meta, dict)
        self.assertTrue(meta)  # at least one plugin


if __name__ == "__main__":
    unittest.main()
