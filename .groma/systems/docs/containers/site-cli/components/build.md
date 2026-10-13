---
type: C4 Component
title: Build
description: Runs a whole build and writes the site only when it is clean
status: draft
groma:
  id: build
  parent: site-cli
  technology: TypeScript
  draft: v1
---

Loads the config, selects the pages, renders each, wraps it in the layout and rewrites and checks its links, collecting every problem sorted by page and order within the page. Refuses an output folder that is the checkout or inside it (after resolving symlinks). Only when there are no problems does it write each page and copy the stylesheet into the output folder, overwriting files of the same name and leaving others alone. The same inputs give byte-identical output.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [build](build.md) | [config](config.md) | Loads the config | function call |
| [build](build.md) | [pages](pages.md) | Selects the pages | function call |
| [build](build.md) | [render](render.md) | Renders each page | function call |
| [build](build.md) | [layout](layout.md) | Wraps each page | function call |
| [build](build.md) | [links](links.md) | Rewrites and checks links | function call |
| [build](build.md) | [stylesheet](../../stylesheet/container.md) | Copies the stylesheet | file |
| [build](build.md) | [site-output](../../site-output/container.md) | Writes the site | files |
