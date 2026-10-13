---
type: C4 Component
title: Ingest
description: Projects the checkout and seed data into the catalog collections
status: stable
groma:
  id: ingest
  parent: evals-cli
  technology: TypeScript
  code:
    - scanner: typescript
      file: src/ingest.ts
---

Serves `evals ingest`: builds the whole projection from the checkout and `data/*.json`: frameworks, framework elements, sources, extenders from the roster and externals (an external also in the roster is skipped with a warning), their files, distributions from plugin assemblies, frontmatter dimensions and the `mechanical-v1` assessments of roster skills, agents and hooks; then retires extenders that left the roster and externals. Deletes only `files` rows of a live roster extender whose file left the tree, and never touches other assessors, curation or eval runs.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/ingest.ts](../../../../../../src/ingest.ts) | [src/checkout.ts](../../../../../../src/checkout.ts) | Reads roster and units | function call |
| [src/ingest.ts](../../../../../../src/ingest.ts) | [src/store.ts](../../../../../../src/store.ts) | Plans and writes the projection | function call |
| [ingest](ingest.md) | [seed-data](../../seed-data/container.md) | Reads seeded doctrine | JSON files |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/ingest.ts](../../../../../../src/ingest.ts) | [src/checkout.ts](../../../../../../src/checkout.ts) | Calls imported functions: normaliseSource, readAssembly, readExternals, readMarketplace, readRoster, readUnit | typescript |
| [src/ingest.ts](../../../../../../src/ingest.ts) | [src/store.ts](../../../../../../src/store.ts) | Calls imported functions: ValidationError, applyPlans, connect, diff, emptyPlan, fetchAll, formatParseOnly, formatPlan, formatWarnings | typescript |
