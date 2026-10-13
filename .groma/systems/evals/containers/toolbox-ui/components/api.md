---
type: C4 Component
title: Api
description: Reads records for every view and holds the session
status: draft
groma:
  id: api
  parent: toolbox-ui
  technology: TypeScript, PocketBase JS SDK, React
  draft: v1
---

The UI side of PocketBase: one SDK client whose token lives in memory only, sign-in against `users` with its failure messages, session end on "Log out", JWT expiry or any 401 (cancelling requests in flight), paged list reads of named fields with `id` as the last sort key and filters built with escaped parameters, cancellation of superseded requests, and the data region that shows exactly one of loading, access, error, empty or the records. Also decides when a URL from the data is safe to link.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [api](api.md) | [pocketbase-service](../../pocketbase-service/container.md) | Reads records with a user token | PocketBase REST, JS SDK |
