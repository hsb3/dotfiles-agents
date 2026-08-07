---
id: TASK-036
title: 'atelier: delegation ledger records the parent session, not the delegation'
status: Done
assignee:
  - '@claude'
created_date: '2026-08-06 23:49'
updated_date: '2026-08-07 00:55'
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
- [x] #1 logs/delegation.jsonl's agent_type is populated for every real delegation row, sourced from the subagent's own subagents/agent-<agent_id>.meta.json, not left empty
- [x] #2 model and ctx_tokens in each row reflect the subagent's own dispatch model and usage, not the parent session's
- [x] #3 Ledger row count for a session matches its actual delegation count -- rows with no matching subagents/ transcript entry are dropped rather than written
- [x] #4 A behavior test proves it: a fixture with N real delegations produces exactly N correct ledger rows
- [x] #5 HANDOFF.md's 'don't trust logs/delegation.jsonl until #250 is fixed' gotcha is removed once verified true
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Fixed test-first. Red run before any hook change: 19 of 25 new tests failed, including 'AssertionError: 10 != 3' on the row-count test, "'' != 'atelier:scout'" on agent_type, and "'claude-parent-model-9' != 'claude-sonnet-5'" on the parent-vs-subagent model test. Green after: 25 tests OK; full suite 269 OK; make ci exit 0.

Two assumptions in the diagnosis were WRONG and were corrected against real data rather than coded around. (1) The sidecar carries no token/usage key at all — a survey of all 2908 agent-*.meta.json files on disk found agentType/description/toolUseId on 2908/2908 but no usage field, so ctx_tokens must come from the sibling subagents/agent-<id>.jsonl transcript (message.usage.*), not the sidecar. (2) 'model' is present on only 256/2908 sidecars (8.8%) because it is the dispatch OVERRIDE, not the effective model; sidecar-only sourcing would leave model null in 91% of rows. Precedence adopted: sidecar override wins, else the subagent transcript's model — never the parent's, either way.

Also corrected a false claim in the hook's own docstring: the payload's transcript_path is the PARENT session's transcript, not the subagent's. That was the actual mechanism of D2 — two sibling delegations logged byte-identical ctx_tokens of 147107.

Real-data verification beyond fixtures: replayed all 262 rows of the existing logs/delegation.jsonl through the fixed hook (output to scratch, ledger untouched). 262 events produced 29 rows, a ~9x reduction matching the reported ~10x inflation, and 29 equals the sidecar count on disk exactly — so no over-dropping. One completed session went 128 rows to 9, its exact sidecar count. agent_type populated 29/29. ctx_tokens now 28 distinct values across 29 rows (was one parent value repeated per session). Sidecar mtimes precede transcript mtimes, confirming the sidecar is written at dispatch and therefore always exists when SubagentStop fires — the drop rule cannot lose a live delegation.

Fail-open matrix (all assert exit 0, empty stdout, no partial row): no subagents dir; dir present but empty; malformed-JSON sidecar; valid JSON that is not an object; sidecar missing agentType with and without a payload fallback; unreadable sidecar (chmod 000); missing subagent transcript; binary-garbage transcript; agent_id absent; agent_id set to a path-escape string; transcript_path absent; garbage stdin; empty stdin.

Judgment call worth knowing: the model column now carries a mixed vocabulary — in the 29 replayed rows, 11 are the bare dispatch alias (opus/sonnet) and 18 are full model ids. Tier is derivable by substring from both, so this was left as-is; flipping precedence would make it uniform at the cost of no longer recording the dispatch decision.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-08-06 23:59
---
D4 (/reload-plugins misreporting skill count) independently reproduced a second time, 2026-08-06: /reload-plugins printed 'Reloaded: 9 plugins · 0 skills · 11 agents · 7 hooks · 0 plugin MCP servers · 0 plugin LSP servers' in a live session where 14+ skills from those same 9 dotfiles-agents user-scope plugins (6 from atelier alone) were visibly loaded and invocable immediately before and after the reload. Plugin/agent/hook counts in that same output were all correct (9 plugins, 7 hooks matching atelier's shipped hook count, 11 agents). Only the skill count is wrong, both times observed. Likely a Claude Code core display bug rather than an atelier defect -- probably out of scope for this task's hook fix, but worth confirming before ruling out, since it's the same symptom shape as issue #244's now-closed skills-not-loading investigation.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The delegation ledger now measures delegations instead of the parent session. agent_type and model come from each subagent's own meta.json sidecar, ctx_tokens from its transcript, and rows with no matching sidecar are dropped — which fixes the ~10x inflation in the same move. Verified three ways: 25 new tests with a captured red run, a 2908-file survey establishing the real sidecar schema (which disproved two assumptions in the original fix plan), and a replay of the live 262-row ledger producing exactly the 29 rows the sidecars on disk predict. The HANDOFF gotcha is replaced with the real caveat: rows are trustworthy from 2026-08-07 forward, but pre-fix history is not salvageable and must be truncated before any tier analysis.
<!-- SECTION:FINAL_SUMMARY:END -->
