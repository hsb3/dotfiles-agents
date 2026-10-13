---
id: TASK-3
title: Render a page's Markdown to its HTML body
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:07'
updated_date: '2026-10-13 03:16'
labels: []
milestone: m-0
dependencies: []
references:
  - render
modified_files:
  - .groma/systems/docs/containers/site-cli/components/render.md
  - bun.lock
  - package.json
  - >-
    .backlog/decisions/decision-2 -
    Post-process-md4c-HTML-with-HTMLRewriter-for-heading-IDs.md
  - src/render.ts
  - test/render.test.ts
priority: high
type: feature
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Pages must render as GitHub renders them, with GitHub's heading IDs because the content's anchors were written against GitHub, with working Mermaid diagrams, and with a real H1 and `<title>` even for decision records without one. Builds the groma ghost `render` (src/render.ts); adds `github-slugger` 2.0.0 as the only runtime dependency.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Frontmatter at the very top is removed; invalid YAML or a non-mapping fails with `<page>: bad frontmatter: <reason>`; both decision-record shapes work
- [x] #2 A page with no H1 (ATX or Setext, not inside code) gets one from a non-empty frontmatter `title` or the file name, escaped, with an ID
- [x] #3 GFM tables, strikethrough, task lists, autolinks, hard breaks and raw HTML (unknown tags kept) render as md4c does
- [x] #4 `mermaid` fences become `<pre class="mermaid">` holding only the escaped source; other code blocks `<pre><code class="language-<info>">`; every `<pre>` and `<table>` gets `tabindex="0"`
- [x] #5 Every heading gets the GitHub ID; every row of the SPEC heading-ID table passes as a test
- [x] #6 The first H1's text (for `<title>`), every id in the body, and a has-Mermaid flag are returned; contents entries are built by Layout from the link-rewritten body
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. bun add github-slugger@2.0.0 --exact (only runtime dependency).
2. src/render.ts: split frontmatter (Bun.YAML, mapping only), render with Bun.markdown.html (GFM, autolinks, headings off), detect an existing H1 in the HTML, otherwise prepend an escaped H1 from title/file name.
3. HTMLRewriter pass: heading IDs from decoded text content via github-slugger (one slugger per page), tabindex=0 on pre/table, collect every id and the first H1 text; mermaid fences rewritten to <pre class="mermaid">.
4. test/render.test.ts: SPEC heading table, both frontmatter shapes, bad frontmatter, H1 insertion, GFM features, mermaid/code blocks, tabindex.
5. Gate, scan, accept render, lint, finish.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Product calls: any H1 in the rendered HTML counts, raw `<h1>` included, so a README with a centred raw H1 gets no second one; raw HTML headings get GitHub IDs too, and one with its own `id` keeps it; empty frontmatter (`---` then `---`) is an empty mapping; a `---` first line with no closing line is not frontmatter; a whitespace-only `title` falls back to the file name. AC 6 changed in the build: the contents entries are built by Layout from the final (link-rewritten) body, since an image or link in a heading must show its rewritten URL; Render returns body, title, ids and the Mermaid flag.
Evidence: `bunx tsc --noEmit && bun test` -> 55 pass, 0 fail (test/render.test.ts: all 9 SPEC heading-ID rows incl. repeated Install, both decision frontmatter shapes, bad/non-mapping frontmatter messages, H1 insertion and escaping, Setext vs code block, GFM features, raw HTML pass-through, Mermaid and code blocks, tabindex). `groma scan` matched 1; `groma accept render`; rescan + `groma lint` -> No findings. github-slugger 2.0.0 pinned exactly; bun.lock updated.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added src/render.ts: frontmatter split (Bun.YAML), md4c rendering with GFM and autolinks, H1 insertion, GitHub heading IDs via github-slugger in an HTMLRewriter post-pass, Mermaid <pre class="mermaid">, tabindex on pre/table, title text and id collection. Added github-slugger 2.0.0 (exact) and decision-2. Verified by 26 new tests and a clean scan/lint.
<!-- SECTION:FINAL_SUMMARY:END -->
