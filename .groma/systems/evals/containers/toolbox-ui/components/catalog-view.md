---
type: C4 Component
title: Catalog View
description: Packaged catalog search beside database extenders and distributions
status: draft
groma:
  id: catalog-view
  parent: toolbox-ui
  technology: React, Carbon
  draft: v1
---

The Catalog area: reads `GET /api/toolbox/catalog` and filters its workflows and plugins by a case-insensitive search, 10 per page, beside the database extenders (linking to their documentation) and the explicit distribution membership; a new search resets all three pagers.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [catalog-view](catalog-view.md) | [api](api.md) | Reads catalog and extenders | function call |
