"""Tests for the kaneo plugin's three hooks.

All run as subprocesses in their real invocation shape — hook JSON on stdin, at most one
JSON line on stdout — so the entry point is covered and not just the decision function.
The child environment is built from scratch with only PATH inherited, which is what makes
the "unset variable" cases assertable rather than dependent on whatever the developer
happens to export.

Ported from the plugin's original `hooks/scripts/test-policy.sh` when the plugin moved into
this marketplace, then extended when the availability guards landed.

The things worth failing over, because every one of them is silent when it breaks:

  - **Floor deny.** The allowlist is the authority, not the calling agent's `tools:` grant.
    A regression hands a subagent claim authority and the board quietly grows edits nobody
    can attribute.
  - **Config preflight.** The MCP server connects on two variables; the skill's contract
    needs five. Between those two facts sits a session with working board tools, no project
    id, and no identity — which does not error, it picks a board.
  - **Stamp idempotence.** Retries are normal. A stamp that appends twice is not a crash;
    it is a comment body that accretes brackets until attribution is unusable.
  - **Preflight silence when healthy.** A warning that fires on every good session is a
    warning nobody reads by the third one.
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(REPO, "primitives-core", "hooks")
POLICY = os.path.join(HOOKS, "kaneo-mcp-policy", "hook.py")
TRIPWIRE = os.path.join(HOOKS, "kaneo-bash-tripwire", "hook.py")
PREFLIGHT = os.path.join(HOOKS, "kaneo-preflight", "hook.py")

MANAGER = os.path.join(REPO, "primitives-core", "agents", "kaneo-manager.md")

# A fully wired repo. The policy tests are about level and stamping, so they all run
# configured; the config preflight has its own class where the absence is the subject.
CONFIGURED = {
    "KANEO_API_URL": "https://kaneo.example.com/api",
    "KANEO_MCP_TOKEN": "token",
    "KANEO_API_KEY": "key",
    "KANEO_PROJECT_ID": "proj",
    "KANEO_AGENT_NAME": "agent-a",
}


def load(path, name):
    """Import a hook module by path — the three hook.py files share a basename."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(hook, payload, env=None):
    """Drive one hook with a payload; return its stdout, stripped."""
    child = {"PATH": os.environ.get("PATH", "")}
    child.update(env or {})
    proc = subprocess.run(
        [sys.executable, hook],
        input=payload if isinstance(payload, str) else json.dumps(payload),
        capture_output=True,
        text=True,
        env=child,
        timeout=30,
    )
    assert proc.returncode == 0, f"hook exited {proc.returncode}: {proc.stderr}"
    return proc.stdout.strip()


def decision(out):
    """The permissionDecision in a hook's output, or None when it stayed silent."""
    if not out:
        return None
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"]


def context(out):
    """The additionalContext in a SessionStart hook's output, or None when silent."""
    if not out:
        return None
    return json.loads(out)["hookSpecificOutput"]["additionalContext"]


class McpPolicyTests(unittest.TestCase):
    def test_main_session_claim_tool_passes_untouched(self):
        out = run(
            POLICY,
            {
                "tool_name": "mcp__kaneo__update_task_status",
                "tool_input": {},
                "session_id": "s1",
            },
            CONFIGURED,
        )
        self.assertEqual(out, "")

    def test_subagent_l2_tool_allowed_silently(self):
        out = run(
            POLICY,
            {
                "tool_name": "mcp__plugin_kaneo_kaneo__list_tasks",
                "tool_input": {},
                "agent_type": "kaneo-manager",
                "agent_id": "a1",
                "session_id": "s1",
            },
            CONFIGURED,
        )
        self.assertEqual(out, "")

    def test_subagent_claim_tool_denied(self):
        out = run(
            POLICY,
            {
                "tool_name": "mcp__plugin_kaneo_kaneo__update_task_status",
                "tool_input": {},
                "agent_type": "kaneo-manager",
                "agent_id": "a1",
                "session_id": "s1",
            },
            CONFIGURED,
        )
        self.assertEqual(decision(out), "deny")
        self.assertIn("level policy", out)

    def test_both_tool_prefixes_are_recognised(self):
        # A wrong prefix fails OPEN and silently, so the deny must land on both live
        # shapes: plugin-registered and directly registered.
        for name in ("mcp__kaneo__move_task", "mcp__plugin_kaneo_kaneo__move_task"):
            with self.subTest(tool=name):
                out = run(
                    POLICY,
                    {
                        "tool_name": name,
                        "tool_input": {},
                        "agent_type": "builder",
                        "agent_id": "a1",
                    },
                    CONFIGURED,
                )
                self.assertEqual(decision(out), "deny")

    def test_unknown_tool_defaults_to_denied_for_subagents(self):
        # Tools added by a future image bump must not arrive pre-authorised.
        out = run(
            POLICY,
            {
                "tool_name": "mcp__kaneo__some_tool_that_ships_later",
                "tool_input": {},
                "agent_type": "builder",
                "agent_id": "a1",
            },
            CONFIGURED,
        )
        self.assertEqual(decision(out), "deny")

    def test_subagent_comment_is_stamped_via_updated_input(self):
        out = run(
            POLICY,
            {
                "tool_name": "mcp__plugin_kaneo_kaneo__create_task_comment",
                "tool_input": {"taskId": "t1", "content": "did the thing"},
                "agent_type": "kaneo-manager",
                "agent_id": "a1",
                "session_id": "s9",
            },
            CONFIGURED,
        )
        self.assertEqual(decision(out), "allow")
        updated = json.loads(out)["hookSpecificOutput"]["updatedInput"]
        self.assertEqual(
            updated["content"], "did the thing — [kaneo-manager, session s9]"
        )
        self.assertEqual(updated["taskId"], "t1", "other fields must survive the rewrite")

    def test_already_stamped_comment_is_a_no_op(self):
        out = run(
            POLICY,
            {
                "tool_name": "mcp__plugin_kaneo_kaneo__create_task_comment",
                "tool_input": {
                    "taskId": "t1",
                    "content": "did the thing — [kaneo-manager, session s9]",
                },
                "agent_type": "kaneo-manager",
                "agent_id": "a1",
                "session_id": "s9",
            },
            CONFIGURED,
        )
        self.assertEqual(out, "", "a retry must not append a second stamp")

    def test_main_session_create_task_is_stamped_as_root(self):
        out = run(
            POLICY,
            {
                "tool_name": "mcp__plugin_kaneo_kaneo__create_task",
                "tool_input": {"title": "T", "description": "body"},
                "session_id": "s2",
            },
            CONFIGURED,
        )
        updated = json.loads(out)["hookSpecificOutput"]["updatedInput"]
        self.assertEqual(updated["description"], "body — [root, session s2]")

    def test_non_string_stamp_field_is_left_alone(self):
        out = run(
            POLICY,
            {
                "tool_name": "mcp__kaneo__create_task",
                "tool_input": {"title": "T", "description": None},
                "session_id": "s3",
            },
            CONFIGURED,
        )
        self.assertEqual(out, "")

    def test_malformed_stdin_fails_open(self):
        self.assertEqual(run(POLICY, "not json at all", CONFIGURED), "")


class ConfigPreflightTests(unittest.TestCase):
    """The silent hole: the server connects on two variables, the contract needs five.

    `KANEO_API_URL` and `KANEO_MCP_TOKEN` are the only ones `.mcp.json` expands, so a repo
    that sets just those gets a fully working set of board tools with no project id and no
    agent identity. Nothing errors. The agent calls `list_projects` and picks one.
    """

    def _env(self, **overrides):
        env = dict(CONFIGURED)
        env.update(overrides)
        return {k: v for k, v in env.items() if v is not None}

    def test_each_scoped_variable_is_named_when_it_is_the_missing_one(self):
        for var in ("KANEO_API_KEY", "KANEO_PROJECT_ID", "KANEO_AGENT_NAME"):
            with self.subTest(missing=var):
                out = run(
                    POLICY,
                    {
                        "tool_name": "mcp__kaneo__list_tasks",
                        "tool_input": {},
                        "session_id": "s1",
                    },
                    self._env(**{var: None}),
                )
                self.assertEqual(decision(out), "deny")
                self.assertIn(var, out, "the reason must name the variable to set")

    def test_an_empty_value_counts_as_unset(self):
        out = run(
            POLICY,
            {"tool_name": "mcp__kaneo__list_tasks", "tool_input": {}},
            self._env(KANEO_PROJECT_ID=""),
        )
        self.assertEqual(decision(out), "deny")

    def test_diagnostic_tools_stay_open_so_the_agent_can_find_out_why(self):
        # Denying whoami would turn a loud failure back into a confusing one: whoami is
        # exactly what the skill prescribes for working out which key is wired.
        for tool in ("whoami", "list_workspaces", "list_projects"):
            with self.subTest(tool=tool):
                out = run(
                    POLICY,
                    {"tool_name": f"mcp__kaneo__{tool}", "tool_input": {}},
                    {"KANEO_API_URL": "https://kaneo.example.com/api"},
                )
                self.assertEqual(out, "")

    def test_a_mutation_is_denied_before_it_can_be_stamped(self):
        # The stamping branch must not run first and auto-approve an unconfigured write.
        out = run(
            POLICY,
            {
                "tool_name": "mcp__kaneo__create_task_comment",
                "tool_input": {"taskId": "t1", "content": "hello"},
                "session_id": "s1",
            },
            self._env(KANEO_AGENT_NAME=None),
        )
        self.assertEqual(decision(out), "deny")
        self.assertNotIn("updatedInput", out)

    def test_the_level_deny_wins_over_the_config_deny(self):
        # Being a subagent is permanent; a missing variable is fixed and retried. Telling a
        # subagent to go set KANEO_PROJECT_ID for a call it may never make wastes a round
        # trip, so the authority reason must be the one it gets.
        out = run(
            POLICY,
            {
                "tool_name": "mcp__kaneo__update_task_status",
                "tool_input": {},
                "agent_type": "builder",
                "agent_id": "a1",
            },
            {"KANEO_API_URL": "https://kaneo.example.com/api"},
        )
        self.assertIn("level policy", out)
        self.assertNotIn("not configured", out)


class BashTripwireTests(unittest.TestCase):
    ENV = {"KANEO_API_URL": "https://kaneo.example.com/api"}

    def test_subagent_bash_naming_the_host_is_denied(self):
        out = run(
            TRIPWIRE,
            {
                "tool_name": "Bash",
                "tool_input": {"command": "curl https://kaneo.example.com/api/task/1"},
                "agent_type": "builder",
                "agent_id": "a1",
            },
            self.ENV,
        )
        self.assertEqual(decision(out), "deny")
        self.assertIn("advisory tripwire", out)

    def test_subagent_bash_naming_the_env_var_is_denied(self):
        out = run(
            TRIPWIRE,
            {
                "tool_name": "Bash",
                "tool_input": {"command": 'curl "$KANEO_API_URL/task/1"'},
                "agent_type": "builder",
                "agent_id": "a1",
            },
            self.ENV,
        )
        self.assertEqual(decision(out), "deny")

    def test_unrelated_subagent_command_passes(self):
        out = run(
            TRIPWIRE,
            {
                "tool_name": "Bash",
                "tool_input": {"command": "ls -la"},
                "agent_type": "builder",
                "agent_id": "a1",
            },
            self.ENV,
        )
        self.assertEqual(out, "")

    def test_main_session_is_never_tripped(self):
        out = run(
            TRIPWIRE,
            {
                "tool_name": "Bash",
                "tool_input": {"command": "curl https://kaneo.example.com/api/task/1"},
            },
            self.ENV,
        )
        self.assertEqual(out, "", "claim authority lives in the root session")

    def test_no_op_when_the_instance_url_is_unset(self):
        out = run(
            TRIPWIRE,
            {
                "tool_name": "Bash",
                "tool_input": {"command": "echo $KANEO_API_URL"},
                "agent_type": "builder",
                "agent_id": "a1",
            },
        )
        self.assertEqual(out, "", "every repo without a board pays nothing but the process")

    def test_malformed_stdin_fails_open(self):
        self.assertEqual(run(TRIPWIRE, "{{{", self.ENV), "")


class PreflightSubprocessTests(unittest.TestCase):
    """The SessionStart warning, driven end to end.

    `HOME` is redirected at a tempdir so the `/mcp disable` probe reads a fixture rather
    than the developer's real `~/.claude.json` — the check exists precisely because that
    file holds state nothing else surfaces, so a test that read the real one would pass or
    fail depending on whose machine ran it.
    """

    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.cwd = "/some/project"

    def _run(self, env=None, source="startup", claude_json=None):
        if claude_json is not None:
            with open(os.path.join(self.home, ".claude.json"), "w", encoding="utf-8") as fh:
                json.dump(claude_json, fh)
        child = {"HOME": self.home}
        child.update(env or {})
        return run(PREFLIGHT, {"source": source, "cwd": self.cwd}, child)

    def test_silent_when_the_board_is_reachable(self):
        self.assertEqual(self._run(CONFIGURED), "")

    def test_unconfigured_repo_is_told_loudly(self):
        body = context(self._run({}))
        self.assertIn("NOT available", body)
        self.assertIn("KANEO_API_URL", body)
        self.assertIn("KANEO_MCP_TOKEN", body)

    def test_the_warning_forbids_the_improvised_fallback(self):
        # The whole reason this hook exists: an agent with no board tools does not stop,
        # it writes a TODO.md — the one thing the skill forbids.
        body = context(self._run({}))
        self.assertIn("TODO.md", body)

    def test_mcp_disable_for_this_project_is_surfaced(self):
        body = context(
            self._run(
                CONFIGURED,
                claude_json={
                    "projects": {self.cwd: {"disabledMcpServers": ["plugin:kaneo:kaneo"]}}
                },
            )
        )
        self.assertIn("/mcp enable", body)

    def test_another_projects_disable_does_not_leak(self):
        out = self._run(
            CONFIGURED,
            claude_json={
                "projects": {"/somewhere/else": {"disabledMcpServers": ["plugin:kaneo:kaneo"]}}
            },
        )
        self.assertEqual(out, "", "the toggle is per-project and must be read that way")

    def test_a_headerless_direct_registration_is_surfaced_as_wrong_identity(self):
        # The 2026-08-11 failure: tools present and working, authenticated as the owner.
        # It must NOT be reported as "board unavailable" — that sends the reader hunting
        # for missing tools that are right there, which is what cost 40 messages.
        body = context(
            self._run(
                CONFIGURED,
                claude_json={"projects": {self.cwd: {"mcpServers": {"kaneo": {"url": "u"}}}}},
            )
        )
        self.assertIn("WRONG USER", body)
        self.assertIn("claude mcp remove kaneo", body)
        self.assertIn("whoami", body)
        self.assertNotIn("NOT available", body)

    def test_a_direct_registration_carrying_its_own_auth_header_is_left_alone(self):
        # Registering the server yourself is supported by the skill; only the headerless
        # kind triggers the OAuth fallback. Warning about a working setup trains the
        # reader to ignore this hook.
        out = self._run(
            CONFIGURED,
            claude_json={
                "projects": {
                    self.cwd: {
                        "mcpServers": {
                            "kaneo": {"url": "u", "headers": {"Authorization": "Bearer t"}}
                        }
                    }
                }
            },
        )
        self.assertEqual(out, "")

    def test_the_auth_header_check_is_case_insensitive(self):
        out = self._run(
            CONFIGURED,
            claude_json={
                "projects": {
                    self.cwd: {
                        "mcpServers": {"kaneo": {"headers": {"authorization": "Bearer t"}}}
                    }
                }
            },
        )
        self.assertEqual(out, "", "HTTP header names are not case-sensitive")

    def test_a_global_headerless_registration_is_surfaced_too(self):
        body = context(self._run(CONFIGURED, claude_json={"mcpServers": {"kaneo": {}}}))
        self.assertIn("WRONG USER", body)

    def test_another_projects_direct_registration_does_not_leak(self):
        out = self._run(
            CONFIGURED,
            claude_json={"projects": {"/somewhere/else": {"mcpServers": {"kaneo": {}}}}},
        )
        self.assertEqual(out, "")

    def test_both_failure_kinds_report_together_without_burying_each_other(self):
        # An unconfigured repo that ALSO has a shadowing registration must say both:
        # fixing the loud one and then hitting the quiet one is the worst version of this.
        body = context(self._run({}, claude_json={"mcpServers": {"kaneo": {}}}))
        self.assertIn("NOT available", body)
        self.assertIn("WRONG USER", body)

    def test_resume_and_compact_stay_quiet(self):
        for source in ("resume", "compact"):
            with self.subTest(source=source):
                self.assertEqual(self._run({}, source=source), "")

    def test_opt_out_stands_it_down(self):
        self.assertEqual(self._run({"KANEO_PREFLIGHT_DISABLED": "1"}), "")

    def test_malformed_stdin_fails_open(self):
        self.assertEqual(run(PREFLIGHT, "nonsense", {"HOME": self.home}), "")


class PreflightUnitTests(unittest.TestCase):
    """The pieces that are awkward to reach through the subprocess: env-skip parsing."""

    def setUp(self):
        self.mod = load(PREFLIGHT, "kaneo_preflight")
        self.home = tempfile.mkdtemp()

    def _problems(self, env):
        return self.mod.problems(env, self.home, "/some/project")

    def test_skip_env_suppresses_plugin_servers(self):
        env = dict(CONFIGURED, CLAUDE_CODE_SKIP_PLUGIN_MCP_SERVERS="1")
        self.assertTrue(any("discovery is off" in p for p in self._problems(env)))

    def test_kaneo_exempted_from_the_skip_is_not_reported(self):
        env = dict(
            CONFIGURED,
            CLAUDE_CODE_SKIP_PLUGIN_MCP_SERVERS="1",
            CLAUDE_CODE_SKIP_PLUGIN_MCP_SERVERS_EXCEPT="kaneo",
        )
        self.assertEqual(self._problems(env), [])

    def test_an_unrelated_exemption_still_leaves_kaneo_skipped(self):
        env = dict(
            CONFIGURED,
            CLAUDE_CODE_SKIP_PLUGIN_MCP_SERVERS="1",
            CLAUDE_CODE_SKIP_PLUGIN_MCP_SERVERS_EXCEPT="something-else",
        )
        self.assertTrue(any("discovery is off" in p for p in self._problems(env)))

    def test_causes_accumulate_rather_than_shadowing_each_other(self):
        # Fixing one cause and finding another waiting is the worst version of this, so
        # every cause is reported in one pass.
        env = {"CLAUDE_CODE_SKIP_PLUGIN_MCP_SERVERS": "1"}
        self.assertEqual(len(self._problems(env)), 2)


class ManagerAgentTests(unittest.TestCase):
    """The reference agent's `tools:` list IS the L2 allowlist, so the two must agree.

    They are authored in different files and nothing else compares them: a tool added to
    the hook's allowlist but not the agent leaves the reference manager unable to do its
    job, and one added to the agent but not the hook is denied at runtime with a confusing
    reason. Both are silent until someone hits them mid-task.
    """

    def test_agent_tools_match_the_hook_allowlist(self):
        policy = load(POLICY, "kaneo_mcp_policy")
        with open(MANAGER, encoding="utf-8") as fh:
            text = fh.read()
        granted = {
            t.rsplit("__", 1)[1]
            for t in text.split("tools:", 1)[1].split("\n", 1)[0].split(",")
            for t in [t.strip()]
            if t.startswith("mcp__")
        }
        self.assertEqual(granted, policy.L2_ALLOW)

    def test_the_diagnostic_set_is_a_subset_of_the_l2_allowlist(self):
        # The preflight lets the diagnostic tools through; the floor deny must not then
        # take them away from a subagent trying to work out why the board is unreachable.
        policy = load(POLICY, "kaneo_mcp_policy")
        self.assertTrue(policy.DIAGNOSTIC <= policy.L2_ALLOW)


if __name__ == "__main__":
    unittest.main()
