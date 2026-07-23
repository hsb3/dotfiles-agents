#!/usr/bin/env python3
"""
example-hook — a minimal, ratified PreToolUse hook template.

This is the shape every hook in this collection takes: a directory holding this
script plus a `config.json` that binds it to an event. Copy this directory into
your project's hook location (e.g. `.claude/hooks/command-log/`), adapt the
behavior, and wire it into settings with a `command` that INVOKES THIS FILE BY
PATH — never inline shell. See the wiring example in
`references/examples/hook.settings.json`.

What it demonstrates (not what it is for — replace the behavior):
  - read the event payload as JSON on stdin
  - do one small, deterministic thing (here: append the Bash command to a log)
  - FAIL OPEN: catch everything and exit 0 so a bug never breaks the session

Contract (PreToolUse):
  - stdin JSON includes at least: session_id, cwd, tool_name, tool_input
  - exit 0  -> allow the tool call to proceed (this template never blocks)
  - exit 2  -> would block the call and feed stderr back to the agent
  - stdout  -> optional; a JSON object can return structured control fields

Python 3 standard library only — zero install, runs anywhere.
"""

import json
import os
import sys


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, ValueError):
        # Malformed payload: fail open, do nothing, do not block.
        sys.exit(0)

    try:
        tool = payload.get("tool_name", "")
        command = payload.get("tool_input", {}).get("command", "")
        cwd = payload.get("cwd") or os.getcwd()

        # Only act on the event we care about; ignore everything else.
        if tool == "Bash" and command:
            log_path = os.path.join(cwd, "logs", "command-log.jsonl")
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"command": command}) + "\n")
    except Exception:
        # Best-effort side effect: never let it break the tool call.
        pass

    # Allow the tool call to proceed.
    sys.exit(0)


if __name__ == "__main__":
    main()
