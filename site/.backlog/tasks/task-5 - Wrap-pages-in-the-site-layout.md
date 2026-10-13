---
id: TASK-5
title: Wrap pages in the site layout
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:07'
updated_date: '2026-10-13 03:19'
labels: []
milestone: m-0
dependencies:
  - TASK-3
references:
  - layout
  - jsdelivr-cdn
  - pages
modified_files:
  - .groma/systems/docs/containers/site-cli/components/layout.md
  - src/layout.ts
  - test/layout.test.ts
priority: high
type: feature
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Every page must be exactly the document the SPEC fixes, because the stylesheet's selectors and the site's accessibility depend on it. Builds the groma ghost `layout` (src/layout.ts).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Head, skip link, header, nav, main, contents and footer match the SPEC example element for element and attribute for attribute
- [x] #2 The current nav entry has `aria-current="page"`; labels are escaped
- [x] #3 The contents block lists H1s and nested H2s, and is left out without an H2
- [x] #4 Only pages with a Mermaid diagram get the Mermaid module script, verbatim
- [x] #5 Contents entries show the heading's inline content with links unwrapped and code spans kept, taken from the link-rewritten body
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. src/layout.ts: layoutPage({site, ref, page, title, body, mermaid}) returns the SPEC page document line for line: head (title '<H1 text> · <site name>', stylesheet), skip link, header (brand to <base>/index.html, repository), nav with escaped labels and aria-current on the current page, main with the contents block, body and footer (canonical Markdown blob URL at the ref, config footer links joined by ' · '), Mermaid script after </div> only when the page has a diagram.
2. Contents: H1/H2 found in the final body; inner HTML with <a> unwrapped and ids dropped (HTMLRewriter); H2s nested under the preceding H1, top level before any H1; omitted without an H2.
3. test/layout.test.ts: the SPEC codex-compatibility example byte for byte (modulo the body), aria-current, escaping, contents nesting and omission, Mermaid script.
4. Gate, scan, accept layout and layout -> jsdelivr-cdn, author derived rows, lint, finish.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Product calls: contents entries drop `id` attributes from the copied heading markup so the page keeps unique ids; other inline markup (em, strong, code, raw tags) is kept; the body is inserted as rendered with trailing newlines trimmed.
Evidence: `bunx tsc --noEmit && bun test` -> 83 pass, 0 fail (test/layout.test.ts: the SPEC codex-compatibility document asserted byte for byte with the shipped config; aria-current only on the current page; escaped labels and title; contents nesting, top-level H2, leaf H1, links unwrapped, code kept; no contents without H2; footer blob URL at the passed ref; Mermaid script verbatim against SPEC.md and only on diagram pages). `groma scan` matched 1; accepted layout and layout -> jsdelivr-cdn; authored layout -> pages over the derived row; `groma lint` -> No findings.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added src/layout.ts: the full page document per the SPEC contract with nav, aria-current, contents block from the final body, footer and the verbatim Mermaid loader for diagram pages. Verified by 8 new tests including a byte-for-byte check of the SPEC example, and a clean scan/lint.
<!-- SECTION:FINAL_SUMMARY:END -->
