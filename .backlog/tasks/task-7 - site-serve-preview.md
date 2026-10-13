---
id: TASK-7
title: site serve preview
status: To Do
assignee: []
created_date: '2026-10-13 03:07'
labels: []
milestone: m-0
dependencies:
  - TASK-6
references:
  - server
  - maintainer
priority: medium
type: feature
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Maintainers need to see the built site as Pages will serve it, under the base path, before pushing. Builds the groma ghost `server` (src/server.ts) and the `serve` command.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `site serve [build options] [--port N]` builds, prints the build line and `Serving http://127.0.0.1:<port><base>/ (Ctrl-C to stop)`; port 8000 by default, `0` picks a free one
- [ ] #2 `<base>/` and paths ending in `/` get that folder's `index.html`; other paths under the base get the file
- [ ] #3 Paths outside the base, missing files and paths escaping the output folder get 404
- [ ] #4 A failed build or a taken port exits 1; serve never rebuilds
- [ ] #5 README.md documents the serve command
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
