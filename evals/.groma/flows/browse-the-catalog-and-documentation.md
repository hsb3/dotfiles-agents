---
type: Groma Flow
title: Browse the catalog and documentation
groma:
  id: browse-the-catalog-and-documentation
---

A Toolbox reader signs in, searches the packaged catalog and the database extenders, and opens one extender's stored documentation. Every read carries the in-memory user token; a 401, the token expiry or "Log out" returns to sign-in.

## Steps

| From | To | Action |
| --- | --- | --- |
| [Toolbox reader](../actors/toolbox-reader.md) | [Toolbox UI](../systems/evals/containers/toolbox-ui/container.md) | Open Toolbox, possibly on a deep link such as `#documentation?extender=<id>` |
| [UI entry](../systems/evals/containers/toolbox-ui/components/main.md) | [App](../systems/evals/containers/toolbox-ui/components/app.md) | Mount the shell, which shows sign-in until a session exists |
| [App](../systems/evals/containers/toolbox-ui/components/app.md) | [Api](../systems/evals/containers/toolbox-ui/components/api.md) | Sign in against `users`; the token stays in memory |
| [App](../systems/evals/containers/toolbox-ui/components/app.md) | [Catalog View](../systems/evals/containers/toolbox-ui/components/catalog-view.md) | Show the Catalog area |
| [Catalog View](../systems/evals/containers/toolbox-ui/components/catalog-view.md) | [Api](../systems/evals/containers/toolbox-ui/components/api.md) | Read the packaged catalog, the extender search and the distributions |
| [Api](../systems/evals/containers/toolbox-ui/components/api.md) | [PocketBase service](../systems/evals/containers/pocketbase-service/container.md) | Read the catalog route and the collections with the user token |
| [App](../systems/evals/containers/toolbox-ui/components/app.md) | [Documentation View](../systems/evals/containers/toolbox-ui/components/documentation-view.md) | Follow an extender link to its documentation |
| [Documentation View](../systems/evals/containers/toolbox-ui/components/documentation-view.md) | [Api](../systems/evals/containers/toolbox-ui/components/api.md) | Read the extender, its source and its reader files |
