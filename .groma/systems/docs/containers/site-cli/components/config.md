---
type: C4 Component
title: Config
description: Loads and validates site.config.json
status: stable
groma:
  id: config
  parent: site-cli
  technology: TypeScript
  draft: v1
  code:
    - scanner: typescript
      file: src/config.ts
---

Reads the config file (the unit's `site.config.json` or `--config`) and checks its shape: `repo` (`<owner>/<name>`) and `ref` required, no unknown keys at the top level or in `nav` and `footer` entries, the optional `base` (default `/<name>`) is `/` plus one segment of letters, digits, `_` and `-`, and `pages`, `exclude`, `rename`, `nav` and `footer` have the right types. It collects every problem, each printed as `<config path>: <problem>`, before failing, and derives the site name from the base. The page-list rules belong to Pages.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [config](config.md) | [site-config](../../site-config/container.md) | Reads settings | JSON file |
