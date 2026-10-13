---
id: TASK-2
title: Select pages and assign output paths and site URLs
status: To Do
assignee: []
created_date: '2026-10-13 03:07'
labels: []
milestone: m-0
dependencies:
  - TASK-1
references:
  - pages
  - dotfiles-agents-checkout
priority: high
type: feature
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The config names pages by path and glob; the build needs the exact page list, each page's output path and site URL, and the config errors that only the page list can reveal (the dotfiles-agents config selects 59 pages, two of them symlinks). Builds the groma ghost `pages` (src/pages.ts).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `*` matches within one segment and `**` across segments; wildcards skip names starting with `.`, explicit names do not; symlinked files match
- [ ] #2 `exclude` removes matches; an entry in `pages` or `exclude` that matches nothing is a config error
- [ ] #3 Output path is the `rename` entry or the listed path with `.md` → `.html`; the site URL is `<base>/<output path>` with each segment percent-encoded except `A–Z a–z 0–9 - . _ ~`
- [ ] #4 A symlinked page keeps its listed path
- [ ] #5 Config errors reported: nav, footer or rename page not in the page list; no page at `index.html`; two pages with the same output path; an output path with a hidden segment (`<config>: <page> would publish at hidden path <output>`)
- [ ] #6 Tests use synthetic checkouts in temporary folders
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
