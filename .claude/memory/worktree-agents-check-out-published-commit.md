---
name: worktree-agents-check-out-published-commit
description: isolation:worktree agents branch from origin/<default-branch> by default — root-caused to the worktreeBaseRef setting, fix is "head"
metadata:
  node_type: memory
  type: project
  originSessionId: e8267e32-b420-462d-92e9-8898d60d4877
  modified: 2026-08-07T05:57:18.710Z
---

`Agent({isolation: "worktree", ...})` calls in this repo land on a *published* commit — root has
`plugins/`, `opencode/`, no `primitives-core/`/`scripts/`/`docs/decisions/` — instead of `dev`.

**Why (root-caused 2026-08-07, was "unclear" before):** the `worktreeBaseRef` setting. Values are
`fresh` (the default) and `head`; `fresh` branches every new worktree from
`origin/<default-branch>`, and this repo's default branch is `main`, the publish-only surface. It
was never a stale cache — it is the documented default doing exactly what it says. The same
setting governs `--worktree`, `EnterWorktree`, and agent isolation.

**How to apply:** set `"worktreeBaseRef": "head"` in settings.json to branch worktrees from local
HEAD instead (unpushed commits and feature-branch state present). Until that is set, every brief
for a worktree-isolated crew must include the self-check: if `primitives-core/` is missing after
checkout, `git fetch origin && git reset --hard origin/dev` before doing any work.

**Second, independent gotcha:** a worktree is a clean checkout of a ref, so **uncommitted and
untracked files in the parent checkout are invisible inside it** — verified by live probe, a
worktree agent got "No such file or directory" for a file sitting in the parent. This is why
[[atelier-worktree-isolation-hook]] never isolates scout/reviewer, and why a builder that must see
uncommitted work needs it committed first.

See [[worktree-agent-isolation]] (global memory) for the related "may commit to main" caution — a
different failure mode (wrong branch target, not wrong base ref).
