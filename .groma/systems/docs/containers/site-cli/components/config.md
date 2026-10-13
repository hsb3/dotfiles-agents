---
type: C4 Component
title: Config
description: Loads and validates site.config.json
status: draft
groma:
  id: config
  parent: site-cli
  technology: TypeScript
  draft: v1
---

Reads the config file and checks its shape: `repo` and `ref` required, no unknown keys, the optional `base` (default `/<name>`) is `/` plus one segment of letters, digits, `_` and `-`, and `pages`, `exclude`, `rename`, `nav` and `footer` have the right types. Every problem prints as `<config path>: <problem>`. Derives the site name from the base.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [config](config.md) | [site-config](../../site-config/container.md) | Reads settings | JSON file |
