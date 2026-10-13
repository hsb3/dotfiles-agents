---
id: TASK-9
title: 'Toolbox UI: shell, sign-in, catalog and documentation'
status: To Do
assignee: []
created_date: '2026-10-13 03:09'
labels: []
milestone: m-0
dependencies:
  - TASK-8
references:
  - toolbox-ui
  - main
  - app
  - api
  - catalog-view
  - documentation-view
priority: high
type: feature
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Authenticated readers need a read-only browser view of the catalog and the stored documentation, served from pb_public. This slice builds the Carbon shell, the in-memory session, the shared data region and safe links, Home, Catalog and Documentation. Builds the app, api, catalog-view and documentation-view components and the toolbox-ui container.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Sign-in keeps the token in memory only, clears the password after each attempt, shows the documented failure messages and ends the session on Log out, JWT expiry or any 401; a deep link survives sign-in
- [ ] #2 The shell has the documented header, caption, side navigation, skip link, breadcrumb, hash routes and Home cards
- [ ] #3 Every data region shows exactly one of loading, access, error, empty or records with the documented texts; lists page 25 per page with named fields and id as the last sort key; filters use escaped parameters; superseded requests are cancelled
- [ ] #4 Catalog and Documentation show the documented records, links and texts; record text renders as text and only safe URLs become links
- [ ] #5 tsc covers ui/src and bun run build:ui produces ui/dist; logic is unit-tested without a browser
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun run build:ui && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
