---
type: C4 Component
title: Reports
description: Renders coverage-matrix.md and analysis.md
status: stable
groma:
  id: reports
  parent: evals-cli
  technology: TypeScript
  code:
    - scanner: typescript
      file: src/reports.ts
---

Serves `evals report`: reads frameworks, elements, extenders, sources, job coverage, relationships, assessments and eval runs from the database or from JSON dumps (`--fixtures`), excludes retired extenders and the rows that reference them, and writes the jobs-to-be-done coverage matrix and the analysis (extender profiles, relationships needing a resolution, assessor comparison, eval-run provenance index) deterministically.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/reports.ts](../../../../../../src/reports.ts) | [src/store.ts](../../../../../../src/store.ts) | Fetches collections | function call |
| [reports](reports.md) | [report-directory](../../report-directory/container.md) | Writes the reports | Markdown files |
| [src/reports.ts](../../../../../../src/reports.ts) | [src/canonical.ts](../../../../../../src/canonical.ts) | Orders slugs by code point | function call |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/reports.ts](../../../../../../src/reports.ts) | [src/canonical.ts](../../../../../../src/canonical.ts) | Calls imported function: compareCodePoints | typescript |
| [src/reports.ts](../../../../../../src/reports.ts) | [src/store.ts](../../../../../../src/store.ts) | Calls imported functions: CommandError, connect, fetchAll, textOf | typescript |
