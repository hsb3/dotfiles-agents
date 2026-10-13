---
id: TASK-4
title: Rewrite and check links and images
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:07'
updated_date: '2026-10-13 03:17'
labels: []
milestone: m-0
dependencies:
  - TASK-2
  - TASK-3
references:
  - links
  - github-content-hosts
  - pages
  - render
modified_files:
  - .groma/systems/docs/containers/site-cli/components/links.md
  - src/links.ts
  - test/links.test.ts
priority: high
type: feature
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The tool's main job in CI is failing on broken links, and on Pages no link may stay relative. Builds the groma ghost `links` (src/links.ts), which rewrites every `<a href>` and `<img src>` per the SPEC link rules and reports broken links and missing headings.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Scheme and `//` destinations are left alone; `#fragment` and empty destinations point at the page itself
- [x] #2 Local paths (percent-decoded, relative to the listed page folder or the checkout root for `/`) must name a file or folder inside the checkout, else `<page>: broken local link: <destination>`; leaving through `..` or a symlink counts as missing
- [x] #3 Pages and README folders become site URLs; other files and folders GitHub blob/tree URLs, images raw URLs, at the build ref; query and fragment kept
- [x] #4 A fragment on a page link must match an id in that page's final HTML, else `<page>: missing heading: <destination>`
- [x] #5 Every row of the SPEC link example table passes as a test
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. src/links.ts: rewriteLinks(context, page, body) collects every a[href] and img[src] in document order (HTMLRewriter), resolves each destination, then writes the new values in a second pass.
2. Resolution: scheme and // left alone; empty or query-only points at the page itself, fragment-only stays; path percent-decoded, relative to the listed page folder or the checkout root for /; must exist inside the checkout after realpath (.. or symlink escape = missing); folder README pages and pages become site URLs, other files blob, folders tree, images raw; query and fragment kept; fragments on page links checked against the target page's ids.
3. Problems '<page>: broken local link: <dest>' / '<page>: missing heading: <dest>' in document order.
4. test/links.test.ts: every row of the SPEC example table from docs/README.md, plus symlinked page resolution, escapes via .. and symlink, raw HTML links, query kept.
5. Gate, scan, accept links and its relations, author derived rows, lint, finish.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Product calls: an empty `href`/`src` and a query-only destination become the page's own site URL (no relative URL may remain); an empty fragment (`page.md#`) is not checked; a trailing slash on a file is a broken link; a malformed percent escape in the path is a broken link; an `<img>` that points at a page gets the page URL (only non-page images become raw URLs); the destination in a problem line is the attribute value with entities decoded.
Evidence: `bunx tsc --noEmit && bun test` -> 75 pass, 0 fail (test/links.test.ts: every SPEC example row incl. image, broken link and missing heading; symlinked page resolving from plugins/bun/; root-relative and root folder; percent-decoding; query/fragment kept with entities; GitHub fragments unchecked; ref passed; escapes via .. and symlink; raw HTML). `groma scan` matched 1; accepted links, links -> dotfiles-agents-checkout, links -> github-content-hosts; authored links -> pages (Builds GitHub URLs) and links -> render (Decodes HTML entities) over the derived rows; `groma lint` -> No findings.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added src/links.ts: collects every a[href]/img[src], resolves local destinations inside the checkout (realpath-checked), rewrites to site, blob, tree or raw URLs at the build ref keeping query and fragment, and reports broken local links and missing headings in document order. Verified by 20 new tests and a clean scan/lint.
<!-- SECTION:FINAL_SUMMARY:END -->
