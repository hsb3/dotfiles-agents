---
name: backlog-cli-rewrites-sibling-tasks
description: "Backlog.md CLI writes can silently overwrite task files you didn't touch, pulling stale/foreign state from its index"
metadata: 
  node_type: memory
  type: project
  originSessionId: 898540dc-edd5-4177-a8b4-6909448e0fba
---

In dotfiles-agents, a single `backlog task create`/`edit` can rewrite **other** task files
from the CLI's internal index, not just the one you targeted. Observed 2026-08-04: editing
task-10 + creating task-26 also overwrote task-9, task-10, task-11 with content from a
different branch's uncommitted task-state cache (#235's foreman-kit review-cycle work had
marked TASK-9/10/11 Done with `rubric-panel`/`layer-cycle`/`e3-ts` proof notes that never
belonged to those tasks — and never made it into #235's actual commit, which only added 3
skills). The stale versions leaked into the working tree via the CLI's index on the next write.

**Why:** the Backlog.md CLI runs `auto_commit: false` here and materializes task files from its
index; a concurrent/prior session's cached edits to sibling task IDs get flushed to disk when
you next invoke it.

**How to apply:** after ANY `backlog task` write, `git status`/`git diff` **all** task files —
not just the one you edited — and `git restore --source=dev` any that changed unexpectedly.
When a file must be edited precisely (re-applying a legit change after cleanup), use the Edit
tool directly rather than the CLI. Cross-check against `origin/dev` if a PR merged mid-session.
Relates to [[worktree-agents-check-out-published-commit]] — both are index/branch-state leaks in
this repo's multi-session backlog workflow.
