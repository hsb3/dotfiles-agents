---
id: TASK-040
title: >-
  Review overlap: claude-code-config vs claude-code-expertise - one plugin or
  two?
status: Done
assignee:
  - '@claude'
created_date: '2026-08-06 23:59'
updated_date: '2026-08-07 00:50'
labels:
  - assembly
dependencies: []
references:
  - plugins/claude-code-config
  - plugins/claude-code-expertise
priority: medium
type: spike
ordinal: 18000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Both are single-skill plugins in this repo's own marketplace, both about Claude Code the harness itself: claude-code-config (primitives-core/skills/claude-code-config) is action-oriented -- route a settings change to the right file by precedence, write narrowest-scope permissions, author a ratified directory-based hook, register env vars/MCP servers, then verify JSON validity and take-effect. claude-code-expertise (primitives-core/skills/claude-code-expertise) is reference-oriented -- a surface-selection decision table across skills/subagents/hooks/commands/plugins/marketplaces/MCP/settings, each surface's frontmatter/config contract, subagent authoring end to end, and distribution mechanics. Their descriptions both name settings/permissions/hooks/MCP registration as covered territory, which is exactly the kind of split that produces the wrong pick or duplicated guidance -- worth checking now, before two more sessions load different fixes into overlapping territory. Two live questions: (1) are the skills' actual bodies (not just their descriptions) sufficiently non-overlapping in what they tell an agent to do, or does one already subsume the other; (2) if they stay distinct, should they still ship as separate installable plugins, or as one plugin with two skills (matches this repo's existing dual-homing pattern for skills that are genuinely one bundle's concern).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Read both skills' full bodies (not just descriptions) and state concretely where they overlap vs. diverge -- cite path:line for any near-duplicate guidance
- [x] #2 Recommend keep-as-two-plugins, merge-into-one-plugin-two-skills, or merge-into-one-skill, with the reasoning that decided it
- [x] #3 If a merge is recommended, name the plugin-id/version-bump/catalog-row/install-migration impact (same shape as the foreman-kit -> atelier rename in #260) before it's executed as a separate task
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Spike executed 2026-08-07 by a reviewer that read both SKILL.md files and every references/ file in full, with paired path:line citations required on both sides of every overlap claim.

Finding: overlap is REAL but ASYMMETRIC and confined to one file. Roughly 88 of the 152 lines in claude-code-expertise/references/surfaces.md (sections 2/4/5) restate territory claude-code-config covers in more depth. Config restates nothing of expertise's. Config's unique job (the seven-step edit workflow, SKILL.md:131-145, plus references/verification.md) has no counterpart in expertise; expertise's unique job (subagents.md, authoring.md, distribution.md — 252 lines on surfaces config never mentions) has no counterpart in config.

Trigger collision assessed separately from content overlap. Config's description uses quoted user utterances, expertise's uses capability verbs; a stopword-stripped token diff shares only: claude, code, command, config, hook, hooks, mcp, skill, surface, surfaces, works. Config wins the action verbs ('add a deny rule', 'register an MCP server'); expertise wins the explain verbs. The one case that routes WRONG is 'how do hooks work?' — it goes to expertise, i.e. to the shallower copy that carried the defects below. Neither description disclaims the other's territory, so nothing arbitrates the matcher.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
RECOMMENDATION: keep as two plugins. Merging into one skill is wrong (a ~1000-line skill spanning 'fix my permission' and 'pick a subagent model tier'; violates the progressive-disclosure principle expertise itself teaches). Merging into one plugin with two skills is the tempting answer and is also wrong for a decisive reason: two skills in one plugin still compete on description match, so it fixes none of the defects and none of the trigger collision — it pays a breaking marketplace change to relocate the problem. Cost asymmetry confirms it: wrong on keep-two costs a redundant install (mild, reversible); wrong on merge dangles every existing install record with no alias mechanism, rewrites gate-checked metadata, and needs a second breaking rename to undo.

The card asked one-plugin-or-two and the answer is two. But the spike found the duplication has already produced three shipped defects, which are the real cost: (a) a FACTUAL CONTRADICTION on hook exit codes — expertise/references/surfaces.md:63 said 'a non-zero exit on PreToolUse blocks the tool', while config/references/hooks.md:100-112 correctly documents exit 2 as blocking and any other non-zero as non-blocking-and-proceeds; (b) expertise's canonical hook example used a bare relative path, the exact silent-failure form config's docs name as 'installed but never fires'; (c) the hook-directory rule shipped as 'Prefer'/'Idiomatic' in expertise but 'non-negotiable' in config. The contradiction was independently re-derived by the dispatching session against both sources before acting. All three fixed in this PR. The larger de-duplication (trim surfaces.md to selection-relevant content, add mutual boundary clauses to both descriptions) is filed separately as TASK-042.
<!-- SECTION:FINAL_SUMMARY:END -->
