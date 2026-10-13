---
type: C4 Component
title: Evaluations
description: Loads evaluation provenance, verdicts and curation
status: draft
groma:
  id: evaluations
  parent: evals-cli
  technology: TypeScript
  draft: v1
---

Serves `load-eval-run` (eval runs and responses with their `measurement` and canonical response hash, optionally stamping `eval_run` on one assessor), `load-verdicts` (assessments of any assessor but `mechanical-v1`, with `fill`, `--extenders` and `--complete` guards), `load-curation` (job coverage and relationships, scoped to the rows the file lists) and the offline `compare-verdicts` agreement report.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [evaluations](evaluations.md) | [store](store.md) | Plans and writes evaluations | function call |
