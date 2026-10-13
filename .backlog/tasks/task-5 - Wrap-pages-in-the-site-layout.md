---
id: TASK-5
title: Wrap pages in the site layout
status: To Do
assignee: []
created_date: '2026-10-13 03:07'
labels: []
milestone: m-0
dependencies:
  - TASK-3
references:
  - layout
  - jsdelivr-cdn
priority: high
type: feature
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Every page must be exactly the document the SPEC fixes, because the stylesheet's selectors and the site's accessibility depend on it. Builds the groma ghost `layout` (src/layout.ts).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Head, skip link, header, nav, main, contents and footer match the SPEC example element for element and attribute for attribute
- [ ] #2 The current nav entry has `aria-current="page"`; labels are escaped
- [ ] #3 The contents block lists H1s and nested H2s, and is left out without an H2
- [ ] #4 Only pages with a Mermaid diagram get the Mermaid module script, verbatim
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
