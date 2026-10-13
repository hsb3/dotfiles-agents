---
type: C4 Component
title: Pages
description: Selects the pages and assigns their output paths and site URLs
status: stable
groma:
  id: pages
  parent: site-cli
  technology: TypeScript
  code:
    - scanner: typescript
      file: src/pages.ts
---

Expands the config's `pages` entries against the checkout (`*` within a segment, `**` across segments, wildcards skip names starting with `.`, explicit names do not, symlinked files match like any other) and removes `exclude` matches; an entry matching nothing is a config error. Only regular `.md` files are pages. Each page keeps its listed path, even when it is a symlink, and gets its output path (its `rename` entry or `.md` → `.html`) and its site URL under the base, each segment percent-encoded except `A–Z a–z 0–9 - . _ ~`. Checks the page-list rules of the config: `nav`, `footer` and `rename` pages are listed, one page publishes at `index.html`, no two pages share an output path, and no output path has a hidden segment. It reads each page's Markdown source and owns the URL scheme Links and Layout use for site URLs and GitHub blob, tree and raw URLs.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [pages](pages.md) | [dotfiles-agents-checkout](../../../../../externals/dotfiles-agents-checkout.md) | Lists and reads Markdown pages | filesystem |
| [src/pages.ts](../../../../../../src/pages.ts) | [src/config.ts](../../../../../../src/config.ts) | Reports page-list config problems | function call |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/pages.ts](../../../../../../src/pages.ts) | [src/config.ts](../../../../../../src/config.ts) | Calls imported function: ConfigError | typescript |
