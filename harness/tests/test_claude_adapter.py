"""ClaudeAdapter — injection, invocation, env scrub, parse_log, success, preflight.

Ports the workbench TestInjection + TestParseStream and adds coverage for the
adapter-API surface (invocation argv shape, CLAUDECODE scrub, allow_bash,
unknown-kind -> unsupported skip).
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import agent_harness.adapters.claude as claude_mod  # noqa: E402
from agent_harness.adapters.base import Injection  # noqa: E402
from agent_harness.adapters.claude import ClaudeAdapter  # noqa: E402


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


class TestInjection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.a = ClaudeAdapter()

    def test_synth_plugin_wraps_skill(self):
        skill = os.path.join(self.tmp, "my-skill")
        _write(os.path.join(skill, "SKILL.md"), "---\nname: my-skill\n---\nbody")
        plug = ClaudeAdapter._synth_plugin(skill, "my-skill", self.tmp)
        with open(os.path.join(plug, ".claude-plugin", "plugin.json")) as fh:
            manifest = json.load(fh)
        self.assertEqual(manifest["name"], "eval-my-skill")
        self.assertTrue(
            os.path.isfile(os.path.join(plug, "skills", "my-skill", "SKILL.md"))
        )

    def test_skill_injection_returns_supported_plugin_flags(self):
        skill = os.path.join(self.tmp, "my-skill")
        _write(os.path.join(skill, "SKILL.md"), "---\nname: my-skill\n---\nbody")
        inj = self.a.inject("skill", skill, self.tmp)
        self.assertTrue(inj.supported)
        self.assertEqual(inj.flags[0], "--plugin-dir")
        self.assertTrue(os.path.isdir(inj.flags[1]))
        self.assertEqual(inj.files, [inj.flags[1]])

    def test_plugin_flags_point_at_candidate(self):
        inj = self.a.inject("plugin", "/x/cand", self.tmp)
        self.assertEqual(inj.flags, ["--plugin-dir", "/x/cand"])
        self.assertTrue(inj.supported)

    def test_agent_flags_carry_definitions(self):
        agent = os.path.join(self.tmp, "my-agent")
        _write(
            os.path.join(agent, "my-agent.md"),
            "---\nname: my-agent\ndescription: does things\n---\nSystem prompt here.",
        )
        inj = self.a.inject("agent", agent, self.tmp)
        self.assertEqual(inj.flags[0], "--agents")
        defs = json.loads(inj.flags[1])
        self.assertEqual(defs["my-agent"]["description"], "does things")
        self.assertIn("System prompt here.", defs["my-agent"]["prompt"])

    def test_unknown_kind_is_unsupported_skip(self):
        # Design change from the workbench (which raised): an unhostable kind is
        # an explicit supported=False skip, never a crash (DESIGN §3).
        inj = self.a.inject("hook", "/x", self.tmp)
        self.assertFalse(inj.supported)
        self.assertEqual(inj.flags, [])


class TestInvocation(unittest.TestCase):
    def setUp(self):
        self.a = ClaudeAdapter()

    def test_argv_shape_and_model(self):
        argv, _env = self.a.invocation(
            "do the thing", "/ws", "claude-sonnet-5", Injection(["--plugin-dir", "/p"])
        )
        self.assertEqual(argv[:2], ["claude", "-p"])
        self.assertIn("do the thing", argv)
        self.assertIn("--bare", argv)
        self.assertEqual(argv[argv.index("--output-format") + 1], "stream-json")
        self.assertIn("--verbose", argv)
        self.assertEqual(argv[argv.index("--permission-mode") + 1], "acceptEdits")
        self.assertIn("--plugin-dir", argv)
        self.assertEqual(argv[-2:], ["--model", "claude-sonnet-5"])

    def test_no_model_omits_flag(self):
        argv, _env = self.a.invocation("p", "/ws", None, Injection())
        self.assertNotIn("--model", argv)

    def test_allow_bash_adds_tool(self):
        argv, _env = ClaudeAdapter(allow_bash=True).invocation("p", "/ws", None, Injection())
        self.assertEqual(argv[argv.index("--allowedTools") + 1], "Bash")
        argv2, _e = ClaudeAdapter(allow_bash=False).invocation("p", "/ws", None, Injection())
        self.assertNotIn("Bash", argv2)

    def test_env_scrubs_claudecode(self):
        os.environ["CLAUDECODE"] = "1"
        try:
            _argv, env = self.a.invocation("p", "/ws", None, Injection())
            self.assertNotIn("CLAUDECODE", env)
        finally:
            os.environ.pop("CLAUDECODE", None)


class TestParseLog(unittest.TestCase):
    def setUp(self):
        self.a = ClaudeAdapter()

    def test_folds_events(self):
        lines = [
            json.dumps(
                {
                    "type": "system",
                    "subtype": "init",
                    "plugins": [{"name": "eval-x", "path": "/p"}],
                    "plugin_errors": [{"plugin": "eval-x", "message": "boom"}],
                }
            ),
            "not json",
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {"type": "text", "text": "hi"},
                            {"type": "tool_use", "name": "Skill", "input": {}},
                            {"type": "tool_use", "name": "Write", "input": {}},
                        ]
                    },
                }
            ),
            json.dumps(
                {
                    "type": "result",
                    "result": "done",
                    "total_cost_usd": 0.12,
                    "duration_ms": 4200,
                    "num_turns": 3,
                }
            ),
        ]
        rec = self.a.parse_log("\n".join(lines))
        self.assertEqual([p["name"] for p in rec.plugins], ["eval-x"])
        self.assertEqual(len(rec.plugin_errors), 1)
        self.assertEqual(rec.tool_names, ["Skill", "Write"])
        self.assertTrue(rec.skill_used)
        self.assertEqual(rec.result, "done")
        self.assertEqual(rec.cost_usd, 0.12)
        self.assertEqual(rec.num_turns, 3)

    def test_empty_log_is_safe(self):
        rec = self.a.parse_log("")
        self.assertFalse(rec.skill_used)
        self.assertEqual(rec.plugins, [])
        self.assertEqual(rec.plugin_errors, [])


class TestSuccessAndPreflight(unittest.TestCase):
    def setUp(self):
        self.a = ClaudeAdapter()

    def test_success_is_exit_zero(self):
        from agent_harness.adapters.base import NormalizedRecord

        self.assertTrue(self.a.success(0, NormalizedRecord()))
        self.assertFalse(self.a.success(1, NormalizedRecord()))
        self.assertFalse(self.a.success(-1, NormalizedRecord()))

    def test_preflight_returns_valid_token(self):
        self.assertIn(self.a.preflight(), ("ok", "missing", "noauth"))

    def test_preflight_missing_when_not_on_path(self):
        orig = claude_mod.shutil.which
        claude_mod.shutil.which = lambda _name: None
        try:
            self.assertEqual(self.a.preflight(), "missing")
        finally:
            claude_mod.shutil.which = orig

    def test_preflight_ok_when_on_path(self):
        orig = claude_mod.shutil.which
        claude_mod.shutil.which = lambda _name: "/usr/local/bin/claude"
        try:
            self.assertEqual(self.a.preflight(), "ok")
        finally:
            claude_mod.shutil.which = orig


if __name__ == "__main__":
    unittest.main()
