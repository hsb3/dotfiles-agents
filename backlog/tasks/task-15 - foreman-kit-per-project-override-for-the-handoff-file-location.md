---
id: TASK-15
title: 'foreman-kit: per-project override for the handoff-file location'
status: To Do
assignee: []
created_date: '2026-08-04 00:43'
updated_date: '2026-08-06 14:13'
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

## Comments

<!-- COMMENTS:BEGIN -->
author: session 2026-08-06
created: 2026-08-06 14:13
---
META-06 half of this task resolved 2026-08-06 (owner sign-off, recorded in decision-8): the published repo-meta-structure checklist now accepts the handoff hooks' precedence trio (_meta/HANDOFF.md, HANDOFF.md, .claude/HANDOFF.md), and DOCS-03..05 accept backlog/decisions/ as the ADR home. This repo's .claude/HANDOFF.md location is now standard-conformant. Residual scope of this task: the per-project handoff-location override feature in foreman-kit itself.
---
<!-- COMMENTS:END -->
