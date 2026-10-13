---
id: TASK-11
title: 'evals fixture: disposable seeded PocketBase'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:09'
updated_date: '2026-10-13 05:22'
labels: []
milestone: m-0
dependencies:
  - TASK-6
  - TASK-10
references:
  - fixture
  - run-the-local-fixture
modified_files:
  - .groma/flows/run-the-local-fixture.md
  - .groma/systems/evals/containers/evals-cli/components/commands.md
  - .groma/systems/evals/containers/evals-cli/components/fixture.md
  - SOP-FEEDBACK.md
  - src/commands.ts
  - src/fixture.ts
  - src/synthetic-tree.ts
  - test/evaluations.test.ts
  - test/fixture.test.ts
  - test/ingest.test.ts
  - test/packager.test.ts
  - test/pb.ts
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
- [x] #1 fixture prints the URL, EMAIL and PASSWORD lines and the Ctrl-C notice once the server is healthy and seeded, and exits 1 if the server does not answer /api/health within 10 s
- [x] #2 The seed matches the spec: source, framework, job, extender with three files, distribution, eval run with a response, assessment, job coverage, 27 runs with measurement v1 (a valid comparison pair at runs 0 and 1, an HTML-like candidate) and one protected artifact linked by events and tool calls of runs 0 and 1
- [x] #3 On SIGINT or SIGTERM it stops the server, deletes the temporary directory and exits 0; it reads no credentials from the environment
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun run build:ui && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Move the synthetic source tree from test/ into src/synthetic-tree.ts (git mv) so fixture can default to it; point the tests at it.
2. src/fixture.ts: binary resolution, fresh package in a new temp dir, start.sh on a free loopback port with the fixture superuser and CORS origin, 10 s health wait, verified user, seed (catalog records, eval run, assessment, coverage, 27 runs through the load-runs run builder, protected artifact linked from events and tool calls of runs 0 and 1), printed lines, SIGINT/SIGTERM cleanup.
3. Wire the fixture command.
4. Tests: fixture ledger rules; end-to-end fixture run with seed checks, token-gated artifact, catalog route, SIGINT cleanup; health timeout and missing binary exit 1 leaving nothing behind.
5. Gate, scan, accept fixture (combine synthetic-tree into it) and its relations, lint, finish.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Evidence: gate `bunx tsc --noEmit && bun run build:ui && bun test` exit 0 (188 pass, 0 fail, 72.9 s). test/fixture.test.ts: the fixture ledger builds 27 runs with measurement v1, runs 0/1 share campaign/candidate/case/harness/model/trial as baseline (passed false) and with (passed true), both execution-valid; runs 2-26 are campaign toolbox-fixture across claude/opencode/codex with the `fixture-<img src=x onerror=alert(1)>` candidate. End to end with PocketBase 0.40.5 and ui/dist: `evals fixture --pocketbase <bin>` prints exactly URL=http://127.0.0.1:<port>, EMAIL, PASSWORD and the Ctrl-C line; the fixture user signs in and reads 27 runs (2 in ui-fixture-campaign), the extender, 3 files, the plugin distribution, the running eval run with its response, the present/score-1 assessment, the covered job coverage, 2 events and 2 tool calls; the artifact is tool_output text/plain, refused without a file token and served (`fixture protected evidence\n`) with one; the catalog route is 401 anonymous and 200 for the user; pb_public serves /; SIGINT exits 0, removes the temp directory and the server stops answering. A fake binary that never serves exits 1 within the 10 s health wait leaving no temp directory, and a missing --pocketbase exits 1. Moved the synthetic checkout from test/ to src/synthetic-tree.ts (git mv) as the fixture default source; tests import it from src. Also fixed a test-harness hang seen in one full-suite run: test/pb.ts piped PocketBase stderr without reading it, so a busy server could block on a full pipe; stderr is now ignored and every health probe has a 1 s timeout (same for the start.sh test). groma: accepted fixture and combined the scanned synthetic-tree into it; accepted commands -> fixture, fixture -> packager, fixture -> runs, fixture -> local-pocketbase-binary; fixture -> store authored by file pair (accept refused because both components own two files) and its draft row removed; authored fixture -> pocketbase-service for the health probe (cleared the unmatched request); flow run-the-local-fixture; scan created 0, lint clean.
Product calls: the fixture reads PB_BINARY (a binary path, not a credential) when --pocketbase is absent; it creates the package under its own temp dir and runs start.sh with cwd at the package; if the server exits on its own while running, the fixture cleans up and exits 1; seeded fixture records carry extra synthetic descriptive text (names, method, criteria) so the UI has something to show; run events and tool calls of runs 0 and 1 carry an `$artifact` marker payload pointing at the protected artifact.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Built `evals fixture` (src/fixture.ts with the synthetic checkout in src/synthetic-tree.ts): fresh package from the synthetic tree, start.sh with the local PocketBase on loopback, 10 s health wait, verified synthetic user, the specified synthetic seed including 27 measured runs and a protected artifact, printed credentials, and full cleanup on SIGINT/SIGTERM. Verified end to end against a real PocketBase, plus failure paths; fixed a test-harness stderr-pipe hang.
<!-- SECTION:FINAL_SUMMARY:END -->
