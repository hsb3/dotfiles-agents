---
type: C4 Component
title: Layout
description: Wraps a rendered body in the site page document
status: draft
groma:
  id: layout
  parent: site-cli
  technology: TypeScript
  draft: v1
---

Writes the page document the spec fixes: head with the `<H1 text> · <site name>` title and the stylesheet link, skip link, header with brand and repository links, the nav with `aria-current="page"` on the current page, the "On this page" contents block when the page has an H2, the body, and the footer linking the canonical Markdown on GitHub and the config's footer pages. Pages with a Mermaid diagram get the module script that imports Mermaid 11.12.0 from jsDelivr.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [layout](layout.md) | [jsdelivr-cdn](../../../../../externals/jsdelivr-cdn.md) | Imports Mermaid from | script URL, never contacted |
