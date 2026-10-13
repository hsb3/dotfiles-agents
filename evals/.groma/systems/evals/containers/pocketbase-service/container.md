---
type: C4 Container
title: PocketBase service
description: The PocketBase server with this repository's migrations, catalog hook and packaged catalog
status: stable
groma:
  id: pocketbase-service
  parent: evals
  technology: PocketBase 0.40.3, JS migrations and hooks
---

Runs from the deploy package (`start.sh`): applies the JavaScript migrations in `pb_migrations/` at start (schema of 17 collections, access rules, rate limiting), serves the REST API, the `GET /api/toolbox/catalog` route from `pb_hooks/`, token-gated artifact downloads and the Toolbox UI from `pb_public`.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [pocketbase-service](container.md) | [pocketbase-database](../pocketbase-database/container.md) | Stores records and blobs | SQLite, file storage |
