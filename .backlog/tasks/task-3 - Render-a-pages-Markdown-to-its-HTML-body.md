---
id: TASK-3
title: Render a page's Markdown to its HTML body
status: To Do
assignee: []
created_date: '2026-10-13 03:07'
labels: []
milestone: m-0
dependencies: []
references:
  - render
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
- [ ] #1 Frontmatter at the very top is removed; invalid YAML or a non-mapping fails with `<page>: bad frontmatter: <reason>`; both decision-record shapes work
- [ ] #2 A page with no H1 (ATX or Setext, not inside code) gets one from a non-empty frontmatter `title` or the file name, escaped, with an ID
- [ ] #3 GFM tables, strikethrough, task lists, autolinks, hard breaks and raw HTML (unknown tags kept) render as md4c does
- [ ] #4 `mermaid` fences become `<pre class="mermaid">` holding only the escaped source; other code blocks `<pre><code class="language-<info>">`; every `<pre>` and `<table>` gets `tabindex="0"`
- [ ] #5 Every heading gets the GitHub ID; every row of the SPEC heading-ID table passes as a test
- [ ] #6 Title text, H1/H2 contents entries (links unwrapped, code spans kept) and a has-Mermaid flag are returned
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
