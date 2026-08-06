---
id: TASK-21.4
title: 'Excalidraw skill: headless render loop + diagram-design methodology'
status: To Do
assignee: []
updated_date: '2026-08-06'
created_date: '2026-08-04 00:43'
labels:
  - extender-db
  - skills
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
Add to the authored `excalidraw` skill the two capabilities the dropped upstream (`excalidraw-diagram-coleam00`, MIT) had and ours lacks — implemented first-party in our own words/design (ADR 0015; authored, not copied): (1) an automated headless render -> view -> fix loop (Playwright-based) so the model can see and iterate on its diagram — ours currently stops at "no official headless CLI"; (2) a diagram-design methodology layer: evidence artifacts, visual pattern library, depth assessment, section-by-section workflow for large diagrams, quality checklist — ours covers file-format mechanics only. The upstream drop was correct; this captures the residual value identified in the drop review. Substance from closed GH #168.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Headless render loop works in the authored skill with no copied upstream body
- [ ] #2 Methodology layer shipped in the skill, first-party
- [ ] #3 make ci green
<!-- AC:END -->
