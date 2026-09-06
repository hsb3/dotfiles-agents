---
name: harness-claude-invocation
description: How the eval harness invokes claude so the Skill tool survives — never --bare
metadata:
  type: project
---

For `harness/` runs (`scripts/harness_campaign.sh`), do **not** use `claude --bare`: it skips keychain reads and strips the Skill/Task tools (`CLAUDE_CODE_SIMPLE=1`), which voided every claude skill cell in the first eval grid. Instead: no `--bare`, a per-run `apiKeyHelper` that echoes `$ANTHROPIC_API_KEY` via `--settings`, and a fresh per-run `CLAUDE_CONFIG_DIR` with `plugins: []` — better isolation than `--bare` gave. Live runs need `export ANTHROPIC_API_KEY="$(secret get ANTHROPIC_API_KEY)"` first. Ledger rows from before the fix carry campaign `""`; post-fix re-runs are campaign `skillfix`.

The git-loop grant that used to live here is now law in AGENTS.md § Governance.
