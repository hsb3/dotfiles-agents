---
id: TASK-8
title: 'evals package: deploy directory and catalog route'
status: To Do
assignee: []
created_date: '2026-10-13 03:09'
labels: []
milestone: m-0
dependencies:
  - TASK-2
references:
  - packager
  - pocketbase-service
priority: high
type: feature
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The PocketBase service is deployed to Railway from a package directory the CLI builds deterministically: Dockerfile, start.sh, railway.toml, migrations, the catalog hook serving GET /api/toolbox/catalog, the catalog and its receipt, and the UI build. Builds the packager component and the catalog hook of the PocketBase service.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A package of the same inputs is byte-identical across runs and contains exactly the documented files, with Dockerfile, start.sh (executable) and railway.toml exactly as specified
- [ ] #2 toolbox-catalog.json and toolbox-package.json match the documented shape, sort order and snapshots
- [ ] #3 UI builds and catalog inputs that break any documented rule are refused with an error naming it, an existing --out or one inside --source-root is refused, and nothing is left behind on failure
- [ ] #4 GET /api/toolbox/catalog answers 200 with the catalog for an authenticated user or superuser and 401 anonymously, against a real server
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun run build:ui && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
