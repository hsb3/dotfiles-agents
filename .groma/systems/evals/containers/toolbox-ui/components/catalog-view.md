---
type: C4 Component
title: Catalog View
description: Packaged catalog search beside database extenders and distributions
status: stable
groma:
  id: catalog-view
  parent: toolbox-ui
  technology: React, Carbon
  draft: v1
  code:
    - scanner: react
      file: ui/src/catalog-view.tsx
    - scanner: typescript
      file: ui/src/catalog-view.tsx
---

The Catalog area: reads `GET /api/toolbox/catalog`, shows its source snapshot, and filters its workflows and plugins by a case-insensitive search over id, name, slug, description or guidance, workflows first, 10 per page; beside them the database extenders (the same search, each linking to its documentation) and the explicit distribution membership with member counts. A new search resets all three pagers.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [ui/src/catalog-view.tsx](../../../../../../ui/src/catalog-view.tsx) | [ui/src/api.tsx](../../../../../../ui/src/api.tsx) | Reads catalog and extenders | function call |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [ui/src/catalog-view.tsx](../../../../../../ui/src/catalog-view.tsx) | [ui/src/api.tsx](../../../../../../ui/src/api.tsx) | Calls imported functions: pageCount, pageSlice, useLoad, useSearch; Renders imported components: DataRegion, ExtenderList, PagedList, Pager, SearchForm | typescript |
