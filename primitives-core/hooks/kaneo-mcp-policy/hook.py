#!/usr/bin/env python3
"""Level policy for the kaneo MCP tools: config preflight, subagent floor-deny, stamping.

Three jobs, all on `PreToolUse` for `mcp__(plugin_kaneo_)?kaneo__*`:

  1. **Config preflight.** Deny any board-scoped tool while `KANEO_API_KEY`,
     `KANEO_PROJECT_ID`, or `KANEO_AGENT_NAME` is unset, naming the variable.

     This closes a genuinely silent hole. The MCP server needs only two of the five
     variables to connect — `KANEO_API_URL` and `KANEO_MCP_TOKEN`, the two that expand in
     `.mcp.json` — but the skill's contract needs all five. So the tools can be fully
     present and working while the session has no idea *which* board it is on and no
     identity to attribute claims to. An agent in that state does not error; it calls
     `list_projects` and picks one. Wrong board, wrong attribution, no warning anywhere.

     The three diagnostic tools stay open, because they are what the skill tells an agent
     to use to work out what is wrong, and denying the diagnostic is how a loud failure
     turns back into a confusing one.

  2. **Floor deny.** A subagent calling anything outside the L2 read/append set is denied.
     The allowlist is the authority rather than the calling agent's own `tools:` grant, so
     a misconfigured agent fails closed instead of inheriting claim authority. Tools added
     by a future image bump default to denied for the same reason.

  3. **Stamping.** `create_task_comment` and `create_task` get `— [<agent or root>, session
     <id>]` appended to the content/description, idempotently so a retry does not
     double-stamp. Because `updatedInput` requires an explicit allow, these two
     append-only tools are auto-approved; that trade is accepted in the design.

Ordering is deliberate: the floor deny runs before the config preflight, because "you are a
subagent and this is root-only" is permanent and true whatever the config says, while a
missing variable is fixed and retried. Telling a subagent to go set `KANEO_PROJECT_ID` for a
call it will never be allowed to make is a wasted round trip.

The enforcement ceiling is real and is documented in the skill's
`references/access-model.md`: this is sound for MCP calls only. Both credentials live in
the shared process environment, so any subagent holding Bash can reach the board over REST
regardless. The companion `kaneo-bash-tripwire` hook catches the naive path and nothing more.

Matchers are regex — `mcp__kaneo__.*`, never `mcp__kaneo__*`, which is a glob-looking regex
that matches by accident. Both live prefixes are handled: a plugin-registered server
surfaces `mcp__plugin_kaneo_kaneo__<tool>`, a directly registered one `mcp__kaneo__<tool>`.
A wrong prefix fails open, and silently.

Stdlib-only. Reads the hook JSON on stdin; prints one JSON object when it has a decision
to make and nothing at all otherwise. Always exits 0 — a policy hook that crashes a session
is worse than one that lets a call through.
"""

import json
import os
import re
import sys

L2_ALLOW = {
    "whoami",
    "list_workspaces",
    "list_projects",
    "get_project",
    "list_tasks",
    "get_task",
    "list_task_comments",
    "create_task_comment",
    "create_task",
    "list_workspace_labels",
    "get_task_relations",
}
STAMP_FIELD = {"create_task_comment": "content", "create_task": "description"}
STAMP_RE = re.compile(r" — \[[^\]]*, session [^\]]*\]$")
TOOL_PREFIX = re.compile(r"^mcp__(plugin_kaneo_)?kaneo__")

# Tools that answer "what is wrong with this setup" rather than acting on a board. They
# need nothing beyond what the server already needed to exist, so the preflight lets them
# through — `whoami` in particular is the check the skill prescribes.
DIAGNOSTIC = {"whoami", "list_workspaces", "list_projects"}
# The variables the MCP server does NOT need to connect, but the skill's contract does.
SCOPED_CONFIG = ("KANEO_API_KEY", "KANEO_PROJECT_ID", "KANEO_AGENT_NAME")


def _deny(reason):
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def decide(data, env):
    """Return the hook payload for one PreToolUse event, or None to stay silent."""
    base = TOOL_PREFIX.sub("", data.get("tool_name", ""))
    subagent = bool(data.get("agent_id") or data.get("agent_type"))

    if subagent and base not in L2_ALLOW:
        return _deny(
            f"kaneo level policy: {base} is claim-authority, root session only; "
            "subagents get the L2 read/append set (see the kaneo skill's "
            "references/access-model.md)."
        )

    if base not in DIAGNOSTIC:
        missing = [name for name in SCOPED_CONFIG if not env.get(name)]
        if missing:
            return _deny(
                f"kaneo is not configured: {', '.join(missing)} unset. The board tools "
                "loaded anyway because the MCP server only needs KANEO_API_URL and "
                f"KANEO_MCP_TOKEN, so {base} would have run against an unknown board with "
                "no identity to attribute it to. Set the missing variables in this repo's "
                ".claude/settings.local.json and restart the session; the kaneo skill's "
                "references/configuration.md says where each value comes from. Do not "
                "guess a project, and do not fall back to a TODO file."
            )

    field = STAMP_FIELD.get(base)
    tool_input = data.get("tool_input") or {}
    value = tool_input.get(field) if field else None
    if isinstance(value, str) and not STAMP_RE.search(value):
        who = data.get("agent_type") or "root"
        sid = data.get("session_id", "unknown")
        updated = dict(tool_input)
        updated[field] = f"{value} — [{who}, session {sid}]"
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "kaneo: attribution stamp appended",
                "updatedInput": updated,
            }
        }
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    out = decide(data, os.environ)
    if out is not None:
        print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
