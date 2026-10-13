---
type: C4 Component
title: Render
description: Renders one page's Markdown to its HTML body
status: stable
groma:
  id: render
  parent: site-cli
  technology: TypeScript, Bun.markdown (md4c), github-slugger
  draft: v1
  code:
    - scanner: typescript
      file: src/render.ts
---

Strips YAML frontmatter that starts on the first line (failing the page with `<page>: bad frontmatter: <reason>` on invalid YAML or a non-mapping), inserts an escaped H1 from the frontmatter `title` or the file name when the page has none, and renders GFM (tables, strikethrough, task lists, autolinks) with raw HTML passed through unfiltered. Mermaid fences become `<pre class="mermaid">` with only the escaped source, other code blocks `<pre><code class="language-…">`, and every `<pre>` and `<table>` gets `tabindex="0"`. Every heading gets the ID GitHub gives it: github-slugger over its decoded text content, with `-1`, `-2` suffixes; a raw HTML heading that already has an `id` keeps it. Returns the body, the first H1's text for the page title, every `id` in the body for fragment checks, and whether the page has a diagram. Also decodes HTML entities for Links.
