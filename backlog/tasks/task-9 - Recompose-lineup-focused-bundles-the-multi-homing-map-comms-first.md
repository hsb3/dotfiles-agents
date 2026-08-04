---
id: TASK-9
title: 'Recompose lineup: focused bundles + the multi-homing map (comms first)'
status: To Do
assignee: []
created_date: '2026-08-04 00:42'
labels:
  - refactor
  - decision
dependencies:
  - TASK-2
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/221'
priority: medium
type: feature
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Migrated from GH #221. Under the symlink architecture a standalone is a directory + marketplace entry, so the mechanism is free; what remains is the ruling: which skills dual-home (comms first), bundle-composition principle as ADR extension, code-desk audit dispositions. Convention touchpoints (output dirs, handoff location) parameterized per-project — ties into task-15.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Bundle-composition principle ratified
- [ ] #2 comms installable without code-desk
- [ ] #3 Disposition recorded per code-desk skill
<!-- AC:END -->
