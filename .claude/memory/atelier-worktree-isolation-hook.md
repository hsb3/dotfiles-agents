---
name: atelier-worktree-isolation-hook
description: "Two levers force subagent worktree isolation — PreToolUse updatedInput on the Agent tool, and an `isolation` agent-frontmatter key"
metadata: 
  node_type: memory
  type: reference
  modified: 2026-08-07T05:57:31.310Z
  originSessionId: e133a0fd-6378-430e-bea4-d8f30120264a
---

Harness contract verified by live probe against Claude Code 2.1.220 (perishable — re-verify at
each curation pass). Two ways to make a subagent run in its own worktree instead of the parent
checkout:

1. **`PreToolUse` hook, matcher `Agent`.** The payload's `tool_name` is `Agent` (not `Task`) and
   carries the full dispatch. Returning
   `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "updatedInput": {...}}}` rewrites the
   tool input in place — no deny, no model retry. `updatedInput` is **PreToolUse-only**.
2. **Agent-definition frontmatter.** `isolation: worktree` is a valid frontmatter key. Resolution
   order is `explicit tool param ?? agentDefinition.isolation`, so frontmatter is the default and a
   dispatch can still override it.

Atelier ships lever 1 as the `worktree-isolation` hook (opt-in per project via `isolate:` in
`.claude/atelier.local.md`) rather than lever 2, so the behavior is not always-on for every
consumer of the plugin.

**Constraints that bit during the build:** forcing isolation outside a git repo is a hard error
(`Cannot create agent worktree`), not a no-op; the `cwd` Agent param is mutually exclusive with
`isolation: "worktree"`; `fork` + `isolation: "remote"` is rejected; and a worktree cannot see the
parent's uncommitted work (see [[worktree-agents-check-out-published-commit]]).

**How to apply:** when a harness behavior like this is in question, probe it — a headless
`claude -p --settings <file>` run in a throwaway git repo, with a logging hook, answers in one
round-trip and beats reasoning from the docs. Grepping `strings` over
`~/.local/share/claude/versions/<v>` surfaces the schemas and error strings the docs omit.
