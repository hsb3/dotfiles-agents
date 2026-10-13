---
type: C4 Component
title: Commands
description: Parses options and runs build or serve
status: draft
groma:
  id: commands
  parent: site-cli
  technology: TypeScript
  draft: v1
---

Parses `site build [--root DIR] [--config FILE] [--output DIR] [--ref REF]` and `site serve [build options] [--port N]`, filling in the defaults (the checkout that contains the unit, the unit's own `site.config.json`, `/tmp/<name>-site/<name>`, the config's `ref`, port 8000). Prints usage to stderr and exits 1 for a missing or unknown subcommand or option. Runs Build, prints `<N> pages built, links verified: <output>` or the problem lines and `build: <K> problems; nothing written`, and for `serve` starts Server after a successful build.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [commands](commands.md) | [build](build.md) | Runs the build | function call |
| [commands](commands.md) | [server](server.md) | Starts the preview | function call |
