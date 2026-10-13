---
type: C4 Component
title: Evaluations
description: Loads evaluation provenance, verdicts and curation
status: stable
groma:
  id: evaluations
  parent: evals-cli
  technology: TypeScript
  draft: v1
  code:
    - scanner: typescript
      file: src/evaluations.ts
---

Serves `load-eval-run` (eval runs and responses with their `measurement` and canonical response hash, optionally stamping `eval_run` on one assessor), `load-verdicts` (assessments of any assessor but `mechanical-v1`, with `fill`, `--extenders` and `--complete` guards), `load-curation` (job coverage and relationships, scoped to the rows the file lists) and the offline `compare-verdicts` agreement report.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/evaluations.ts](../../../../../../src/evaluations.ts) | [src/store.ts](../../../../../../src/store.ts) | Plans and writes evaluations | function call |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/evaluations.ts](../../../../../../src/evaluations.ts) | [src/canonical.ts](../../../../../../src/canonical.ts) | Calls imported functions: canonicalSha256, parseJson, plain, sha256Hex | typescript |
| [src/evaluations.ts](../../../../../../src/evaluations.ts) | [src/store.ts](../../../../../../src/store.ts) | Calls imported functions: CommandError, ValidationError, applyPlans, connect, diff, fetchAll, formatParseOnly, formatPlan | typescript |
