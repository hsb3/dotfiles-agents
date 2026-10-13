---
id: TASK-1
title: Load and validate site.config.json
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:07'
updated_date: '2026-10-13 03:11'
labels: []
milestone: m-0
dependencies: []
references:
  - config
  - site-config
modified_files:
  - .groma/systems/docs/containers/site-cli/components/config.md
  - SOP-FEEDBACK.md
  - site.config.json
  - src/config.ts
  - test/config.test.ts
  - test/fixture.ts
priority: high
type: feature
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Every build starts from the unit's own `site.config.json` (or `--config`), and a bad config must stop the build with a message naming the file, before anything is rendered. Builds the groma ghost `config` (src/config.ts) and ships the config file with dotfiles-agents' values (store `site-config`).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `site.config.json` ships in the unit folder with exactly the values SPEC.md gives
- [x] #2 Missing `repo` or `ref`, an unknown key, or a wrongly typed key is reported as `<config path>: <problem>`
- [x] #3 `base` defaults to `/<name>` from `repo`; a base that is not `/` plus one segment of `A–Z a–z 0–9 _ -` is reported
- [x] #4 The site name is the base without its `/`
- [x] #5 Unit tests cover every config error message this task owns
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add site.config.json at the unit root with the SPEC values.
2. src/config.ts: loadConfig(path, label) reads JSON, checks keys and types (repo owner/name, ref, base, pages, exclude, rename, nav, footer and nested label/page), collects every problem as '<config path>: <problem>' into a ConfigError, defaults base to /<name>, derives the site name.
3. test/config.test.ts: shipped file loads with SPEC values; each error message; base default and validation.
4. Gate, groma scan, accept config and config->site-config, lint, finish.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Product calls: config problems are all collected and printed before exiting; nested nav/footer entries report unknown and missing keys as `nav[i]: ...`; `repo` must be `<owner>/<name>`; when `base` is absent and the repo name is not a valid base segment the config asks for an explicit base. The config path in messages is the label the caller passes (TASK-6 decides it).
Evidence: `bunx tsc --noEmit && bun test` -> 18 pass, 0 fail (test/config.test.ts covers the shipped values, base default/validation, every config message this task owns). `groma scan` matched 1 (config); `groma accept config`, `groma accept relation config site-config`; rescan + `groma lint` -> No findings (after extracting a shared `checked` helper for the duplicate lint flagged).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added site.config.json with the SPEC values and src/config.ts, which loads it, validates every key and type, defaults base to /<name> and derives the site name; all problems are reported as `<config path>: <problem>`. Verified by the gate (18 tests) and a clean groma scan/lint with config accepted.
<!-- SECTION:FINAL_SUMMARY:END -->
