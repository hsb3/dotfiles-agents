"""OpencodeAdapter — injection, invocation, throwaway HOME, parse_log, preflight.

Mirrors test_claude_adapter.py coverage for the vendor seam, plus the opencode
specifics: config-dir injection (skill/agent), the stricter skill-name-regex skip
and the plugin skip, argv/env shape (throwaway HOME placement, OPENCODE_CONFIG_DIR,
env scrub, model provider-normalization), and parse_log against event fixtures
faithful to the observed opencode 1.18.0 `--format json` schema — including the
opencode#26855 missing-final-`step_finish` gap.

Also covers the CLI grid-cell expansion (``cli._cells``). No live CLI here —
fixtures only (a real live run is recorded in handoff-w2.md).
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import agent_harness.adapters.opencode as oc_mod  # noqa: E402
from agent_harness.adapters.base import Injection, NormalizedRecord  # noqa: E402
from agent_harness.adapters.opencode import OpencodeAdapter  # noqa: E402
from agent_harness import cli  # noqa: E402


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def _ev(etype, part, ts):
    """Build one opencode `--format json` envelope line (observed 1.18.0 schema)."""
    return json.dumps({"type": etype, "timestamp": ts, "sessionID": "ses_x", "part": part})


class TestInjection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.a = OpencodeAdapter()

    def _config_dir(self, inj):
        self.assertTrue(inj.supported)
        self.assertEqual(inj.flags, [])  # opencode injects via env, never flags
        self.assertEqual(len(inj.files), 1)
        return inj.files[0]

    def test_skill_injection_lays_down_config_dir(self):
        skill = os.path.join(self.tmp, "my-skill")
        _write(os.path.join(skill, "SKILL.md"), "---\nname: my-skill\n---\nbody")
        inj = self.a.inject("skill", skill, self.tmp)
        cfg = self._config_dir(inj)
        self.assertTrue(
            os.path.isfile(os.path.join(cfg, "skills", "my-skill", "SKILL.md"))
        )
        with open(os.path.join(cfg, "opencode.json")) as fh:
            manifest = json.load(fh)
        # Skill granted so a headless call never blocks on the default `ask`.
        self.assertEqual(manifest["permission"]["skill"]["my-skill"], "allow")
        self.assertEqual(manifest["$schema"], "https://opencode.ai/config.json")

    def test_skill_bad_name_is_unsupported_skip(self):
        # opencode's name regex is stricter than CC's; an invalid name is silently
        # invisible to opencode, so we skip loudly instead of injecting a dead skill.
        for bad in ("Bad_Name", "has_underscore", "Upper", "trailing-"):
            skill = os.path.join(self.tmp, bad)
            _write(os.path.join(skill, "SKILL.md"), "---\nname: x\n---\nbody")
            inj = self.a.inject("skill", skill, self.tmp)
            self.assertFalse(inj.supported, bad)
            self.assertEqual(inj.flags, [])
            self.assertEqual(inj.files, [])

    def test_plugin_is_unsupported_skip(self):
        # A CC plugin bundle (hooks) has no mechanical opencode translation (v1).
        plugin = os.path.join(self.tmp, "plug")
        _write(os.path.join(plugin, ".claude-plugin", "plugin.json"), "{}")
        inj = self.a.inject("plugin", plugin, self.tmp)
        self.assertFalse(inj.supported)
        self.assertEqual(inj.flags, [])

    def test_unknown_kind_is_unsupported_skip(self):
        inj = self.a.inject("hook", "/x", self.tmp)
        self.assertFalse(inj.supported)
        self.assertEqual(inj.flags, [])

    def test_agent_injection_translates_frontmatter(self):
        agent = os.path.join(self.tmp, "my-agent")
        _write(
            os.path.join(agent, "my-agent.md"),
            "---\nname: my-agent\ndescription: does things\n"
            "model: claude-sonnet-4-5\ntools: Read, Grep\n---\nSystem prompt here.",
        )
        inj = self.a.inject("agent", agent, self.tmp)
        cfg = self._config_dir(inj)
        path = os.path.join(cfg, "agents", "my-agent.md")
        self.assertTrue(os.path.isfile(path))
        with open(path) as fh:
            text = fh.read()
        self.assertIn("description: does things", text)
        self.assertIn("mode: subagent", text)  # CC subagent marker added
        self.assertIn("model: anthropic/claude-sonnet-4-5", text)  # provider prefix
        self.assertIn("System prompt here.", text)
        # tools allowlist -> permission map: unlisted write surfaces denied.
        self.assertIn("edit: deny", text)
        self.assertIn("bash: deny", text)
        self.assertIn("read: allow", text)
        self.assertIn("grep: allow", text)

    def test_agent_bare_model_dropped_when_absent(self):
        agent = os.path.join(self.tmp, "a")
        _write(
            os.path.join(agent, "a.md"),
            "---\nname: a\ndescription: d\n---\nbody",
        )
        inj = self.a.inject("agent", agent, self.tmp)
        with open(os.path.join(inj.files[0], "agents", "a.md")) as fh:
            text = fh.read()
        self.assertNotIn("model:", text)  # omitted -> inherits the run model
        self.assertIn("mode: subagent", text)

    def test_agent_duplicate_names_fail_before_config_injection(self):
        # Removing the adapter's shared preflight would overwrite one rendered
        # agent file and leave an oc-config directory behind.
        agent = os.path.join(self.tmp, "agents")
        _write(os.path.join(agent, "same.md"), "fallback body")
        _write(os.path.join(agent, "other.md"), "---\nname: same\n---\nother body")
        with self.assertRaisesRegex(ValueError, "duplicate agent name 'same'"):
            self.a.inject("agent", agent, self.tmp)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "oc-config")))


class TestInvocation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.ws = os.path.join(self.tmp, "ws")
        os.makedirs(self.ws)
        self.a = OpencodeAdapter()

    def test_argv_shape(self):
        argv, _env = self.a.invocation("do the thing", self.ws, "claude-haiku-4-5", Injection())
        self.assertEqual(argv[:3], ["opencode", "run", "do the thing"])
        self.assertEqual(argv[argv.index("--dir") + 1], self.ws)
        self.assertEqual(argv[argv.index("--format") + 1], "json")
        self.assertIn("--auto", argv)  # 1.18.0 permission bypass

    def test_model_provider_normalization(self):
        # bare id -> anthropic/<id>
        argv, _e = self.a.invocation("p", self.ws, "claude-sonnet-4-5", Injection())
        self.assertEqual(argv[argv.index("-m") + 1], "anthropic/claude-sonnet-4-5")
        # already-prefixed -> passthrough
        argv, _e = self.a.invocation("p", self.ws, "openai/gpt-5", Injection())
        self.assertEqual(argv[argv.index("-m") + 1], "openai/gpt-5")

    def test_model_default_falls_back_to_pinned(self):
        for m in (None, "default"):
            argv, _e = self.a.invocation("p", self.ws, m, Injection())
            self.assertEqual(argv[argv.index("-m") + 1], OpencodeAdapter.DEFAULT_MODEL)

    def test_throwaway_home_inside_tmpdir(self):
        _argv, env = self.a.invocation("p", self.ws, None, Injection())
        expected = os.path.join(self.tmp, "oc-home")
        self.assertEqual(env["HOME"], expected)
        self.assertTrue(os.path.isdir(expected))  # created so the CLI can populate it

    def test_config_dir_from_injection_files(self):
        cfg = os.path.join(self.tmp, "oc-config")
        os.makedirs(cfg)
        _argv, env = self.a.invocation("p", self.ws, None, Injection(files=[cfg]))
        self.assertEqual(env["OPENCODE_CONFIG_DIR"], cfg)

    def test_baseline_sets_no_config_dir(self):
        _argv, env = self.a.invocation("p", self.ws, None, Injection())
        self.assertNotIn("OPENCODE_CONFIG_DIR", env)

    def test_env_scrubs_inherited_opencode_config(self):
        for k in ("OPENCODE_CONFIG", "OPENCODE_CONFIG_CONTENT", "OPENCODE_CONFIG_DIR"):
            os.environ[k] = "stale"
        try:
            _argv, env = self.a.invocation("p", self.ws, None, Injection())
            self.assertNotIn("OPENCODE_CONFIG", env)
            self.assertNotIn("OPENCODE_CONFIG_CONTENT", env)
            self.assertNotIn("OPENCODE_CONFIG_DIR", env)  # not injecting -> unset
        finally:
            for k in ("OPENCODE_CONFIG", "OPENCODE_CONFIG_CONTENT", "OPENCODE_CONFIG_DIR"):
                os.environ.pop(k, None)

    def test_auth_env_passthrough(self):
        os.environ["ANTHROPIC_API_KEY"] = "sk-probe"
        try:
            _argv, env = self.a.invocation("p", self.ws, None, Injection())
            self.assertEqual(env["ANTHROPIC_API_KEY"], "sk-probe")
        finally:
            os.environ.pop("ANTHROPIC_API_KEY", None)


class TestParseLog(unittest.TestCase):
    def setUp(self):
        self.a = OpencodeAdapter()

    def _stream(self, drop_final_finish=False):
        events = [
            _ev("step_start", {"type": "step-start"}, 1000),
            _ev("text", {"type": "text", "text": "I'll create the file."}, 1000),
            _ev(
                "tool_use",
                {"type": "tool", "tool": "write", "state": {"status": "completed"}},
                1410,
            ),
            _ev("step_finish", {"type": "step-finish", "reason": "tool-calls", "cost": 0.0128}, 1411),
            _ev("step_start", {"type": "step-start"}, 2000),
            _ev("text", {"type": "text", "text": "Done."}, 2010),
            _ev("step_finish", {"type": "step-finish", "reason": "stop", "cost": 0.0013}, 2415),
        ]
        if drop_final_finish:
            events = events[:-1]
        return "\n".join(events)

    def test_folds_events(self):
        rec = self.a.parse_log(self._stream())
        self.assertEqual(rec.tool_names, ["write"])
        self.assertFalse(rec.skill_used)
        self.assertAlmostEqual(rec.cost_usd, 0.0128 + 0.0013)
        self.assertEqual(rec.num_turns, 2)  # two step_start
        self.assertEqual(rec.duration_ms, 2415 - 1000)  # max-min timestamp
        self.assertIn("Done.", rec.result)
        self.assertIn("I'll create the file.", rec.result)

    def test_missing_final_step_finish_is_graceful(self):
        # opencode#26855: the terminal step_finish can be absent. We scan the whole
        # stream, so cost still accrues from the earlier finish and duration from
        # the remaining timestamps — no crash, no assumption the last line is final.
        rec = self.a.parse_log(self._stream(drop_final_finish=True))
        self.assertAlmostEqual(rec.cost_usd, 0.0128)  # only the surviving finish
        self.assertEqual(rec.num_turns, 2)
        self.assertEqual(rec.duration_ms, 2010 - 1000)
        self.assertEqual(rec.tool_names, ["write"])

    def test_skill_tool_sets_skill_used(self):
        raw = "\n".join(
            [
                _ev("step_start", {"type": "step-start"}, 1),
                _ev("tool_use", {"type": "tool", "tool": "skill"}, 2),
                _ev("step_finish", {"type": "step-finish", "reason": "stop", "cost": 0.001}, 3),
            ]
        )
        rec = self.a.parse_log(raw)
        self.assertTrue(rec.skill_used)
        self.assertIn("skill", rec.tool_names)

    def test_tokens_summed_across_step_finishes(self):
        # opencode reports per-step tokens under part.tokens (input/output +
        # cache.read/write); we sum them across every step_finish.
        raw = "\n".join([
            _ev("step_start", {"type": "step-start"}, 1),
            _ev("step_finish", {"type": "step-finish", "reason": "tool-calls",
                                "cost": 0.01,
                                "tokens": {"input": 3, "output": 4,
                                           "cache": {"read": 0, "write": 7977}}}, 2),
            _ev("step_start", {"type": "step-start"}, 3),
            _ev("step_finish", {"type": "step-finish", "reason": "stop",
                                "cost": 0.02,
                                "tokens": {"input": 10, "output": 20,
                                           "cache": {"read": 100, "write": 5}}}, 4),
        ])
        rec = self.a.parse_log(raw)
        self.assertEqual(rec.input_tokens, 13)
        self.assertEqual(rec.output_tokens, 24)
        self.assertEqual(rec.cache_read_tokens, 100)
        self.assertEqual(rec.cache_creation_tokens, 7982)

    def test_tokens_absent_stay_none(self):
        # A stream with no token blocks leaves the token fields None (not 0).
        rec = self.a.parse_log(self._stream())
        self.assertIsNone(rec.input_tokens)
        self.assertIsNone(rec.cache_creation_tokens)

    def test_error_event_captured(self):
        raw = _ev("error", {"message": "provider auth failed"}, 5)
        rec = self.a.parse_log(raw)
        self.assertEqual(rec.error, "provider auth failed")
        self.assertEqual(rec.plugin_errors, ["provider auth failed"])

    def test_empty_and_garbage_log_is_safe(self):
        for raw in ("", "\n\n", "not json\n{bad", None):
            rec = self.a.parse_log(raw)
            self.assertIsInstance(rec, NormalizedRecord)
            self.assertEqual(rec.tool_names, [])
            self.assertIsNone(rec.cost_usd)
            self.assertIsNone(rec.num_turns)
            self.assertEqual(rec.result, "")


class TestSuccessAndPreflight(unittest.TestCase):
    def setUp(self):
        self.a = OpencodeAdapter()

    def test_success_is_exit_zero(self):
        self.assertTrue(self.a.success(0, NormalizedRecord()))
        self.assertFalse(self.a.success(1, NormalizedRecord()))
        self.assertFalse(self.a.success(-1, NormalizedRecord()))

    def test_preflight_missing_when_not_on_path(self):
        orig = oc_mod.shutil.which
        oc_mod.shutil.which = lambda _n: None
        try:
            self.assertEqual(self.a.preflight(), "missing")
        finally:
            oc_mod.shutil.which = orig

    def test_preflight_noauth_without_provider_key(self):
        orig = oc_mod.shutil.which
        oc_mod.shutil.which = lambda _n: "/usr/local/bin/opencode"
        saved = {k: os.environ.pop(k, None) for k in OpencodeAdapter._AUTH_ENV}
        try:
            self.assertEqual(self.a.preflight(), "noauth")
        finally:
            oc_mod.shutil.which = orig
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v

    def test_preflight_ok_with_provider_key(self):
        orig = oc_mod.shutil.which
        oc_mod.shutil.which = lambda _n: "/usr/local/bin/opencode"
        os.environ["ANTHROPIC_API_KEY"] = "sk-probe"
        try:
            self.assertEqual(self.a.preflight(), "ok")
        finally:
            oc_mod.shutil.which = orig
            os.environ.pop("ANTHROPIC_API_KEY", None)


class TestGridExpansion(unittest.TestCase):
    """cli._cells — comma-separated --harness/--model -> (harness, model) cells."""

    def test_single_defaults_to_one_cell(self):
        self.assertEqual(cli._cells("claude", None), [("claude", None)])

    def test_multi_harness_multi_model_is_cartesian(self):
        cells = cli._cells("claude,opencode", "claude-sonnet-4-5,claude-haiku-4-5")
        self.assertEqual(
            cells,
            [
                ("claude", "claude-sonnet-4-5"),
                ("claude", "claude-haiku-4-5"),
                ("opencode", "claude-sonnet-4-5"),
                ("opencode", "claude-haiku-4-5"),
            ],
        )
        # The W2 criterion: >=2 opencode model cells and >=1 claude cell.
        self.assertGreaterEqual(sum(1 for h, _ in cells if h == "opencode"), 2)
        self.assertGreaterEqual(sum(1 for h, _ in cells if h == "claude"), 1)

    def test_cross_harness_same_model_pair(self):
        self.assertEqual(
            cli._cells("claude,opencode", "claude-sonnet-4-5"),
            [("claude", "claude-sonnet-4-5"), ("opencode", "claude-sonnet-4-5")],
        )

    def test_whitespace_and_empty_tolerated(self):
        self.assertEqual(cli._cells(" claude , opencode ", None), [("claude", None), ("opencode", None)])
        self.assertEqual(cli._cells("claude", "  "), [("claude", None)])


if __name__ == "__main__":
    unittest.main()
