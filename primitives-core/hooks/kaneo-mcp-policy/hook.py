#!/usr/bin/env python3
"""Level policy for the kaneo MCP tools: subagent floor-deny plus attribution stamping.

Two jobs, both on `PreToolUse` for `mcp__(plugin_kaneo_)?kaneo__*`:

  1. **Floor deny.** A subagent calling anything outside the L2 read/append set is denied.
     The allowlist is the authority rather than the calling agent's own `tools:` grant, so
     a misconfigured agent fails closed instead of inheriting claim authority. Tools added
     by a future image bump default to denied for the same reason.

  2. **Stamping.** `create_task_comment` and `create_task` get `— [<agent or root>, session
     <id>]` appended to the content/description, idempotently so a retry does not
     double-stamp. Because `updatedInput` requires an explicit allow, these two
     append-only tools are auto-approved; that trade is accepted in the design.

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


def decide(data):
    """Return the hook payload for one PreToolUse event, or None to stay silent."""
    base = TOOL_PREFIX.sub("", data.get("tool_name", ""))
    subagent = bool(data.get("agent_id") or data.get("agent_type"))

    if subagent and base not in L2_ALLOW:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"kaneo level policy: {base} is claim-authority, root session only; "
                    "subagents get the L2 read/append set (see the kaneo skill's "
                    "references/access-model.md)."
                ),
            }
        }

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
    out = decide(data)
    if out is not None:
        print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
