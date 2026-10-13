---
id: TASK-6
title: site build command
status: To Do
assignee: []
created_date: '2026-10-13 03:07'
labels: []
milestone: m-0
dependencies:
  - TASK-1
  - TASK-2
  - TASK-4
  - TASK-5
references:
  - build
  - commands
  - cli
  - site-output
  - stylesheet
priority: high
type: feature
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
CI runs `site build` as the repo-wide link check on every pull request and as the build step of the Pages deploy, so it must report every problem in one run and write nothing on failure. Builds the groma ghosts `build` (src/build.ts) and `commands` (src/commands.ts) and wires `cli` to them; the output folder is the store `site-output`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `site build [--root] [--config] [--output] [--ref]` with the SPEC defaults renders every page and prints `<N> pages built, links verified: <output>`
- [ ] #2 On problems, stderr gets one sorted line per problem then `build: <K> problems; nothing written`, exit 1, nothing written
- [ ] #3 An output folder that is the checkout or inside it (after resolving symlinks) is refused
- [ ] #4 A successful build writes each page and a byte-identical `assets/site.css`, overwrites same-named files and leaves others; output is byte-identical across runs
- [ ] #5 No subcommand, or an unknown subcommand or option, prints usage to stderr and exits 1
- [ ] #6 Fixture checkouts cover the SPEC list: symlinked plugin README, both frontmatter shapes, renamed CONTRIBUTING, excluded page linked, Mermaid, folder link, image, every error message
- [ ] #7 README.md documents the build command, the config keys and the link rules
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
