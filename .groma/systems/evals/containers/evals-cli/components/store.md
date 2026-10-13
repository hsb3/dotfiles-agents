---
type: C4 Component
title: Store
description: PocketBase access, planning and writing for every loader
status: stable
groma:
  id: store
  parent: evals-cli
  technology: TypeScript
  draft: v1
  code:
    - scanner: typescript
      file: src/store.ts
    - scanner: typescript
      file: src/canonical.ts
---

The only PocketBase client of the CLI (the official JS SDK). Reads `PB_URL`, `PB_ADMIN_EMAIL` and `PB_ADMIN_PASSWORD`, authenticates once as superuser (retrying a `429` after 1.5 s, up to 3 times), fetches whole collections or scoped records, applies the json coercion rule, diffs desired records against stored ones by natural key under the idempotence comparison rules, prints the plan block (`[dry-run] plan` or `applied`) and writes in plan order, stopping on the first failure with the collection, natural key and PocketBase message. Also owns canonical JSON: Python-compatible `json.dumps(sort_keys=True)` serialisation with number lexemes kept, and its SHA-256.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [store](store.md) | [pocketbase-service](../../pocketbase-service/container.md) | Reads and writes records as superuser | PocketBase REST, JS SDK |
| [src/store.ts](../../../../../../src/store.ts) | [src/runs.ts](../../../../../../src/runs.ts) | Asks which fields to compare | callback |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/store.ts](../../../../../../src/store.ts) | [src/runs.ts](../../../../../../src/runs.ts) | Invokes supplied callback: skip | typescript |
