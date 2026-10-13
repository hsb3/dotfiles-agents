---
type: C4 Component
title: Links
description: Rewrites and checks every link and image in a page
status: draft
groma:
  id: links
  parent: site-cli
  technology: TypeScript, HTMLRewriter
  draft: v1
---

Visits every `<a href>` and `<img src>` in a page body. Scheme and `//` destinations stay as written; local paths resolve from the page's listed folder (or the checkout root for `/`) and must name a file or folder inside the checkout, else `<page>: broken local link: <destination>`. A page, or a folder whose `README.md` is a page, becomes its site URL; any other file or folder becomes a GitHub blob or tree URL, and an image a raw URL, at the build's ref. Query and fragment are kept, and a fragment on a page link must match an `id` in that page's final HTML, else `<page>: missing heading: <destination>`.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [links](links.md) | [dotfiles-agents-checkout](../../../../../externals/dotfiles-agents-checkout.md) | Checks link targets exist | filesystem |
| [links](links.md) | [github-content-hosts](../../../../../externals/github-content-hosts.md) | Points links at | URL, never contacted |
