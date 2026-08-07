---
id: TASK-040
title: >-
  Review overlap: claude-code-config vs claude-code-expertise - one plugin or
  two?
status: To Do
assignee: []
created_date: '2026-08-06 23:59'
updated_date: '2026-08-07 00:01'
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
- [ ] #1 Read both skills' full bodies (not just descriptions) and state concretely where they overlap vs. diverge -- cite path:line for any near-duplicate guidance
- [ ] #2 Recommend keep-as-two-plugins, merge-into-one-plugin-two-skills, or merge-into-one-skill, with the reasoning that decided it
- [ ] #3 If a merge is recommended, name the plugin-id/version-bump/catalog-row/install-migration impact (same shape as the foreman-kit -> atelier rename in #260) before it's executed as a separate task
<!-- AC:END -->
