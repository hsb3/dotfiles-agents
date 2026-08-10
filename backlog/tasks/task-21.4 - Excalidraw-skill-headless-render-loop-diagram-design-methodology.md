---
id: TASK-21.4
title: 'Excalidraw skill: headless render loop + diagram-design methodology'
status: To Do
assignee: []
created_date: '2026-08-04 00:43'
updated_date: '2026-08-10 02:24'
labels:
  - primitives
milestone: m-3
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/168'
parent_task_id: TASK-21
priority: low
type: feature
ordinal: 1350
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add to the authored `excalidraw` skill the two capabilities the dropped upstream package (`excalidraw-diagram-coleam00`, MIT) had and ours lacks, implemented first-party — in our own words/design, not copied (ADR 0015):

1. An automated headless render -> view -> fix loop (Playwright-based) so the model can see and iterate on its diagram. Ours currently stops at 'no official headless CLI'.
2. A diagram-design methodology layer: evidence artifacts, visual pattern library, depth assessment, section-by-section workflow for large diagrams, quality checklist. Ours covers file-format mechanics only.

The upstream drop was correct; this captures the residual value identified in the drop review.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Headless render loop runs end-to-end on a sample diagram — render, screenshot, detect a defect, produce a corrected render — with no copied upstream body
- [ ] #2 Methodology layer shipped in the skill, first-party
- [ ] #3 make ci green
<!-- AC:END -->
