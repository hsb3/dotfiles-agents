---
type: C4 Component
title: App
description: 'The Toolbox shell: sign-in, navigation and routing'
status: stable
groma:
  id: app
  parent: toolbox-ui
  technology: React, Carbon
  code:
    - scanner: react
      file: ui/src/app.tsx
    - scanner: typescript
      file: ui/src/app.tsx
---

Shows sign-in until a session exists, then the shell: header "Toolbox" with caption and "Log out", side navigation (collapsible below 66rem), skip-to-content link, breadcrumb, and the hash routes #home, #catalog, #documentation, #performance, #evaluations with parameters after ?, each area view receiving the route parameters. A deep link survives sign-in, the main region takes focus on each route change, and Home shows a card per area. Ending the session unmounts the shell, which clears the loaded records and the Performance selection.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [ui/src/app.tsx](../../../../../../ui/src/app.tsx) | [ui/src/api.tsx](../../../../../../ui/src/api.tsx) | Signs in and out | function call |
| [ui/src/app.tsx](../../../../../../ui/src/app.tsx) | [ui/src/catalog-view.tsx](../../../../../../ui/src/catalog-view.tsx) | Shows the catalog | React render |
| [ui/src/app.tsx](../../../../../../ui/src/app.tsx) | [ui/src/documentation-view.tsx](../../../../../../ui/src/documentation-view.tsx) | Shows documentation | React render |
| [ui/src/app.tsx](../../../../../../ui/src/app.tsx) | [ui/src/evaluations-view.tsx](../../../../../../ui/src/evaluations-view.tsx) | Shows evaluations | React render |
| [ui/src/app.tsx](../../../../../../ui/src/app.tsx) | [ui/src/performance-view.tsx](../../../../../../ui/src/performance-view.tsx) | Shows performance | React render |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [ui/src/app.tsx](../../../../../../ui/src/app.tsx) | [ui/src/api.tsx](../../../../../../ui/src/api.tsx) | Calls imported functions: ToolboxClient, hashHref, useClient; Renders imported component: ClientProvider | typescript |
| [ui/src/app.tsx](../../../../../../ui/src/app.tsx) | [ui/src/catalog-view.tsx](../../../../../../ui/src/catalog-view.tsx) | Renders imported component: CatalogView | typescript |
| [ui/src/app.tsx](../../../../../../ui/src/app.tsx) | [ui/src/documentation-view.tsx](../../../../../../ui/src/documentation-view.tsx) | Renders imported component: DocumentationView | typescript |
| [ui/src/app.tsx](../../../../../../ui/src/app.tsx) | [ui/src/evaluations-view.tsx](../../../../../../ui/src/evaluations-view.tsx) | Renders imported component: EvaluationsView | typescript |
| [ui/src/app.tsx](../../../../../../ui/src/app.tsx) | [ui/src/performance-view.tsx](../../../../../../ui/src/performance-view.tsx) | Renders imported component: PerformanceView | typescript |
