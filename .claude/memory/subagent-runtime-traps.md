---
name: subagent-runtime-traps
description: /clear re-homes a running subagent instead of killing it, and an agent's memory frontmatter litters the tree
metadata:
  type: project
---

**`/clear` does not kill a running subagent; it re-homes it.** Measured 2026-08-23: a 70-minute `atelier:manager` survived a `/clear`, finished its wave, and answered `SendMessage`. Its files split: the old session dir keeps `agent-<id>.meta.json` (the sidecar) and the pre-clear transcript; the new dir gets only a fresh transcript. `agent_id` is stable across the boundary; the session dir is not. **How to apply:** resolve subagent state by `agent_id` across sibling session dirs. When widening a lookup, widen only the settled set; widening the started universe reports every delegation the project ever ran as stalled. That asymmetry is deliberate in `subagent-telemetry` and pinned by a test.

**An agent definition's `memory:` key creates `<cwd>/.claude/agent-memory/<agentType>/` at dispatch**, even empty. The enum is `user | project | local` with no off; omitting the key is the only way to disable it, and no prose in the agent body prevents the mkdir. No atelier agent has set it since 2026-08-07, so litter here means some other definition carries the key. **How to apply:** after a worker wave, before `git add`, check `git status` for stray nested `.claude/` dirs; read them (worker doctrine is sometimes worth promoting), then delete the exact `??` paths git shows. Never `git rm -r --cached` a parent dir; that once swept five tracked memory files. Anything showing `delete mode` was tracked: stop.

Related: [[worktree-isolation]], [[signals-that-lie]].
