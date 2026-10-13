---
id: decision-2
title: Post-process md4c HTML with HTMLRewriter for heading IDs
date: '2026-10-13 03:15'
status: accepted
---
## Context

`Bun.markdown.html` (md4c) must render the pages, but its `headings` option gives IDs that differ from GitHub's (`hooks-as-script-config` instead of `hooks-as-script--config`), and the spec wants every heading, levels 1 to 6, to carry GitHub's ID computed by github-slugger from the heading's rendered text (code-span text kept, markup and raw tags dropped). `Bun.markdown.render` callbacks would mean re-implementing the whole HTML renderer to change one element. HTMLRewriter cannot change a start tag once the element's content has been seen, so a heading's text is not known when its `id` must be written.

## Decision

Render with `Bun.markdown.html` (headings off), then run two HTMLRewriter passes over the result: the first collects each `h1`–`h6`'s text chunks (descendants included, so raw tags drop out and their text stays) and every existing `id`; the slugs are computed in document order with one `GithubSlugger` per page after decoding entities; the second pass writes the IDs in the same order and adds `tabindex="0"` to every `<pre>` and `<table>`. Mermaid fences are rewritten from md4c's fixed `<pre><code class="language-mermaid">` output with one regular expression. Raw HTML headings are treated like Markdown ones; one that already has an `id` keeps it.

## Consequences

md4c stays the only Markdown renderer, so GFM behaviour is exactly Bun's. Entity decoding uses a small table (numeric references plus common named entities); an unknown named entity in a raw HTML heading stays as written and its characters are slugged as text. Links reuse the same HTMLRewriter approach for `href` and `src`.
