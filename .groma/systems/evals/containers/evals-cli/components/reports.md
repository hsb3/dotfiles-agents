---
type: C4 Component
title: Reports
description: Renders coverage-matrix.md and analysis.md
status: draft
groma:
  id: reports
  parent: evals-cli
  technology: TypeScript
  draft: v1
---

Serves `evals report`: reads frameworks, elements, extenders, sources, job coverage, relationships, assessments and eval runs from the database or from JSON dumps (`--fixtures`), excludes retired extenders and the rows that reference them, and writes the jobs-to-be-done coverage matrix and the analysis (extender profiles, relationships needing a resolution, assessor comparison, eval-run provenance index) deterministically.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [reports](reports.md) | [store](store.md) | Fetches collections | function call |
| [reports](reports.md) | [report-directory](../../report-directory/container.md) | Writes the reports | Markdown files |
