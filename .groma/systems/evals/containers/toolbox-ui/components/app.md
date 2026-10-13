---
type: C4 Component
title: App
description: 'The Toolbox shell: sign-in, navigation and routing'
status: draft
groma:
  id: app
  parent: toolbox-ui
  technology: React, Carbon
  draft: v1
---

Shows sign-in until a session exists, then the shell: header "Toolbox" with caption and "Log out", side navigation (collapsible below 66rem), skip-to-content link, breadcrumb, and the hash routes `#home`, `#catalog`, `#documentation`, `#performance`, `#evaluations` with parameters after `?`. A deep link survives sign-in, the main region takes focus on each route change, and Home shows a card per area.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [app](app.md) | [api](api.md) | Signs in and out | function call |
| [app](app.md) | [catalog-view](catalog-view.md) | Shows the catalog | React render |
| [app](app.md) | [documentation-view](documentation-view.md) | Shows documentation | React render |
| [app](app.md) | [evaluations-view](evaluations-view.md) | Shows evaluations | React render |
| [app](app.md) | [performance-view](performance-view.md) | Shows performance | React render |
