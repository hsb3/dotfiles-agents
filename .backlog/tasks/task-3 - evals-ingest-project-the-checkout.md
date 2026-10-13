---
id: TASK-3
title: 'evals ingest: project the checkout'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:09'
updated_date: '2026-10-13 03:29'
labels: []
milestone: m-0
dependencies:
  - TASK-2
references:
  - checkout
  - ingest
  - project-the-catalog
modified_files:
  - .groma/flows/project-the-catalog.md
  - .groma/index.md
  - .groma/systems/evals/containers/evals-cli/components/checkout.md
  - .groma/systems/evals/containers/evals-cli/components/commands.md
  - .groma/systems/evals/containers/evals-cli/components/ingest.md
  - src/checkout.ts
  - src/commands.ts
  - src/ingest.ts
  - test/ingest.test.ts
  - test/pb.ts
  - test/synthetic-tree.ts
priority: high
type: feature
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The extender inventory, the seeded doctrine and the mechanical-v1 assessments are what every report and the UI read. ingest projects a dotfiles-agents checkout and data/*.json into frameworks, framework_elements, sources, extenders, files, distributions, frontmatter_dimensions and assessments, then retires vanished extenders. Builds the checkout and ingest components; tests use a synthetic source tree with every case SPEC.md lists.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A synthetic tree with every listed case (each roster type, references/ and scripts/, block-sequence tools, folded description, hook with hook.py, config.json and .sh, an id in roster and externals, standalone and bundle plugins with hooks/_lib, commands/ and .mcp.json links) is projected exactly as The projection section states, including file roles, languages, distributions kind and members, frontmatter dimensions and mechanical verdicts and evidence
- [x] #2 A second ingest of the unchanged tree plans 0 create / 0 update in every collection; a removed roster entry is listed as retired and comes back un-retired when it returns; a file that left the tree is deleted from files
- [x] #3 `--parse-only` prints planned record counts and warnings without connecting; `--dry-run` writes nothing and prints `to retire` lines; missing roster, externals or marketplace exits 1
- [x] #4 Nothing is written under --source-root; ingest never writes other assessors, job_coverage, relationships, eval_runs or eval_responses
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun run build:ui && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. src/checkout.ts: roster and externals (Bun.YAML, scalar-as-list, validation), frontmatter split, unit reading per type (entry file, files walk with skip rules, symlink handling, UTF-8/binary, sha256, language, role), marketplace manifest, plugin assemblies (symlinks per folder, .mcp.json target).
2. src/ingest.ts: seed data, extenders from roster and externals (source by upstream prefix), files with deletes, distributions (members order, standalone/bundle), frontmatter dimensions, mechanical-v1 assessments, retire; parse-only counts, dry-run plan with to-retire lines, applied output and warnings.
3. Wire ingest into commands.
4. test/synthetic-tree.ts with every case the spec lists; tests for checkout units and an end-to-end ingest against PocketBase (exact projection, idempotent re-run, retire/un-retire, file delete, read-only source root, missing inputs).
5. Gate, scan, accept checkout and ingest and their relations, add the project-the-catalog flow, lint, finish.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Evidence: gate `bunx tsc --noEmit && bun run build:ui && bun test` passes (39 tests). test/ingest.test.ts runs the CLI against PocketBase 0.40.5 on test/synthetic-tree.ts (every case of the Stack section): dry run plans 9/72/10/9/17/3/12/30 creates and writes nothing; the write projects extenders (roster and external field by field, source by upstream prefix), files (skip rules, symlinked file read through, symlinked dir not descended, binary, sha256, roles, languages), distributions (bundle with _lib/commands/.mcp.json, standalone, missing dir), frontmatter dimensions and every mechanical verdict and evidence string; the source tree snapshot (sizes, mtimes, hashes) is unchanged; a re-run plans 0 create / 0 update everywhere; a coverage-v1 row and a stamped eval_run on a mechanical row survive; a removed roster entry prints `to retire`/`retired command/prepare-compact`, keeps its files, a vanished file is the one delete, and the entry un-retires on return. --parse-only output matched exactly without a server; missing roster/externals/marketplace and invalid roster entries exit 1 naming each problem. Manual timing: 89 extenders and 497 files ingest in 260 ms against a local server (re-run 132 ms). groma: accepted checkout and ingest and their five planned relations, added flow project-the-catalog; scan created 0, lint clean.
Product calls: mechanical-v1 assessments are written for roster extenders only (externals have no files to judge); entry_file is "" when the entry file is missing; a non-string frontmatter name/description is converted to text (JSON for objects); the non-stdlib evidence lists full dotted module names, deduplicated and sorted; warnings print after the plan block and retired lines as `warnings (<n>):` with `  - ` items; a broken symlink in a unit and frontmatter YAML that is not a mapping are skipped with a warning.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Built `evals ingest`: src/checkout.ts reads the roster, externals, unit sources (frontmatter, files, roles, languages), marketplace and plugin assemblies read-only; src/ingest.ts projects seed data, extenders, files, distributions, frontmatter dimensions and mechanical-v1 assessments, deletes vanished files of live extenders and retires vanished extenders, with --parse-only and --dry-run. Verified end to end against PocketBase on a synthetic checkout covering every listed case, including idempotence, retire/un-retire and a read-only source tree.
<!-- SECTION:FINAL_SUMMARY:END -->
