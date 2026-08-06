---
id: TASK-036
title: 'atelier: delegation ledger records the parent session, not the delegation'
status: To Do
assignee: []
created_date: '2026-08-06 23:49'
labels:
  - primitives
milestone: m-2
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/250'
  - 'https://github.com/hsb3/dotfiles-agents/issues/252'
priority: high
type: bug
ordinal: 14000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The subagent-telemetry hook's ledger (logs/delegation.jsonl) is meant to give one row per delegation with the subagent's own agent_type, model, and context tokens. Verified defects (GH issue #250, reproduced on this repo): agent_type is empty in the large majority of rows; model and ctx_tokens record the *parent session's* values, not the subagent's; total row count runs roughly 10x the actual delegation count. Net effect: the kit cannot measure whether it actually delegated, so the H8 tier A/B mechanism and the new tier-cutoff protocol (primitives-core/skills/foreman/references/tier-cutoff.md, shipped in #260/atelier 0.8.0) both depend on data this hook does not produce. #260 (the foreman-kit -> atelier rename + doctrine rewrite) did NOT fix this hook -- confirmed by diff, only a foreman-kit -> atelier string rename touched it. GH issue #252 Appendix B already scoped the fix: Claude Code writes a sibling subagents/agent-<agent_id>.meta.json next to every subagent transcript containing agentType, the dispatch-override model, and spawnDepth -- read those instead of the parent session's fields, and drop ledger rows that have no matching subagents/ transcript entry (this also fixes the ~10x row inflation in the same move).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 logs/delegation.jsonl's agent_type is populated for every real delegation row, sourced from the subagent's own subagents/agent-<agent_id>.meta.json, not left empty
- [ ] #2 model and ctx_tokens in each row reflect the subagent's own dispatch model and usage, not the parent session's
- [ ] #3 Ledger row count for a session matches its actual delegation count -- rows with no matching subagents/ transcript entry are dropped rather than written
- [ ] #4 A behavior test proves it: a fixture with N real delegations produces exactly N correct ledger rows
- [ ] #5 HANDOFF.md's 'don't trust logs/delegation.jsonl until #250 is fixed' gotcha is removed once verified true
<!-- AC:END -->
