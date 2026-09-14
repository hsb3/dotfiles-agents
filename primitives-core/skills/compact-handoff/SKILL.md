---
name: compact-handoff
description: Update and verify the session handoff, then prepare a KEEP/DROP compaction prompt that preserves active agents and dependent commands. Use when asked to compact with a handoff or prepare session compaction.
---

# Compact with a handoff

Keep this session alive when work still depends on its native handles. Compaction is
not a new session, a process restart, or permission to terminate background work.

## 1. Persist first

Invoke the existing `handoff` skill's update pass. Use its selected destination and
session identity; do not choose another card, file, stamp, or storage convention.
Require a fresh readback of the written handoff, confirming this session's current
state and destination. In external mode require the body readback before the handoff
skill's final stamp update; a successful write response or fresh stamp alone is not proof.
In file mode read the written file back. If invocation, write, readback, or required
stamp update fails, report the failure and STOP: do not offer or trigger compaction.
If the handoff skill is unavailable, stop rather than inventing its implementation.

## 2. Preserve live state

Read [the KEEP/DROP template](references/keep-drop.md). Fill it from this session and
current status surfaces; preserve exact identifiers and instructions, not guesses.
Include every active agent and dependent command, even when idle or awaiting input.
Keep unknown status explicit; an empty list means verified none, not uninspected.
Exclude secrets. Keep a restricted record's pointer instead of copying its contents.
Print the completed prompt in a fenced block for the owner to paste. Put the verified
handoff pointer in it; do not summarize any exact handle, ruling, permission scope, or next wait.
Refresh the handoff and prompt if consequential state changes before compaction.

## 3. Use the actual runtime surface

Read [runtime support](references/runtime-support.md) for the installed runtime/version.
An owner slash command, client API, or hook event does not itself expose an agent tool.
Invoke compaction only when a supported tool in THIS session accepts the intended
prompt and preserves the session. Wait for its completion event before claiming success.
Do not send terminal keystrokes to yourself, launch a replacement runtime, or create an
API bridge/configuration change to turn a user-only command into an agent tool.

<!-- harness:claude-code -->
Verified 2026-09-10: Claude Code 2.1.266 and Codex CLI 0.154.0 have no established
ordinary agent-callable compaction tool. Claude Code's Skill tool cannot invoke
`/compact`. Stop after printing the prompt and say once that manual compaction remains.
For Claude Code, print `/compact <completed KEEP/DROP prompt>` as the pasteable block.
For Codex, print the KEEP/DROP prompt as a normal message to submit first, then tell
the owner to run `/compact` separately; custom slash-command arguments are not assumed.
Use `atelier:compact-handoff` directly or `/atelier:prepare-compact`; the differently
named tiny command avoids shadowing the skill. Codex loads the skill directly.
<!-- /harness -->

For an unknown runtime, leave the prompt ready and identify invocation as unverified.
After compaction, read the retained prompt/handoff and use each recorded next wait or
resume action on its original handle. If a handle is unavailable, report that loss;
do not silently respawn work or claim continuity merely because a summary appeared.
