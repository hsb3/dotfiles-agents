---
id: TASK-038
title: 'atelier scout: no sanctioned read path for CLI-mediated repos'
status: To Do
assignee: []
created_date: '2026-08-06 23:49'
labels:
  - primitives
milestone: m-2
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/255'
priority: medium
type: feature
ordinal: 16000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GH issue #255: scout's hard read-only guarantee (Read/Grep/Glob, no Bash) collides with repos whose project law routes all task reads through a CLI -- e.g. this repo's own Backlog.md CRITICAL_INSTRUCTION ('do not edit Backlog task files directly, use the backlog CLI'), whose read guides assume 'backlog task view TASK-123 --plain'. The workaround used (Glob the raw markdown, Read it directly) worked but bypasses the sanctioned read path and can silently diverge from the CLI-rendered view -- e.g. computed fields and config-stamped Definition-of-Done defaults are invisible in raw frontmatter, so a scout reading raw files will wrongly report 'no DoD on this task'. Checked #260: no diff to agents/scout.md at all, so this is still open.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Either: scout gains an opt-in dispatch knob for a documented, explicitly allowlisted read-only CLI command set (Bash stays off by default), or: the foreman skill documents a pattern for CLI-mediated repos (paste CLI output into the brief vs. point scout at raw files with the specific caveat about computed/config-stamped fields)
- [ ] #2 The chosen approach is written into the foreman skill's own docs so a future foreman does not have to re-derive it per brief
<!-- AC:END -->
