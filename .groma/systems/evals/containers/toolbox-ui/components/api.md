---
type: C4 Component
title: Api
description: Reads records for every view and holds the session
status: stable
groma:
  id: api
  parent: toolbox-ui
  technology: TypeScript, PocketBase JS SDK, React
  draft: v1
  code:
    - scanner: react
      file: ui/src/api.tsx
    - scanner: typescript
      file: ui/src/api.tsx
---

The UI side of PocketBase and the pieces every area shares. One SDK client on the page origin whose token lives in an in-memory auth store only; sign-in against `users` with its failure messages; session end on "Log out", JWT expiry (a timer, and a check before each request) or any 401 answer, cancelling every request in flight; paged list reads of named fields with `id` as the last sort key and filters built only from escaped SDK filter parameters; cancellation of superseded reads, whose answers are ignored. It renders the data region that shows exactly one of loading, access, error, empty or the records, the pager, the search form, the single-record and paged-list regions, and the "Database extenders" search list that Catalog and Documentation both show. It also decides when a URL from the data is safe to link and builds the hash links between areas.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [api](api.md) | [pocketbase-service](../../pocketbase-service/container.md) | Reads records with a user token | PocketBase REST, JS SDK |
| [ui/src/api.tsx](../../../../../../ui/src/api.tsx) | [ui/src/catalog-view.tsx](../../../../../../ui/src/catalog-view.tsx) | Calls back the list query, item renderer and emptiness test the view supplies | React props |
| [ui/src/api.tsx](../../../../../../ui/src/api.tsx) | [ui/src/documentation-view.tsx](../../../../../../ui/src/documentation-view.tsx) | Calls back the list query and item renderer the view supplies | React props |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [ui/src/api.tsx](../../../../../../ui/src/api.tsx) | [ui/src/catalog-view.tsx](../../../../../../ui/src/catalog-view.tsx) | Invokes supplied callbacks: isEmpty, item, query | react |
| [ui/src/api.tsx](../../../../../../ui/src/api.tsx) | [ui/src/documentation-view.tsx](../../../../../../ui/src/documentation-view.tsx) | Invokes supplied callbacks: item, query | react |
