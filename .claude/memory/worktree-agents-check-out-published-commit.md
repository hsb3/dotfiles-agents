---
name: worktree-agents-check-out-published-commit
description: isolation:worktree Agent calls in this repo sometimes land on a published-surface commit instead of dev — every crew must verify and self-correct
metadata: 
  node_type: memory
  type: project
  originSessionId: e8267e32-b420-462d-92e9-8898d60d4877
  modified: 2026-07-23T01:06:59.274Z
---

`Agent({isolation: "worktree", ...})` calls in this repo have repeatedly (5/5 crews in the
2026-07-22 waves run) been checked out from a *published* commit — root has `plugins/`,
`opencode/`, no `primitives-core/`/`scripts/`/`docs/decisions/` — instead of `dev`, the actual
source branch.

**Why:** unclear (possibly a stale default ref cached by the worktree-isolation mechanism); not
yet root-caused.

**How to apply:** every brief for a worktree-isolated crew in this repo must include an explicit
check: if `primitives-core/` is missing after checkout, `git fetch origin && git reset --hard
origin/dev` before doing any work. Crews that did this self-corrected cleanly with no source
loss. Without the instruction, a crew could silently build on the wrong tree and open a PR with a
huge, wrong diff. See [[worktree-agent-isolation]] (global memory) for the related "may commit to
main" caution — this is a different failure mode (wrong base ref, not wrong branch target).
