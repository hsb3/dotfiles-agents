---
type: C4 Component
title: Layout
description: Wraps a rendered body in the site page document
status: stable
groma:
  id: layout
  parent: site-cli
  technology: TypeScript
  code:
    - scanner: typescript
      file: src/layout.ts
---

Writes the page document the spec fixes: head with the `<H1 text> · <site name>` title and the stylesheet link, skip link, header with brand and repository links, the nav with escaped labels and `aria-current="page"` on the current page, then `main` with the "On this page" contents block, the body and the footer linking the canonical Markdown on GitHub at the build's ref and the config's footer pages. The contents block lists the H1 and H2 headings of the final, link-rewritten body (H2s nested under the H1 before them, links unwrapped, code spans kept) and is left out when the page has no H2. Pages with a Mermaid diagram get the module script that imports Mermaid 11.12.0 from jsDelivr in the reader's browser.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [layout](layout.md) | [jsdelivr-cdn](../../../../../externals/jsdelivr-cdn.md) | References Mermaid 11.12.0 | script URL, never contacted |
| [src/layout.ts](../../../../../../src/layout.ts) | [src/pages.ts](../../../../../../src/pages.ts) | Builds site and GitHub URLs | function call |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/layout.ts](../../../../../../src/layout.ts) | [src/pages.ts](../../../../../../src/pages.ts) | Calls imported functions: githubUrl, siteUrl | typescript |
