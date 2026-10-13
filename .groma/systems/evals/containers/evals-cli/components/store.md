---
type: C4 Component
title: Store
description: PocketBase access, planning and writing for every loader
status: draft
groma:
  id: store
  parent: evals-cli
  technology: TypeScript
  draft: v1
---

The only PocketBase client of the CLI (the official JS SDK). Reads `PB_URL`, `PB_ADMIN_EMAIL` and `PB_ADMIN_PASSWORD`, authenticates once as superuser (retrying a `429` after 1.5 s, up to 3 times), fetches whole collections or scoped records, applies the json coercion rule, diffs desired records against stored ones by natural key under the idempotence comparison rules, prints the plan block (`[dry-run] plan` or `applied`) and writes in plan order, stopping on the first failure with the collection, natural key and PocketBase message. Also owns canonical JSON: Python-compatible `json.dumps(sort_keys=True)` serialisation with number lexemes kept, and its SHA-256.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [store](store.md) | [pocketbase-service](../../pocketbase-service/container.md) | Reads and writes records as superuser | PocketBase REST, JS SDK |
