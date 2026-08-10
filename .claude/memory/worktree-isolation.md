---
name: worktree-isolation
description: "How subagent worktree isolation is forced in this repo, and the two things a worktree cannot see"
metadata: 
  node_type: memory
  type: reference
  originSessionId: f88d2c41-439c-40b6-bbea-2ee31abb84ec
  modified: 2026-08-10T02:48:07.885Z
---

Two levers make a subagent run in its own worktree (verified by live probe against Claude Code
2.1.220 — perishable):

1. **`PreToolUse` hook, matcher `Agent`** (`tool_name` is `Agent`, not `Task`). Returning
   `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "updatedInput": {...}}}` rewrites the
   dispatch in place — no deny, no model retry. `updatedInput` is PreToolUse-only.
2. **`isolation: worktree` in agent frontmatter.** Resolution is
   `explicit tool param ?? agentDefinition.isolation`.

Atelier ships lever 1 (`worktree-isolation` hook, opt-in per project via `isolate:` in
`.claude/atelier.local.md`) so it is not always-on for every consumer.

**Constraints that bite:** forcing isolation outside a git repo is a hard error, not a no-op;
the `cwd` param is mutually exclusive with `isolation: "worktree"`; `fork` + `isolation: "remote"`
is rejected; and **a worktree cannot see the parent's uncommitted or untracked files** — commit
first, or send a non-isolated agent (which is why scout/reviewer are never isolated).

**Base ref:** the key is **nested — `worktree.baseRef`**, and defaults to `fresh`, which branches
from `origin/<default-branch>` — here `main`, the publish-only surface, which is how worktree
agents land on a tree with no `primitives-core/`. **The flat spelling `worktreeBaseRef` is only the
`/config` menu's widget id, never a settings key** (binary 2.1.220: the handler reads
`r?.worktree?.baseRef ?? "fresh"` and writes `{worktree: {baseRef}}`), so a settings file using it
is silently ignored — this repo's own was, from `8ea83ba` until 2026-08-09, while three docs
asserted the fix was applied. `.claude/settings.json` now sets `worktree.baseRef: "head"`. If a
crew reports a missing `primitives-core/`, check the nesting first.

**How to apply:** when a harness behavior is in question, probe it — a headless
`claude -p --settings <file>` run in a throwaway git repo with a logging hook answers in one
round-trip and beats reasoning from the docs. `strings` over
`~/.local/share/claude/versions/<v>` surfaces schemas and error strings the docs omit.
