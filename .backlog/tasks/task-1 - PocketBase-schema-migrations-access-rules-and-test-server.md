---
id: TASK-1
title: 'PocketBase schema migrations, access rules and test server'
status: To Do
assignee: []
created_date: '2026-10-13 03:09'
labels: []
milestone: m-0
dependencies: []
references:
  - pocketbase-service
  - pocketbase-database
priority: high
type: feature
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The deployed PocketBase 0.40.3 instance holds verdicts and provenance that cannot be regenerated, and every later loader and the UI need the schema of SPEC.md Appendix A with its access rules. Schema, rules and settings must be JavaScript migrations in `pb_migrations/` that the server applies at start, upgrading a database the previous tooling built through the REST API in place. Tests need a disposable loopback PocketBase built from `$PB_BINARY` or `pocketbase` on PATH. Builds the PocketBase service and database containers.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 On an empty database the migrations create all 17 collections (16 base plus the coverage_gaps view) with exactly the fields, options, select values, relations, cascades and unique indexes of Appendix A, in dependency order
- [ ] #2 On a legacy database built through the REST API from Appendix A without the three additions, with one record in every collection, the migrations keep every record, field id and option and add only runs.harness codex, run_events.vendor codex, extenders.assumes, the rules and the settings
- [ ] #3 Re-running the migrations on a migrated database changes nothing; down migrations do nothing
- [ ] #4 Access rules match the spec table: anonymous list is 200 with no items and anonymous view 404 on readable collections, a user create/update/delete is 403, a user lists only itself in users and gets 404 viewing another, frontmatter_dimensions, relationships and coverage_gaps are superuser-only; artifacts.blob is protected; rate limiting is enabled with its rules unchanged
- [ ] #5 Tests start a disposable server on a free loopback port with a temporary data directory and this repository migrations and hooks, and report as skipped when no binary exists
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun run build:ui && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
