---
type: C4 Component
title: Pages
description: Selects the pages and assigns their output paths and site URLs
status: draft
groma:
  id: pages
  parent: site-cli
  technology: TypeScript
  draft: v1
---

Expands the config's `pages` globs against the checkout (`*` within a segment, `**` across segments, wildcards skip dot names, explicit names do not, symlinked files match like any other) and removes `exclude` matches; an entry matching nothing is an error. Each page keeps its listed path, even when it is a symlink, and gets its output path (its `rename` entry or `.md` → `.html`) and its percent-encoded site URL under the base. Checks the page-list rules of the config: `nav`, `footer` and `rename` pages are listed, one page publishes at `index.html`, no two pages share an output path, and no output path has a hidden segment. Reads each page's Markdown source.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [pages](pages.md) | [dotfiles-agents-checkout](../../../../../externals/dotfiles-agents-checkout.md) | Lists and reads Markdown pages | filesystem, Bun.Glob |
