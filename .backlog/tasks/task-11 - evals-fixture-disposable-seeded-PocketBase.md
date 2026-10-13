---
id: TASK-11
title: 'evals fixture: disposable seeded PocketBase'
status: To Do
assignee: []
created_date: '2026-10-13 03:09'
labels: []
milestone: m-0
dependencies:
  - TASK-6
  - TASK-10
references:
  - fixture
priority: medium
type: feature
ordinal: 11000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The UI needs a local instance to look at without touching real data or credentials: fixture builds a fresh package, runs it on loopback with a synthetic superuser and user, seeds synthetic records including 27 measured runs, and deletes everything on exit. Builds the fixture component.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 fixture prints the URL, EMAIL and PASSWORD lines and the Ctrl-C notice once the server is healthy and seeded, and exits 1 if the server does not answer /api/health within 10 s
- [ ] #2 The seed matches the spec: source, framework, job, extender with three files, distribution, eval run with a response, assessment, job coverage, 27 runs with measurement v1 (a valid comparison pair at runs 0 and 1, an HTML-like candidate) and one protected artifact linked by events and tool calls of runs 0 and 1
- [ ] #3 On SIGINT or SIGTERM it stops the server, deletes the temporary directory and exits 0; it reads no credentials from the environment
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun run build:ui && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
