---
name: subagent-agent-memory-litter
description: foreman-kit worker agents may write .claude/agent-memory/ into their working dir — sweep before committing
metadata: 
  node_type: memory
  type: reference
  originSessionId: 2be61392-0223-4be0-b571-1d7471c67169
  modified: 2026-07-21T16:27:43.714Z
---

Subagents with agent-memory enabled (observed with `foreman-kit:reviewer`, 2026-07-20)
can write a nested `.claude/agent-memory/<agent-name>/` directory into whatever directory
they were working in — not the repo root. It shows up as an untracked `?? <dir>/.claude/`
in `git status` and would land in the commit if the parent dir is `git add`-ed wholesale.

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
