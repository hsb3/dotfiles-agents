---
id: TASK-12
title: 'SOP: configure Claude Code for a new project'
status: To Do
assignee: []
created_date: '2026-08-04 00:43'
updated_date: '2026-08-10 02:26'
labels:
  - governance
milestone: m-2
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/216'
priority: medium
type: feature
ordinal: 1500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Repeatable assess→decide→author→validate SOP for what agent-facing config a new repo gets (CLAUDE.md, agents, skills, settings, continuity scaffolding), grounded in this ecosystem's proven patterns. Ships as its own distributed skill — kept separate from claude-code-config per owner ruling 2026-08-07: the two answer different questions at different points in a project's life ("what should a new repo have at all" vs. "change a setting on a live installation"), and the TASK-040 spike found drift between them causes shipped defects. Validation target: tmp-learn-pocketbase.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 SOP authored and grounded in linked patterns
- [ ] #2 Re-running the SOP against tmp-learn-pocketbase produces a CLAUDE.md, skill/agent selection, and settings that satisfy every checklist item the SOP itself defines, checked item-by-item rather than by subjective judgment
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @claude
created: 2026-08-07 01:09
---
Owner ruling 2026-08-07: its OWN SKILL, not folded into claude-code-config.

Context that informed it: the TASK-040 spike ruled claude-code-config and claude-code-expertise stay separate precisely because they serve different audiences, and found three shipped defects caused by their content drifting together — including a factual error about hook exit codes. Adding a third concern to claude-code-config cuts directly against that finding.

The two answer different questions at different moments. claude-code-config answers 'change this setting on a live installation'; this answers 'what should a new repo have at all'. Different trigger, different user, different point in a project's life.

AC#2's dependency on re-running against an external repo remains the weak criterion — it has no defined pass signal ('a defensible config' is a judgment call). Worth tightening when the card is picked up.
---
<!-- COMMENTS:END -->
