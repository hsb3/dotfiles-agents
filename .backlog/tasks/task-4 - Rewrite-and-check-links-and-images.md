---
id: TASK-4
title: Rewrite and check links and images
status: To Do
assignee: []
created_date: '2026-10-13 03:07'
labels: []
milestone: m-0
dependencies:
  - TASK-2
  - TASK-3
references:
  - links
  - github-content-hosts
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
- [ ] #1 Scheme and `//` destinations are left alone; `#fragment` and empty destinations point at the page itself
- [ ] #2 Local paths (percent-decoded, relative to the listed page folder or the checkout root for `/`) must name a file or folder inside the checkout, else `<page>: broken local link: <destination>`; leaving through `..` or a symlink counts as missing
- [ ] #3 Pages and README folders become site URLs; other files and folders GitHub blob/tree URLs, images raw URLs, at the build ref; query and fragment kept
- [ ] #4 A fragment on a page link must match an id in that page's final HTML, else `<page>: missing heading: <destination>`
- [ ] #5 Every row of the SPEC link example table passes as a test
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
