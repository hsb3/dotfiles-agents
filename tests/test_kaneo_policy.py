"""Tests for the kaneo plugin's two PreToolUse hooks.

Both run as subprocesses in their real invocation shape — hook JSON on stdin, at most one
JSON line on stdout — so the entry point is covered and not just the decision function.
The child environment is built from scratch with only PATH inherited, which is what makes
the tripwire's "no-op when KANEO_API_URL is unset" case assertable rather than dependent on
whatever the developer happens to export.

Ported from the plugin's original `hooks/scripts/test-policy.sh` when the plugin moved into
this marketplace; the assertions are the same set, plus coverage of the fail-open path the
bash version could not reach.

The two things worth failing over, because both are silent when they break:

  - **Floor deny.** The allowlist is the authority, not the calling agent's `tools:` grant.
    A regression here does not error — it hands a subagent claim authority and the board
    quietly grows edits nobody can attribute.
  - **Stamp idempotence.** Retries are normal. A stamp that appends twice is not a crash;
    it is a comment body that slowly accretes brackets, which nobody reads closely enough
    to notice until attribution is unusable.
"""

import json
import os
import subprocess
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(REPO, "primitives-core", "hooks")
POLICY = os.path.join(HOOKS, "kaneo-mcp-policy", "hook.py")
TRIPWIRE = os.path.join(HOOKS, "kaneo-bash-tripwire", "hook.py")

MANAGER = os.path.join(REPO, "primitives-core", "agents", "kaneo-manager.md")


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


class McpPolicyTests(unittest.TestCase):
    def test_main_session_claim_tool_passes_untouched(self):
        out = run(
            POLICY,
            {
                "tool_name": "mcp__kaneo__update_task_status",
                "tool_input": {},
                "session_id": "s1",
            },
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
        )
        self.assertEqual(out, "")

    def test_malformed_stdin_fails_open(self):
        self.assertEqual(run(POLICY, "not json at all"), "")


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


class ManagerAgentTests(unittest.TestCase):
    """The reference agent's `tools:` list IS the L2 allowlist, so the two must agree.

    They are authored in different files and nothing else compares them: a tool added to
    the hook's allowlist but not the agent leaves the reference manager unable to do its
    job, and one added to the agent but not the hook is denied at runtime with a confusing
    reason. Both are silent until someone hits them mid-task.
    """

    def test_agent_tools_match_the_hook_allowlist(self):
        sys.path.insert(0, os.path.join(HOOKS, "kaneo-mcp-policy"))
        import hook as policy  # noqa: E402

        with open(MANAGER, encoding="utf-8") as fh:
            text = fh.read()
        granted = {
            t.rsplit("__", 1)[1]
            for t in text.split("tools:", 1)[1].split("\n", 1)[0].split(",")
            for t in [t.strip()]
            if t.startswith("mcp__")
        }
        self.assertEqual(granted, policy.L2_ALLOW)


if __name__ == "__main__":
    unittest.main()
