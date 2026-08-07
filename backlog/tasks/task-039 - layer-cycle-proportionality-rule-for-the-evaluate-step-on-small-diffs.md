---
id: TASK-039
title: 'layer-cycle: proportionality rule for the evaluate step on small diffs'
status: In Progress
assignee:
  - '@claude'
created_date: '2026-08-06 23:49'
updated_date: '2026-08-07 00:44'
labels:
  - primitives
milestone: m-2
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/256'
priority: low
type: docs
ordinal: 17000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GH issue #256: layer-cycle's process mandates a full persona-diverse rubric-panel as the evaluate step every cycle. Running a bug-fix wave of five backlog bugs (diffs from one line to ~50 lines), a full panel per cycle would have cost more than the builds. What actually worked and converged in <=2 cycles per task: a one-line diff got a foreman spot-check with no agent (observed-red evidence made the assertion non-vacuous); 20-50-line diffs got a single adversarial reviewer (re-derive + re-run + attack), which caught a real residual defect; module-scale artifacts would earn the panel's cost (did not arise in that run). The current text reads as panel-always, which either burns budget on trivial cycles or trains users to skip the evaluate step entirely. Checked #260: only layer-cycle/README.md's foreman-kit -> atelier rename touched this skill, so the sizing gap is still open.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 layer-cycle (and/or the foreman skill's cheat-sheet) states a sizing rule for the evaluate step: spot-check vs single reviewer vs rubric-panel, chosen by diff size / coupling / stakes
- [ ] #2 The panel is explicitly framed as reserved for module-scale or contested artifacts, not the default for every cycle
<!-- AC:END -->
