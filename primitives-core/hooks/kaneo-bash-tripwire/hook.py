#!/usr/bin/env python3
"""Advisory tripwire: denies subagent Bash that reaches the Kaneo board host directly.

**This is a tripwire, not containment, and the distinction is the whole point.** Both
credentials live in the shared process environment, so any subagent holding Bash can reach
the board through `curl`, a python/node one-liner, or a script it writes first. No string
guard can close that. This hook catches the naive path and leaves an audit trail; the only
sound configuration for an untrusted level is no Bash at all, which code-writing workers
cannot have. The full ceiling is in the kaneo skill's `references/access-model.md`.

Fires on `PreToolUse` for `Bash`. Denies when all three hold: the caller is a subagent, the
instance URL is configured, and the command mentions the board host or either of the
`KANEO_API_URL` / `KANEO_CLIENT_URL` variable names. No-op when the env is unset, which is
every repo that does not use the board — the cost there is one hook process per Bash call.

Stdlib-only. Reads the hook JSON on stdin; prints one JSON object on a deny and nothing
otherwise. Always exits 0.
"""

import json
import os
import sys
from urllib.parse import urlparse

VAR_NAMES = ("KANEO_API_URL", "KANEO_CLIENT_URL")


def decide(data, env):
    """Return the deny payload for one PreToolUse event, or None to stay silent."""
    if not (data.get("agent_id") or data.get("agent_type")):
        return None
    url = env.get("KANEO_API_URL")
    if not url:
        return None
    host = urlparse(url).hostname or ""
    command = (data.get("tool_input") or {}).get("command", "")
    needles = [n for n in (host, *VAR_NAMES) if n]
    if not any(n in command for n in needles):
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "advisory tripwire — board access from subagents goes through the "
                "kaneo MCP tools"
            ),
        }
    }


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    out = decide(data, os.environ)
    if out is not None:
        print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
