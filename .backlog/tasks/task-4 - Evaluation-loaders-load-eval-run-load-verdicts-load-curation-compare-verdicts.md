---
id: TASK-4
title: >-
  Evaluation loaders: load-eval-run, load-verdicts, load-curation,
  compare-verdicts
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:09'
updated_date: '2026-10-13 03:44'
labels: []
milestone: m-0
dependencies:
  - TASK-3
references:
  - evaluations
  - record-an-evaluation-pass
modified_files:
  - .groma/flows/record-an-evaluation-pass.md
  - .groma/systems/evals/containers/evals-cli/components/commands.md
  - .groma/systems/evals/containers/evals-cli/components/evaluations.md
  - src/commands.ts
  - src/evaluations.ts
  - test/commands.test.ts
  - test/evaluations.test.ts
  - test/ingest.test.ts
  - test/migrations.test.ts
  - test/pb.ts
  - test/store.test.ts
priority: high
type: feature
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Every verdict links back to the run, prompt and response that produced it, so evaluation passes are loaded as eval runs with responses first, then verdict files into assessments and curation files into job_coverage and relationships; compare-verdicts measures agreement between two verdict sets offline. Builds the evaluations component.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 load-eval-run writes eval_runs and eval_responses with the measurement envelope (manifest sha256, canonical resolved_response_sha256, availability and provenance) and with link_assessor stamps eval_run on that assessor assessments; refused extenders, NaN response_json and bad metrics are validation errors
- [x] #2 load-verdicts expands fill rows, refuses mechanical-v1, unknown or retired extenders, foreign elements, duplicates within and across files, and enforces --extenders and --complete
- [x] #3 load-curation writes only the rows the file lists, keyed as the spec states, and refuses duplicate keys and unknown eval runs
- [x] #4 compare-verdicts prints sorted disagreements and `verdict agreement: a/t (p%)`, honours fill, and exits 1 with `no overlapping extenders`
- [x] #5 Each loader supports --parse-only and --dry-run and a re-run plans no writes
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun run build:ui && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. src/evaluations.ts: shared lookups (eval run by id or slug, extenders by slug or name with retired checks, elements by framework), lexeme-preserving JSON file reads, problem collection per file.
2. load-eval-run: manifest shape, inline/file texts, metrics, response measurement with manifest sha and canonical resolved hash, eval_runs and eval_responses diffs, link_assessor stamping.
3. load-verdicts: fill expansion, score only when given, refusals, --extenders and --complete guards; compare-verdicts offline with fill semantics and Python rounding.
4. load-curation: job_coverage and relationships scoped to listed rows.
5. Wire the four commands; tests offline and against PocketBase; gate, scan, accept evaluations and its relations, flow record-an-evaluation-pass, lint, finish.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Evidence: gate `bunx tsc --noEmit && bun run build:ui && bun test` passes (69 tests). test/evaluations.test.ts against PocketBase 0.40.5 after ingesting the synthetic tree: load-eval-run --parse-only counts, write creates the run (criteria_file text, framework ids, default status complete) and responses (file texts, response_json, extender ids, tokens/duration, absent metrics sent as 0 and unavailable) with the measurement compared exactly, including the manifest sha256 and a resolved_response_sha256 recomputed in the test; re-run plans 0/0/1 and 0/0/2; bad metrics, duplicate role and NaN response_json refused in --parse-only, an unknown extender refused before any write; link_assessor coverage-v1 updates all 48 rows and leaves mechanical-v1 alone, then converges. load-verdicts: fill expands to 24 rows per extender (48), score sent only when given, re-run unchanged; refusals for mechanical-v1, unknown eval_run, extender not in DB, foreign element, duplicate extender, duplicate element, the same key from two files, --extenders missing and extra, --complete. load-curation writes 2+2 rows with eval_run and source, a job_coverage row outside the file keeps its `updated`, re-run unchanged, duplicate key and unknown eval run refused. compare-verdicts (offline): exact disagreement lines and `verdict agreement: 1/3 (33%)`, fill on one side, half-to-even rounding (1/8 -> 12%), `no overlapping extenders` and invalid JSON exit 1. Also moved the 60 s test timeout into each slow test file (setDefaultTimeout only applies to the file that calls it), which made the TASK-3 ingest test reliable in the full suite. groma: accepted evaluations with commands -> evaluations and evaluations -> store, added flow record-an-evaluation-pass; scan created 0, lint clean.
Product calls: prompt, agent_type and model default to "" (the resolved hash uses the same defaults); extenders and elements resolve by slug first, then by name; two manifests loading the same run slug, or linking the same assessor, in one invocation are refused; with fill, --parse-only counts rows from data/frameworks.json element counts; --extenders is compared with the raw identifiers under --parse-only and with resolved slugs otherwise; compare-verdicts refuses the same (framework, extender) twice on one side, rounds the percentage half to even as Python round() does, and exits 1 with `no overlapping verdicts` when extenders overlap but no element is comparable; curation relationships resolve extenders like verdict files do.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Built src/evaluations.ts: load-eval-run (eval runs and responses with the manifest measurement and canonical resolved-response hash, link_assessor stamping), load-verdicts (fill expansion, refusals, --extenders/--complete guards), load-curation (job_coverage and relationships scoped to the file) and the offline compare-verdicts, wired into the dispatcher. Verified with offline and PocketBase-backed CLI tests covering every acceptance criterion, idempotent re-runs included.
<!-- SECTION:FINAL_SUMMARY:END -->
