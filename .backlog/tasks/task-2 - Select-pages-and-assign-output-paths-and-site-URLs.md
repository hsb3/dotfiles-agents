---
id: TASK-2
title: Select pages and assign output paths and site URLs
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:07'
updated_date: '2026-10-13 03:13'
labels: []
milestone: m-0
dependencies:
  - TASK-1
references:
  - pages
  - dotfiles-agents-checkout
  - config
modified_files:
  - .groma/systems/docs/containers/site-cli/components/pages.md
  - test/fixture.ts
  - >-
    .backlog/decisions/decision-1 -
    Own-glob-matcher-for-the-page-list-instead-of-Bun.Glob.md
  - src/pages.ts
  - test/pages.test.ts
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
- [x] #1 `*` matches within one segment and `**` across segments; wildcards skip names starting with `.`, explicit names do not; symlinked files match
- [x] #2 `exclude` removes matches; an entry in `pages` or `exclude` that matches nothing is a config error
- [x] #3 Output path is the `rename` entry or the listed path with `.md` → `.html`; the site URL is `<base>/<output path>` with each segment percent-encoded except `A–Z a–z 0–9 - . _ ~`
- [x] #4 A symlinked page keeps its listed path
- [x] #5 Config errors reported: nav, footer or rename page not in the page list; no page at `index.html`; two pages with the same output path; an output path with a hidden segment (`<config>: <page> would publish at hidden path <output>`)
- [x] #6 Tests use synthetic checkouts in temporary folders
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. src/pages.ts: own glob matcher (* within a segment, ** across, wildcards skip dot names, literal segments match dot names), a directory walk from the checkout root that follows symlinked files but not symlinked folders, .md regular files only.
2. selectPages(config, root): expand pages, drop exclude matches, report entries that match nothing; Page = listed path, output path (rename or .md->.html), site URL (segments percent-encoded except unreserved); check nav/footer/rename pages listed, index.html present, unique output paths, no hidden output segment; collect all problems as ConfigError.
3. URL helpers (encodePath, siteUrl, githubUrl) exported for Links and Layout; readSource reads a page's Markdown.
4. test/pages.test.ts with synthetic checkouts (symlinked plugin README, renamed .github/CONTRIBUTING.md, excluded page) covering every message.
5. Gate, scan, accept pages and pages->dotfiles-agents-checkout, lint, finish.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Product calls: only `*` and `**` are wildcards (decision-1); only regular `.md` files are selected; `**` does not descend into symlinked folders; a pages entry or rename value with an empty, `.` or `..` segment is a config error; `exclude` matches against the selected pages; pages are sorted by listed path (code-point order) for stable output; every page-list problem is collected before failing.
Evidence: `bunx tsc --noEmit && bun test` -> 29 pass, 0 fail (test/pages.test.ts: synthetic dotfiles-like checkout with a symlinked plugins/bun/README.md, .github/CONTRIBUTING.md renamed, excluded template, hidden dot folders; every page-list message; URL encoding and GitHub URLs). `groma scan` matched 1 (pages); accepted pages and pages -> dotfiles-agents-checkout; authored pages -> config (the derived ConfigError row); rescan + `groma lint` -> No findings.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added src/pages.ts: glob expansion against the checkout, exclude, output paths, percent-encoded site URLs, GitHub blob/tree/raw URL helpers, and the page-list config checks (unlisted nav/footer/rename pages, no index.html, duplicate and hidden output paths). Recorded decision-1 (own glob matcher). Verified by 11 new tests and a clean scan/lint.
<!-- SECTION:FINAL_SUMMARY:END -->
