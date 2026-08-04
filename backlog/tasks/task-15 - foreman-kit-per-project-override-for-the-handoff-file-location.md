---
id: TASK-15
title: 'foreman-kit: per-project override for the handoff-file location'
status: To Do
assignee: []
created_date: '2026-08-04 00:43'
labels:
  - foreman-kit
  - decision
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/220'
priority: high
type: feature
ordinal: 200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Migrated from GH #220. The hardcoded trio (_meta/HANDOFF.md / HANDOFF.md / .claude/HANDOFF.md) bakes in the code-desk taxonomy; Backlog.md-managed projects (now including THIS repo) have no sanctioned home. Decision: override via .claude/foreman-kit.local.md frontmatter key (recommended) vs env var. Honor in both handoff hooks + the handoff skill.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Override mechanism ruled and implemented in surfacer + freshness-guard + SKILL.md
- [ ] #2 Standard trio unchanged when override absent
<!-- AC:END -->
