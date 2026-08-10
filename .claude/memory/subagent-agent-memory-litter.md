---
name: subagent-agent-memory-litter
description: "A stray .claude/agent-memory/ dir comes from an agent's `memory:` frontmatter key, not from misbehavior — omitting the key is the only off switch"
metadata: 
  node_type: memory
  type: reference
  originSessionId: f88d2c41-439c-40b6-bbea-2ee31abb84ec
  modified: 2026-08-10T02:01:46.444Z
---

The runtime resolves an agent definition's `memory: project` frontmatter to
`<cwd>/.claude/agent-memory/<agentType>/` and creates it at dispatch — proof: one such directory
was found completely empty. The enum is `user | project | local` with no `off`, so **omitting the
key is the only way to disable it**, and no prose instruction in an agent body can prevent the
`mkdir`. No atelier agent has set `memory:` since 2026-08-07, so fresh litter here means some
*other* agent definition carries the key — check its frontmatter.

**How to apply:** after a worker wave, before `git add`, check `git status` for stray nested
`.claude/` dirs. Read the files first (distilled worker doctrine is sometimes worth promoting),
then delete **the specific `?? ` paths git shows** — never a parent dir with a wholesale
`git rm -r --cached`, which once swept five tracked memory files and needed a restore commit.
This repo's tracked memory is `.claude/memory/`, so `.claude/agent-memory/` is unambiguous litter.
Anything staged `A` is a litter candidate; anything showing as `delete mode` was tracked — stop.
