---
type: C4 Component
title: Render
description: Renders one page's Markdown to its HTML body
status: draft
groma:
  id: render
  parent: site-cli
  technology: TypeScript, Bun.markdown (md4c), github-slugger
  draft: v1
---

Strips YAML frontmatter (failing the page on invalid YAML or a non-mapping), inserts an H1 from the frontmatter `title` or the file name when the page has none, and renders GFM with raw HTML passed through. Mermaid fences become `<pre class="mermaid">` with only the escaped source, other code blocks `<pre><code class="language-…">`, and every `<pre>` and `<table>` gets `tabindex="0"`. Every heading gets the ID GitHub gives it (github-slugger over its rendered text, with `-1`, `-2` suffixes). Returns the body, the title text, the H1 and H2 entries for the contents block, and whether the page has a diagram.
