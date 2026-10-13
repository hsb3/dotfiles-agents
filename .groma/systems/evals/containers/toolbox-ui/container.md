---
type: C4 Container
title: Toolbox UI
description: Read-only single-page app for authenticated readers
status: draft
groma:
  id: toolbox-ui
  parent: evals
  technology: React 19, Carbon, Vite
  draft: v1
---

Built from `ui/` with Vite into `ui/dist` and served by the PocketBase service from `pb_public` on the same origin as the API. Readers sign in against the `users` collection and browse Home, Catalog, Documentation, Performance and Evaluations through hash routes; it only reads, keeps the token in memory, renders record text as text and links only safe URLs.
