---
type: C4 Actor
title: Maintainer
description: Maintainer or contributor of dotfiles-agents
status: stable
groma:
  id: maintainer
  draft: v1
---

Builds the site locally to check links before pushing, and previews it with `site serve` in a browser at `http://127.0.0.1:8000/dotfiles-agents/`.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [maintainer](maintainer.md) | [site-cli](../systems/docs/containers/site-cli/container.md) | Runs build and serve | shell |
| [maintainer](maintainer.md) | [server](../systems/docs/containers/site-cli/components/server.md) | Previews the site | HTTP, browser |
