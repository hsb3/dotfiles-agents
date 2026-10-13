---
type: C4 Component
title: Ingest
description: Projects the checkout and seed data into the catalog collections
status: draft
groma:
  id: ingest
  parent: evals-cli
  technology: TypeScript
  draft: v1
---

Serves `evals ingest`: builds the whole projection from the checkout and `data/*.json`: frameworks, framework elements, sources, extenders from the roster and externals, their files, distributions from plugin assemblies, frontmatter dimensions and the `mechanical-v1` assessments of skills, agents and hooks; then retires extenders that left the roster and externals. Deletes only `files` rows whose file left the tree.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [ingest](ingest.md) | [checkout](checkout.md) | Reads roster and units | function call |
| [ingest](ingest.md) | [seed-data](../../seed-data/container.md) | Reads seeded doctrine | JSON files |
| [ingest](ingest.md) | [store](store.md) | Plans and writes the projection | function call |
