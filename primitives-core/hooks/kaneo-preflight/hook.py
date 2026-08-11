#!/usr/bin/env python3
"""Says loudly, at session start, that the Kaneo board tools are NOT going to be there.

The companion `kaneo-mcp-policy` hook can only fire on a kaneo tool call, so it cannot
catch the case where the tools never loaded — there is no call to intercept. That case is
the dangerous one: the kaneo skill still loads, still tells the agent the board holds the
tracked work, and still forbids `TODO.md`. An agent that finds no board tools does not stop;
it improvises. This hook is the one thing standing between that state and a silent wrong
turn, so it states the problem in the session's own context before any work starts.

Three causes, each silent on its own and each checkable here:

  1. **Unconfigured.** `KANEO_API_URL` or `KANEO_MCP_TOKEN` unset, so `${...}` expansion in
     the plugin's `.mcp.json` cannot resolve and the server never connects.
  2. **Disabled for this project.** `/mcp disable` writes `plugin:kaneo:kaneo` into
     `disabledMcpServers` under this directory's entry in `~/.claude.json`. It is
     per-project, reversible only by `/mcp enable`, and visible nowhere else. Observed in
     the wild on another plugin's server, which is why it is checked rather than assumed
     rare.
  3. **Discovery switched off.** `CLAUDE_CODE_SKIP_PLUGIN_MCP_SERVERS` suppresses plugin
     MCP servers wholesale, with an `..._EXCEPT` allowlist that can exempt this one.

Silent when the board is reachable, which is the common case — this fires only when
something is actually wrong. `KANEO_PREFLIGHT_DISABLED` (any non-empty value) stands it
down entirely.

Stdlib-only. Reads the hook JSON on stdin, prints at most one JSON object, always exits 0:
a session must start even when this hook is broken.
"""

import json
import os
import sys

DISABLE_ENV = "KANEO_PREFLIGHT_DISABLED"
SKIP_ENV = "CLAUDE_CODE_SKIP_PLUGIN_MCP_SERVERS"
SKIP_EXCEPT_ENV = "CLAUDE_CODE_SKIP_PLUGIN_MCP_SERVERS_EXCEPT"

# Only on a genuinely new session. On resume/compact the context is already carried and a
# second copy of this is noise — same rule the other session hook in this marketplace uses.
SURFACE_SOURCES = ("startup", "clear")

# The server itself expands only these two; the other three are the skill's contract and
# are enforced at call time by kaneo-mcp-policy instead.
SERVER_VARS = ("KANEO_API_URL", "KANEO_MCP_TOKEN")
# How Claude Code names a plugin-provided server: plugin:<plugin>:<server>.
SERVER_KEY = "plugin:kaneo:kaneo"
BARE_SERVER_KEY = "kaneo"

HEADER = (
    "The Kaneo board is NOT available in this session. Its MCP tools will be missing, "
    "not merely slow or empty."
)
FOOTER = (
    "Until it is fixed: do not work the board, do not guess a project, and do NOT fall "
    "back to a TODO.md or backlog.md — the kaneo skill forbids those precisely because "
    "the board is meant to be the only copy. Say this to the owner and stop, or continue "
    "with work that does not touch tracked tasks."
)


def _disabled_for_project(home, cwd):
    """True when /mcp disable has switched this plugin's server off for this directory.

    Reads ~/.claude.json rather than any settings file on purpose: that is where the
    toggle actually persists, and the whole point of this check is that the state is
    invisible everywhere else.
    """
    try:
        with open(os.path.join(home, ".claude.json"), encoding="utf-8") as fh:
            entry = json.load(fh).get("projects", {}).get(cwd, {})
        disabled = entry.get("disabledMcpServers") or []
        return SERVER_KEY in disabled or BARE_SERVER_KEY in disabled
    except Exception:
        # An unreadable or absent file is not evidence of anything; stay quiet.
        return False


def _skipped_by_env(env):
    """True when plugin MCP discovery is off and kaneo is not on the exemption list."""
    if not env.get(SKIP_ENV):
        return False
    exempt = env.get(SKIP_EXCEPT_ENV) or ""
    names = [part.strip().lower() for part in exempt.split(",") if part.strip()]
    return not any(name == BARE_SERVER_KEY or name.startswith("kaneo@") for name in names)


def problems(env, home, cwd):
    """Every reason the board tools will be absent, worst first. Empty means healthy."""
    found = []
    missing = [name for name in SERVER_VARS if not env.get(name)]
    if missing:
        found.append(
            f"Not configured: {', '.join(missing)} unset, so the server definition cannot "
            "expand and no connection is attempted. Set the five KANEO_* values in this "
            "repo's .claude/settings.local.json — the kaneo skill's "
            "references/configuration.md says where each comes from — then restart the "
            "session, because headers expand at session start."
        )
    if _disabled_for_project(home, cwd):
        found.append(
            "Disabled for this project: someone ran /mcp disable, which wrote "
            f"'{SERVER_KEY}' into disabledMcpServers under this directory's entry in "
            "~/.claude.json. It is per-project and shows up nowhere else. Re-enable with "
            "/mcp enable."
        )
    if _skipped_by_env(env):
        found.append(
            f"Plugin MCP discovery is off: {SKIP_ENV} is set and kaneo is not named in "
            f"{SKIP_EXCEPT_ENV}, so no plugin ships an MCP server in this session."
        )
    return found


def build_message(found):
    lines = [HEADER, ""]
    lines += [f"- {item}" for item in found]
    lines += ["", FOOTER]
    return "\n".join(lines)


def _emit(obj):
    """Print the hook's one JSON object without letting a closed stdout become a nonzero
    exit: flush inside the guard, and on a broken pipe point fd 1 at devnull so the
    interpreter's shutdown flush has nothing left to do."""
    try:
        print(json.dumps(obj))
        sys.stdout.flush()
    except BrokenPipeError:
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), 1)
        except Exception:
            pass


def main():
    try:
        if os.environ.get(DISABLE_ENV):
            return 0
        payload = json.loads(sys.stdin.read())
        if not isinstance(payload, dict):
            return 0
        if payload.get("source") not in SURFACE_SOURCES:
            return 0
        found = problems(
            os.environ, os.path.expanduser("~"), payload.get("cwd") or os.getcwd()
        )
        if not found:
            return 0
        _emit({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": build_message(found),
            },
        })
    except Exception:
        # Fail open and silent. A warning that never arrives degrades to today's
        # behaviour; a hook that crashes keeps the session from starting at all.
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
