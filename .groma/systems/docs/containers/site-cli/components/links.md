---
type: C4 Component
title: Links
description: Rewrites and checks every link and image in a page
status: stable
groma:
  id: links
  parent: site-cli
  technology: TypeScript, HTMLRewriter
  draft: v1
  code:
    - scanner: typescript
      file: src/links.ts
---

Visits every `<a href>` and `<img src>` in a page body, from Markdown or raw HTML, in document order. Scheme and `//` destinations stay as written; a fragment-only destination stays and an empty or query-only one becomes the page's own URL. Other paths are percent-decoded and resolve from the page's listed folder (or the checkout root for `/`); they must name a file or folder inside the checkout after resolving symlinks, else `<page>: broken local link: <destination>`. A page, or a folder whose `README.md` is a page, becomes its site URL; any other file becomes a GitHub blob URL, a folder a tree URL and an image a raw URL, at the build's ref, using the URL scheme Pages owns. Query and fragment are kept as written, and a fragment on a page link must match an `id` in that page's final HTML, else `<page>: missing heading: <destination>`.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [links](links.md) | [dotfiles-agents-checkout](../../../../../externals/dotfiles-agents-checkout.md) | Checks link targets exist | filesystem |
| [links](links.md) | [github-content-hosts](../../../../../externals/github-content-hosts.md) | Points links at | URL, never contacted |
| [src/links.ts](../../../../../../src/links.ts) | [src/pages.ts](../../../../../../src/pages.ts) | Builds GitHub URLs | function call |
| [src/links.ts](../../../../../../src/links.ts) | [src/render.ts](../../../../../../src/render.ts) | Decodes HTML entities | function call |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/links.ts](../../../../../../src/links.ts) | [src/pages.ts](../../../../../../src/pages.ts) | Calls imported function: githubUrl | typescript |
| [src/links.ts](../../../../../../src/links.ts) | [src/render.ts](../../../../../../src/render.ts) | Calls imported function: decodeEntities | typescript |
