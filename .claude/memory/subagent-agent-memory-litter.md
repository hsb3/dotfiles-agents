---
name: subagent-agent-memory-litter
description: agent-memory litter comes from an agent's `memory:` frontmatter key, not its behavior — no atelier agent sets it since 2026-08-07, so new litter means a non-atelier agent
metadata: 
  node_type: memory
  type: reference
  originSessionId: 2be61392-0223-4be0-b571-1d7471c67169
  modified: 2026-08-07T01:14:28.282Z
---

**Root cause, established 2026-08-07: the directory comes from the agent definition's
`memory:` frontmatter key, not from anything the agent does.** The Claude Code runtime
resolves `memory: project` to `<cwd>/.claude/agent-memory/<agentType>/` and creates it at
dispatch. Proof: an `atelier-reviewer/` directory was found **empty** — a zero-file directory
cannot have been written by an agent, so the runtime made it from the frontmatter alone. The
schema enum is `user | project | local` and the field is optional; there is no `off` value, so
**omitting the key is the only way to disable it.** No prose instruction in an agent body can
prevent the `mkdir`, which is why briefs saying "report-only, no scratch files" never worked.

**No atelier agent sets `memory:` as of 2026-08-07** (removed from `reviewer.md`, the only one
that had it). So a fresh `.claude/agent-memory/` appearing in this repo now means some *other*
agent definition carries the key — check its frontmatter rather than assuming misbehavior.

Historic shape, still worth recognizing: the directory lands in whatever directory the agent
was working in, not necessarily the repo root, showing up as an untracked `?? <dir>/.claude/`
that would land in the commit if the parent dir is `git add`-ed wholesale.

**How to apply:** after any worker wave, before `git add`, check `git status` for stray
nested `.claude/` dirs. The memory files inside are sometimes genuinely good distilled
doctrine (the reviewer's duplicative-false-positives note fed extender-db's INSIGHTS) —
read them, promote anything valuable into the project's insights/docs, then delete the
stray directory. Related: [[reference-worktree-agent-isolation]].

**Scope the sweep to the worker-created paths ONLY.** Since 2026-07-22 this repo's tracked
memory lives at `.claude/memory/` (renamed from `.claude/agent-memory/` when the project
auto-memory redirect was wired), so any worker-dropped `.claude/agent-memory/` is now
**unambiguous litter** — no name collision with the tracked store. Still: delete the specific
new `?? ` paths git shows, never a parent dir with a whole-directory
`git rm -r --cached`. (Under the old name, one such wholesale rm swept five tracked memory
files with one reviewer's litter subdir and needed a restore commit `c2133fe`; the rename
removes that trap but the discipline stands.) Anything staged `A` is new (litter candidate);
anything the commit output shows as `delete mode` was tracked — stop.
