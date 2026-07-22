---
name: harness-bare-flag-auth
description: "harness claude runs use Option Z (no --bare; apiKeyHelper + fresh CLAUDE_CONFIG_DIR); live runs still need ANTHROPIC_API_KEY via `secret get`"
metadata: 
  node_type: memory
  type: project
  originSessionId: 7cd91ebc-af47-437b-8eec-c3a53e5836ad
  modified: 2026-07-21T21:44:33.247Z
---

Agent-harness claude invocation history (merged to dev via PR #169, 2026-07-21):

- Wave 1 used `claude --bare`, which **skips keychain reads AND strips the Skill/Task tools**
  (`CLAUDE_CODE_SIMPLE=1`) — that voided all claude skill-cells in the first grid (#170).
- Wave 4 replaced it with **Option Z**: no `--bare`; per-run `apiKeyHelper` (echoes
  `$ANTHROPIC_API_KEY`) via `--settings` + fresh per-run `CLAUDE_CONFIG_DIR` (plugins: [] — better
  isolation than --bare ever gave). Probe matrix: `_meta/research/agent-harness/handoff-w4.md` §1.
- Live runs STILL require `export ANTHROPIC_API_KEY="$(secret get ANTHROPIC_API_KEY)"` first.
- Ledger rows before the fix are campaign `""` (confounded claude cells); post-fix re-runs are
  campaign `skillfix`. Related: [[agent-harness-standing-permission]].
