---
id: TASK-2
title: CLI dispatcher and PocketBase store
status: To Do
assignee: []
created_date: '2026-10-13 03:09'
labels: []
milestone: m-0
dependencies:
  - TASK-1
references:
  - commands
  - store
priority: high
type: feature
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Every subcommand shares the same rules (usage and errors, phases, idempotent diffing, the plan block, one superuser authentication with 429 retry, json coercion), so they live in one dispatcher and one store before any loader is written. Canonical Python-compatible JSON (record_sha256) is shared by load-runs and load-eval-run. Builds the commands and store components.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `--help` on any command prints its usage and exits 0; no subcommand, an unknown subcommand, an unknown flag or a missing required flag prints usage to stderr and exits 1; `--parse-only` with `--dry-run` is refused
- [ ] #2 Missing PB_ADMIN_EMAIL or PB_ADMIN_PASSWORD exits 1 naming the variables, and the password is never printed; authentication happens once per invocation and a 429 is retried after 1.5 s up to 3 times
- [ ] #3 The json coercion rule turns the spec examples into the stated stored values, and record comparison follows the idempotence rules (missing/null/"" equal for text, select and relation; numeric numbers; strict booleans; ordered lists; canonical json)
- [ ] #4 The plan block prints the dry-run and applied headers, one line per collection in write order with delete and retire extensions, and `no writes made` after a dry run; a failed write exits 1 naming the collection, natural key and PocketBase message
- [ ] #5 Canonical serialisation reproduces the Appendix C.1 synthetic canonical form and every C.1 record_sha256 vector
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun run build:ui && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
