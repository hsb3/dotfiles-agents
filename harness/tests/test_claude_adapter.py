"""ClaudeAdapter — injection, invocation, env scrub, parse_log, success, preflight.

Ports the workbench TestInjection + TestParseStream and adds coverage for the
adapter-API surface (invocation argv shape, CLAUDECODE scrub, allow_bash,
unknown-kind -> unsupported skip).
"""

import json
import os
import shutil
import subprocess
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


def _restore_env(key, previous):
    """Put an os.environ key back exactly as it was (absent stays absent)."""
    if previous is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = previous


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

    def test_agent_duplicate_names_fail_before_injection(self):
        # Removing the adapter's shared preflight would collapse these two
        # definitions into one --agents entry.
        agent = os.path.join(self.tmp, "agents")
        _write(os.path.join(agent, "one.md"), "---\nname: same\n---\none")
        _write(os.path.join(agent, "two.md"), "---\nname: same\n---\ntwo")
        with self.assertRaisesRegex(ValueError, "duplicate agent name 'same'"):
            self.a.inject("agent", agent, self.tmp)
        self.assertEqual(os.listdir(self.tmp), ["agents"])

    def test_unknown_kind_is_unsupported_skip(self):
        # Design change from the workbench (which raised): an unhostable kind is
        # an explicit supported=False skip, never a crash (DESIGN §3).
        inj = self.a.inject("hook", "/x", self.tmp)
        self.assertFalse(inj.supported)
        self.assertEqual(inj.flags, [])


class TestInvocation(unittest.TestCase):
    def setUp(self):
        self.a = ClaudeAdapter()
        # A real, writable run tmpdir so invocation() can materialise its
        # per-run config dir + apiKeyHelper (workspace == <run_tmp>/ws).
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.ws = os.path.join(self.tmp, "ws")
        os.makedirs(self.ws)

    def _allowed(self, argv):
        return argv[argv.index("--allowedTools") + 1].split(",")

    def test_argv_shape_and_model(self):
        argv, _env = self.a.invocation(
            "do the thing", self.ws, "claude-sonnet-5",
            Injection(["--plugin-dir", "/p"]),
        )
        self.assertEqual(argv[:2], ["claude", "-p"])
        self.assertIn("do the thing", argv)
        self.assertEqual(argv[argv.index("--output-format") + 1], "stream-json")
        self.assertIn("--verbose", argv)
        self.assertEqual(argv[argv.index("--permission-mode") + 1], "acceptEdits")
        self.assertIn("--plugin-dir", argv)
        self.assertEqual(argv[argv.index("--model") + 1], "claude-sonnet-5")

    def test_bare_is_dropped(self):
        # --bare set CLAUDE_CODE_SIMPLE=1 which stripped Skill/Task from the
        # advertised toolset (#170). It must NOT be in the argv anymore.
        argv, _env = self.a.invocation("p", self.ws, None, Injection())
        self.assertNotIn("--bare", argv)

    def test_allowed_tools_surface_skill_and_task(self):
        # The regression at the heart of #170: Skill (invoke an injected skill)
        # and Task (invoke an injected agent) must be in the allowlist.
        argv, _env = self.a.invocation("p", self.ws, None, Injection())
        allowed = self._allowed(argv)
        for tool in ("Skill", "Task", "Bash", "Edit", "Read", "Write", "Grep", "Glob"):
            self.assertIn(tool, allowed)

    def test_injection_kinds_map_to_needed_tools(self):
        # Assert each injection kind's required tool is auto-allowed: a skill needs
        # Skill (to invoke the injected skill), an agent needs Task (to dispatch the
        # injected subagent), a plugin may add either so needs both. Injection is
        # constant across kinds here, so the invariant is on the allowlist itself.
        need = {"skill": ["Skill"], "agent": ["Task"], "plugin": ["Skill", "Task"]}
        allowed = set(ClaudeAdapter.ALLOWED_TOOLS.split(","))
        for kind, required in need.items():
            for tool in required:
                self.assertIn(tool, allowed, f"{kind} needs {tool} auto-allowed")
        # And the tool actually reaches the argv unchanged.
        argv, _env = self.a.invocation("p", self.ws, None, Injection())
        self.assertEqual(set(self._allowed(argv)), allowed)

    def test_env_key_auth_helper_and_isolated_config(self):
        # Option Z: dropping --bare loses env-key-strict auth + config isolation;
        # we restore both — an apiKeyHelper via --settings and a fresh
        # CLAUDE_CONFIG_DIR beside the workspace (cleaned up with the run tmp).
        argv, env = self.a.invocation("p", self.ws, None, Injection())
        settings = json.loads(argv[argv.index("--settings") + 1])
        self.assertIn("apiKeyHelper", settings)
        self.assertTrue(os.path.isfile(settings["apiKeyHelper"]))
        self.assertTrue(os.access(settings["apiKeyHelper"], os.X_OK))
        self.assertIn("CLAUDE_CONFIG_DIR", env)
        self.assertTrue(os.path.isdir(env["CLAUDE_CONFIG_DIR"]))
        # config dir + helper live under the run tmp, not the workspace itself.
        self.assertTrue(env["CLAUDE_CONFIG_DIR"].startswith(self.tmp))

    def test_helper_echoes_env_key(self):
        # The apiKeyHelper must emit exactly $ANTHROPIC_API_KEY at run time.
        argv, _env = self.a.invocation("p", self.ws, None, Injection())
        helper = json.loads(argv[argv.index("--settings") + 1])["apiKeyHelper"]
        out = subprocess.run(
            [helper], capture_output=True, text=True,
            env={"ANTHROPIC_API_KEY": "sk-test-123", "PATH": os.environ.get("PATH", "")},
        )
        self.assertEqual(out.stdout, "sk-test-123")

    def test_isolation_contract(self):
        # task-22 gap 1: one place asserting the whole isolation contract on the
        # CONSTRUCTED env+argv (no subprocess). Every layer the CLI can load host
        # state from must be closed: throwaway HOME, throwaway config roots, no
        # settings-file sources, no foreign MCP config, no bleed env vars.
        bleed = {
            "CLAUDECODE": "1",
            "CLAUDE_CODE_ENTRYPOINT": "cli",
            "CLAUDE_PLUGIN_ROOT": "/host/plugins",
            "CLAUDE_CONFIG_DIR": "/host/.claude",
            "XDG_CONFIG_HOME": "/host/.config",
            "ANTHROPIC_API_KEY": "sk-test-contract",
        }
        for key, val in bleed.items():
            self.addCleanup(_restore_env, key, os.environ.get(key))
            os.environ[key] = val

        argv, env = self.a.invocation(
            "p", self.ws, None, Injection(["--plugin-dir", "/p"])
        )

        # 1. Throwaway HOME inside the run tmp (cleaned up with it), never the user's.
        self.assertTrue(env["HOME"].startswith(self.tmp + os.sep))
        self.assertNotEqual(
            os.path.realpath(env["HOME"]), os.path.realpath(os.environ["HOME"])
        )
        self.assertTrue(os.path.isdir(env["HOME"]))
        # 2. HOME-adjacent + claude config roots point inside the throwaway tree.
        self.assertTrue(env["XDG_CONFIG_HOME"].startswith(env["HOME"] + os.sep))
        self.assertTrue(os.path.isdir(env["XDG_CONFIG_HOME"]))
        self.assertTrue(env["CLAUDE_CONFIG_DIR"].startswith(self.tmp + os.sep))
        self.assertTrue(os.path.isdir(env["CLAUDE_CONFIG_DIR"]))
        # 3. No user/project/local settings files, no foreign MCP servers.
        self.assertEqual(argv[argv.index("--setting-sources") + 1], "")
        self.assertIn("--strict-mcp-config", argv)
        # 4. --settings still carries an executable apiKeyHelper (auth survives the
        #    empty setting-sources list; probe: apiKeySource == apiKeyHelper).
        helper = json.loads(argv[argv.index("--settings") + 1])["apiKeyHelper"]
        self.assertTrue(os.path.isfile(helper))
        self.assertTrue(os.access(helper, os.X_OK))
        # 5. Bleed vars are gone / overwritten even though os.environ had them.
        for key in ClaudeAdapter.CONFIG_BLEED_ENV:
            if key in ("CLAUDE_CONFIG_DIR", "XDG_CONFIG_HOME"):
                self.assertNotEqual(env[key], bleed[key])  # replaced, not inherited
            else:
                self.assertNotIn(key, env)
        # 6. PATH + the API key must NOT be scrubbed (CLI lookup + helper input).
        self.assertEqual(env.get("PATH"), os.environ.get("PATH"))
        self.assertEqual(env["ANTHROPIC_API_KEY"], "sk-test-contract")

    def test_non_writable_run_dir_falls_back(self):
        # A stub workspace whose parent is not writable must not crash — and must
        # NOT degrade to the host config either (that hole was the task-22 gap).
        # The adapter falls back to a private temp isolation root instead.
        ro = os.path.join(self.tmp, "ro")
        os.makedirs(ro)
        os.chmod(ro, 0o500)
        self.addCleanup(os.chmod, ro, 0o700)

        argv, env = self.a.invocation("p", os.path.join(ro, "ws"), None, Injection())

        self.assertIn("Skill", self._allowed(argv))
        self.assertIn("--settings", argv)
        helper = json.loads(argv[argv.index("--settings") + 1])["apiKeyHelper"]
        self.assertTrue(os.access(helper, os.X_OK))
        self.assertTrue(os.path.isdir(env["CLAUDE_CONFIG_DIR"]))
        self.assertTrue(os.path.isdir(env["HOME"]))
        self.assertNotEqual(
            os.path.realpath(env["HOME"]), os.path.realpath(os.environ["HOME"])
        )
        self.assertFalse(env["HOME"].startswith(ro + os.sep))  # not the dead run dir
        self.assertTrue(env["XDG_CONFIG_HOME"].startswith(env["HOME"] + os.sep))
        self.assertEqual(argv[argv.index("--setting-sources") + 1], "")

    def test_unbuildable_isolation_raises_rather_than_inheriting(self):
        # Last resort: if even the temp root cannot be made, the adapter refuses to
        # run instead of silently handing the trial the operator's real config.
        ro = os.path.join(self.tmp, "ro2")
        os.makedirs(ro)
        os.chmod(ro, 0o500)
        self.addCleanup(os.chmod, ro, 0o700)

        class _NoTemp:
            @staticmethod
            def mkdtemp(*_a, **_kw):
                raise OSError("no temp dir")

        orig = claude_mod.tempfile
        claude_mod.tempfile = _NoTemp
        try:
            with self.assertRaises(RuntimeError) as ctx:
                self.a.invocation("p", os.path.join(ro, "ws"), None, Injection())
        finally:
            claude_mod.tempfile = orig
        self.assertIn("isolated", str(ctx.exception))

    def test_no_model_omits_flag(self):
        argv, _env = self.a.invocation("p", self.ws, None, Injection())
        self.assertNotIn("--model", argv)

    def test_env_scrubs_claudecode(self):
        os.environ["CLAUDECODE"] = "1"
        try:
            _argv, env = self.a.invocation("p", self.ws, None, Injection())
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
                    "usage": {
                        "input_tokens": 58,
                        "output_tokens": 3251,
                        "cache_read_input_tokens": 201107,
                        "cache_creation_input_tokens": 42055,
                    },
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
        # Token usage normalized from the result event's `usage` block.
        self.assertEqual(rec.input_tokens, 58)
        self.assertEqual(rec.output_tokens, 3251)
        self.assertEqual(rec.cache_read_tokens, 201107)
        self.assertEqual(rec.cache_creation_tokens, 42055)

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
