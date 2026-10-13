---
type: C4 Component
title: Commands
description: Parses options and runs build or serve
status: stable
groma:
  id: commands
  parent: site-cli
  technology: TypeScript
  draft: v1
  code:
    - scanner: typescript
      file: src/commands.ts
---

Parses `site build [--root DIR] [--config FILE] [--output DIR] [--ref REF]` and `site serve [build options] [--port N]` (values as the next argument or after `=`), filling in the defaults: the folder that contains the unit as the checkout, the unit's own `site.config.json` (named relative to the working folder in messages), and the unit's `assets/site.css`; the output folder and ref default inside Build from the config. A missing or unknown command or option prints the reason and usage to stderr and exits 1. Runs Build and prints `<N> pages built, links verified: <output>`, or each problem and `build: <K> problems; nothing written` with exit 1; for `serve` it then starts Server on port 8000 by default.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/commands.ts](../../../../../../src/commands.ts) | [src/build.ts](../../../../../../src/build.ts) | Runs the build | function call |

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [commands](commands.md) | [server](server.md) | Starts the preview | function call |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/commands.ts](../../../../../../src/commands.ts) | [src/build.ts](../../../../../../src/build.ts) | Calls imported function: build | typescript |
