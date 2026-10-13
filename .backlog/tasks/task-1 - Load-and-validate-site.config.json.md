---
id: TASK-1
title: Load and validate site.config.json
status: To Do
assignee: []
created_date: '2026-10-13 03:07'
labels: []
milestone: m-0
dependencies: []
references:
  - config
  - site-config
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
- [ ] #1 `site.config.json` ships in the unit folder with exactly the values SPEC.md gives
- [ ] #2 Missing `repo` or `ref`, an unknown key, or a wrongly typed key is reported as `<config path>: <problem>`
- [ ] #3 `base` defaults to `/<name>` from `repo`; a base that is not `/` plus one segment of `A–Z a–z 0–9 _ -` is reported
- [ ] #4 The site name is the base without its `/`
- [ ] #5 Unit tests cover every config error message this task owns
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
