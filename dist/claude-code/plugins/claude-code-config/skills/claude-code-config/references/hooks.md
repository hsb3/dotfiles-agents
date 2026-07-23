# Hooks

A hook is a script the **harness runs automatically** when a named event fires. Hooks are the
*only* mechanism that can keep an "always / every time / whenever X" promise, and the ratified
layout for one is a **directory with a script plus its config — never an inline shell string**.

## Why automation must be a hook

"Whenever X happens, do Y" is a guarantee about the harness's behavior, and only the harness can
guarantee it. The harness *executes* a hook every time its event fires — deterministically, with
no model judgment in the loop. By contrast, anything written into instructions, a memory file,
or a CLAUDE.md is **read as guidance**, not executed: the model may follow it, may not, and
certainly won't on the turn where it wasn't looking. So:

> If a request says "always", "every time", "whenever", "automatically", or "on every X" — the
> correct implementation is a **hook**, not a sentence added to instructions or memory. Encoding
> it as prose will appear to work and then silently fail intermittently.

Convert such a request into: pick the event, write the script, wire it into settings.

## The events

| Event | Fires… | Typical use |
|---|---|---|
| `PreToolUse` | before a tool call runs | gate/validate/log a command before it executes; can block it |
| `PostToolUse` | after a tool call completes | format-on-save, run a check on what was just edited |
| `UserPromptSubmit` | when the user submits a prompt | inject context, warn, or block the prompt |
| `SessionStart` | at the start of a session | surface state to a fresh session |
| `PreCompact` | before context is compacted | guard or checkpoint before compaction |
| `Stop` | when the agent finishes responding | end-of-turn bookkeeping |

Other events exist (for example a subagent-finished event and session-end/notification events);
consult the current hooks documentation for the full set. The six above cover the common cases.

## Matchers

Within an event, a matcher selects *which* occurrences the hook runs on:

- **`PreToolUse` / `PostToolUse`** — the matcher is a **tool-name pattern**: `Bash`, an
  alternation like `Edit|Write`, `*` for all tools, or a regex such as `mcp__.*` for any MCP
  tool.
- **Events without a tool** (`UserPromptSubmit`, `SessionStart`, `PreCompact`, `Stop`) — use
  `*` (or omit the matcher). Some of these accept a source qualifier (for example a
  compaction being manual vs automatic); use `*` unless you specifically need to narrow it.

## The ratified layout: a hook is a directory

**Do not paste shell into settings.** The `command` field of a hook must invoke a **script file
by path** — the executable behavior lives in a versioned, reviewable file, not in a JSON string.
A hook is therefore a small directory:

```
hooks/command-log/
  config.json     # the event binding and run options (event, matcher, timeout, statusMessage)
  hook.py         # the behavior — Python 3 standard library only, fails open
```

A working template ships in this skill at `assets/example-hook/` (`config.json` + `hook.py`).
Copy it into your project's hook directory and adapt it.

### Why the directory layout, not an inline command

- **Versioned and reviewable** — the logic is a file in the repo, diffable in a PR. An inline
  shell blob is invisible to review and untestable.
- **No quoting minefield** — multi-line logic pasted into a JSON `command` string becomes an
  escaping nightmare that breaks silently.
- **Portable** — the script is referenced through a root variable
  (`$CLAUDE_PROJECT_DIR` for a project hook, or the plugin-root variable for a distributed one),
  so it works on any machine that installs it, with no absolute paths baked in.
- **Stdlib-only** — the script depends on nothing that must be installed, so it runs everywhere.

### Wiring it into settings

The settings `hooks` block references the script **by path through a root variable** — it does
not contain the logic:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/command-log/hook.py\"",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

A validatable copy (with a second `PostToolUse` example) is in
`references/examples/hook.settings.json`. Note the `command` is a *call to the script file*,
carrying only an interpreter and a path — never embedded program logic.

## The script contract

A hook script reads a JSON event payload on **stdin** and communicates back through its **exit
code** and, optionally, **stdout**:

- **Exit `0`** — success. For most events stdout is informational; for `UserPromptSubmit` and
  `SessionStart` stdout can be added to the model's context.
- **Exit `2`** — blocking error: stderr is fed back to the agent and the action is blocked
  (where the event supports blocking, e.g. `PreToolUse`).
- **Any other non-zero** — non-blocking error: surfaced to the user, the action proceeds.
- **Structured control** — printing a JSON object on stdout lets a hook return fields like
  additional context or a systemMessage instead of relying on the raw exit code.

**Fail open.** A hook that errors should not break the session — catch everything and exit `0`
unless blocking is the explicit intent. The template demonstrates this.

## The executable-bit failure mode

How the script is invoked decides whether it needs an executable bit:

- **Invoked via an interpreter** — `command: "python3 \"…/hook.py\""` — the exec bit is **not**
  required; `python3` runs the file regardless. This is the recommended, most portable form and
  the one the wiring example uses.
- **Invoked directly** — `command: "\"…/hook.py\""` (no interpreter) — the file **must** be
  executable (`chmod +x hook.py`) **and** carry a shebang (`#!/usr/bin/env python3`) on line one.
  A directly-invoked script without the exec bit fails to run, often silently.

Give every hook script a shebang and `chmod +x` regardless — it costs nothing and removes the
whole class of "hook installed but never fires" bugs.

## Verify a hook took effect

Hook changes are **snapshotted at startup** — an add/edit/remove does not reach the running
session, by design. So: save, validate the JSON, **start a fresh session**, confirm the hook is
registered with the `/hooks` command, then trigger its event and confirm it fires. Details in
`references/verification.md`.
