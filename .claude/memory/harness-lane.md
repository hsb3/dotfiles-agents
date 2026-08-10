---
name: harness-lane
description: The agent-harness lane — standing commit/push/PR/merge permission (dev only) and the claude invocation that actually works
metadata: 
  node_type: memory
  type: project
  originSessionId: f88d2c41-439c-40b6-bbea-2ee31abb84ec
  modified: 2026-08-10T02:01:32.472Z
---

**Standing permission (Henry, 2026-07-21):** commit, push, open PRs, and squash-merge on the
harness lane once the wave's gates pass (`make ci`, `make harness-test`, live smoke where
required). Never extends to `main` (publish-only, CI-guarded) and covers no other lane. After
opening any PR, watch CI to green and report.

**claude invocation — Option Z.** Do **not** use `claude --bare`: it skips keychain reads *and*
strips the Skill/Task tools (`CLAUDE_CODE_SIMPLE=1`), which voided every claude skill-cell in the
first eval grid. Instead: no `--bare`, a per-run `apiKeyHelper` (echoes `$ANTHROPIC_API_KEY`) via
`--settings`, plus a fresh per-run `CLAUDE_CONFIG_DIR` with `plugins: []` — better isolation than
`--bare` ever gave. Live runs still need
`export ANTHROPIC_API_KEY="$(secret get ANTHROPIC_API_KEY)"` first.

Ledger rows from before the fix carry campaign `""` (confounded claude cells); post-fix re-runs
are campaign `skillfix`.
