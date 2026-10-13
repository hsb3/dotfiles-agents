---
id: TASK-2
title: CLI dispatcher and PocketBase store
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:09'
updated_date: '2026-10-13 03:21'
labels: []
milestone: m-0
dependencies:
  - TASK-1
references:
  - commands
  - store
modified_files:
  - >-
    .backlog/decisions/decision-2 -
    Plans-assign-client-side-record-ids-and-write-with-bounded-concurrency.md
  - .groma/systems/evals/containers/evals-cli/components/cli.md
  - .groma/systems/evals/containers/evals-cli/components/commands.md
  - .groma/systems/evals/containers/evals-cli/components/store.md
  - src/canonical.ts
  - src/cli.ts
  - src/commands.ts
  - src/store.ts
  - test/canonical.test.ts
  - test/cli.ts
  - test/commands.test.ts
  - test/store.test.ts
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
- [x] #1 `--help` on any command prints its usage and exits 0; no subcommand, an unknown subcommand, an unknown flag or a missing required flag prints usage to stderr and exits 1; `--parse-only` with `--dry-run` is refused
- [x] #2 Missing PB_ADMIN_EMAIL or PB_ADMIN_PASSWORD exits 1 naming the variables, and the password is never printed; authentication happens once per invocation and a 429 is retried after 1.5 s up to 3 times
- [x] #3 The json coercion rule turns the spec examples into the stated stored values, and record comparison follows the idempotence rules (missing/null/"" equal for text, select and relation; numeric numbers; strict booleans; ordered lists; canonical json)
- [x] #4 The plan block prints the dry-run and applied headers, one line per collection in write order with delete and retire extensions, and `no writes made` after a dry run; a failed write exits 1 naming the collection, natural key and PocketBase message
- [x] #5 Canonical serialisation reproduces the Appendix C.1 synthetic canonical form and every C.1 record_sha256 vector
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun run build:ui && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. src/canonical.ts: lexeme-preserving JSON parser (JsonNumber), Python json.dumps(sort_keys, compact, ensure_ascii=False) serialiser with Python float repr, canonical sha256; C.1 vectors as tests.
2. src/store.ts: env connection with one superuser auth and 429 retry, auto-cancellation off, fetchAll, json coercion, per-collection field kinds, record comparison under the idempotence rules, plan computation with client-side ids for creates, plan block formatting, ordered writes with bounded concurrency and named failures.
3. src/commands.ts: argument parser (value, multi-value, boolean flags, positionals, --flag=value), per-command usage and --help, usage errors, --parse-only/--dry-run exclusivity, CommandError/ValidationError reporting as 'evals <command>: <what>'; src/cli.ts calls it.
4. Tests: CLI usage/exit codes via spawned process, coercion and comparison units, plan block, store against a disposable PocketBase (auth, missing env, write failure naming key).
5. Gate, scan, accept commands and store with their planned relations, flows none yet, lint, finish.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Evidence: `bunx tsc --noEmit && bun run build:ui && bun test` passes (28 tests). test/commands.test.ts spawns the CLI: --help on all nine commands exits 0 with usage on stdout; no or unknown subcommand, unknown flag, missing required flag or value, extra positional and --parse-only with --dry-run all exit 1 with `evals <command>: <what>` and usage on stderr. test/store.test.ts: missing PB_ADMIN_EMAIL/PB_ADMIN_PASSWORD named; a stub answering 429 twice is retried after 1.5 s each (3 calls, >= 2.9 s) and a permanent 429 fails without echoing the password; coercion of every spec example, and against PocketBase 0.40.5 the stored values equal coerceJson for all eight examples; comparison rules; diff create/update/unchanged with client ids; plan block for dry-run (with delete/retire extensions and `no writes made`) and applied; a failed write reports `write failed in frameworks for fw-b: ...`. test/canonical.test.ts: C.1 synthetic canonical form and all four record_sha256 vectors match. groma: scan matched commands and store, accepted both, combined the scanned canonical component into store (canonical.ts is its helper), accepted cli -> commands and store -> pocketbase-service; lint clean.
Product calls: the usage text lists each command with a one-line summary; an unimplemented command prints a notice and exits 1 until its task lands. A missing PB_URL defaults to http://127.0.0.1:8090.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added the CLI dispatcher (src/commands.ts: flags, usage, --help, usage errors, error reporting) and the PocketBase store (src/store.ts: one superuser auth with 429 retry, fetchAll, json coercion, idempotent diff with client-side ids, plan block, bounded-concurrency writes with named failures) plus Python-compatible canonical JSON (src/canonical.ts). Verified by spawned-CLI tests, unit tests, the Appendix C.1 vectors and tests against a real PocketBase.
<!-- SECTION:FINAL_SUMMARY:END -->
