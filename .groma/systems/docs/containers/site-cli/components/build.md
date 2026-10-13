---
type: C4 Component
title: Build
description: Runs a whole build and writes the site only when it is clean
status: stable
groma:
  id: build
  parent: site-cli
  technology: TypeScript
  draft: v1
  code:
    - scanner: typescript
      file: src/build.ts
---

Runs one whole build for `site build` and `site serve`: loads the config, refuses an output folder that is the checkout or lies inside it (after resolving symlinks, even when the folder does not exist yet), selects the pages, renders each, rewrites and checks its links against every page's ids, and wraps it in the layout. Problems are collected rather than thrown: config problems first, then each page's in page order and document order within the page. Only when there are none does it write each page into the output folder (default `/tmp/<name>-site/<name>`) and copy the stylesheet byte for byte to `assets/site.css`, overwriting files of the same name and leaving others alone. The same checkout, config and ref give byte-identical output.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/build.ts](../../../../../../src/build.ts) | [src/config.ts](../../../../../../src/config.ts) | Loads the config | function call |
| [src/build.ts](../../../../../../src/build.ts) | [src/pages.ts](../../../../../../src/pages.ts) | Selects the pages | function call |
| [src/build.ts](../../../../../../src/build.ts) | [src/render.ts](../../../../../../src/render.ts) | Renders each page | function call |
| [src/build.ts](../../../../../../src/build.ts) | [src/links.ts](../../../../../../src/links.ts) | Rewrites and checks links | function call |
| [src/build.ts](../../../../../../src/build.ts) | [src/layout.ts](../../../../../../src/layout.ts) | Wraps each page | function call |
| [build](build.md) | [stylesheet](../../stylesheet/container.md) | Copies the stylesheet | file |
| [build](build.md) | [site-output](../../site-output/container.md) | Writes the site | files |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/build.ts](../../../../../../src/build.ts) | [src/config.ts](../../../../../../src/config.ts) | Calls imported function: loadConfig | typescript |
| [src/build.ts](../../../../../../src/build.ts) | [src/layout.ts](../../../../../../src/layout.ts) | Calls imported function: layoutPage | typescript |
| [src/build.ts](../../../../../../src/build.ts) | [src/links.ts](../../../../../../src/links.ts) | Calls imported function: rewriteLinks | typescript |
| [src/build.ts](../../../../../../src/build.ts) | [src/pages.ts](../../../../../../src/pages.ts) | Calls imported functions: readSource, selectPages | typescript |
| [src/build.ts](../../../../../../src/build.ts) | [src/render.ts](../../../../../../src/render.ts) | Calls imported function: renderPage | typescript |
