---
id: TASK-1
title: 'PocketBase schema migrations, access rules and test server'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:09'
updated_date: '2026-10-13 03:15'
labels: []
milestone: m-0
dependencies: []
references:
  - pocketbase-service
  - pocketbase-database
modified_files:
  - >-
    .backlog/decisions/decision-1 -
    One-idempotent-schema-migration-that-upgrades-in-place.md
  - pb_migrations/1767225600_evals_v1_schema.js
  - test/appendix-a.ts
  - test/migrations.test.ts
  - test/pb.ts
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
- [x] #1 On an empty database the migrations create all 17 collections (16 base plus the coverage_gaps view) with exactly the fields, options, select values, relations, cascades and unique indexes of Appendix A, in dependency order
- [x] #2 On a legacy database built through the REST API from Appendix A without the three additions, with one record in every collection, the migrations keep every record, field id and option and add only runs.harness codex, run_events.vendor codex, extenders.assumes, the rules and the settings
- [x] #3 Re-running the migrations on a migrated database changes nothing; down migrations do nothing
- [x] #4 Access rules match the spec table: anonymous list is 200 with no items and anonymous view 404 on readable collections, a user create/update/delete is 403, a user lists only itself in users and gets 404 viewing another, frontmatter_dimensions, relationships and coverage_gaps are superuser-only; artifacts.blob is protected; rate limiting is enabled with its rules unchanged
- [x] #5 Tests start a disposable server on a free loopback port with a temporary data directory and this repository migrations and hooks, and report as skipped when no binary exists
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun run build:ui && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. test/pb.ts: find the PocketBase binary (existing PB_BINARY, else PATH), free loopback port, temp data dir, superuser upsert, serve with this repo's pb_migrations and pb_hooks, wait for /api/health, restart with other migrations, stop and clean up; tests skip when no binary.
2. test/appendix-a.ts: parse Appendix A from SPEC.md (fields, options, indexes, view query) and derive the legacy variant without the three additions plus REST create bodies.
3. pb_migrations/1767225600_evals_v1_schema.js: create missing collections in dependency order, upgrade existing ones in place (add missing fields after their spec predecessor, append select values, add missing indexes), set access rules, users rules and rateLimits.enabled, saving only what differs; down does nothing.
4. test/migrations.test.ts: empty DB vs Appendix A; re-run under a new name changes nothing; legacy DB through REST with a record per collection then upgrade keeps records, field ids and options; access-rule behaviour and protected blob.
5. Decision record, gate, groma scan/lint, finish.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Evidence: `bunx tsc --noEmit && bun run build:ui && bun test` passes (7 tests, 2085 expect calls, test/migrations.test.ts: empty-database schema and rules vs Appendix A parsed from SPEC.md, rate limits enabled with default rules; re-running the migration under a new name leaves collections and settings byte-identical including `updated`; legacy database built via REST from Appendix A minus additions, one record per collection, upgraded in place with every record, collection id, field id and option kept and only assumes/codex/rules/settings added; anonymous list 200 empty, anonymous view 404, user create/update/delete 403, superuser-only collections 403 to a user, users list only self, other user 404, protected blob refused without token and served with a file token). `PB_BINARY=/nope bun test` reports every PocketBase test as skipped. `groma scan`: created 0; `groma lint`: no findings (21 task references across 11 tasks). No TypeScript component built: the migrations are JavaScript, which the configured scanners do not read, so the map change is none beyond the declared pocketbase-service and pocketbase-database containers this task references.
Product calls: superuser-only collections answer a user list with 403 (PocketBase behaviour for a null rule); the spec states only the readable ones. The users collection updateRule is null too (no self-service profile edits; the UI never writes).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added the v1 PocketBase schema as one idempotent JavaScript migration (17 collections in dependency order, in-place upgrade of a legacy REST-built database keeping field ids and options, access rules, users rules, rate limiting on, no-op down) and a disposable-PocketBase test harness. Verified against a real PocketBase 0.40.5: empty build vs Appendix A parsed from SPEC.md, legacy upgrade with a record per collection, no-op re-run, and the observable access rules including token-gated blobs.
<!-- SECTION:FINAL_SUMMARY:END -->
