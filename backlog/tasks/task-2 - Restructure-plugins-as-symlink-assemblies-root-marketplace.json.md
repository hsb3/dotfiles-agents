---
id: TASK-2
title: 'Restructure: plugins/ as symlink assemblies + root marketplace.json'
status: To Do
assignee: []
created_date: '2026-08-04 00:41'
labels:
  - refactor
milestone: m-0
dependencies:
  - TASK-1
priority: high
type: feature
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create plugins/<id>/ dirs (plugin.json, hooks.json hand-authored; skills/agents/hooks as symlinks into primitives-core/), move .claude-plugin/marketplace.json to repo root, add a symlink lint (every link under plugins/ resolves inside the repo). Multi-homing a skill = one more symlink.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 All 15 current plugins reproduced as symlink assemblies; installed output byte-identical to today's dist output
- [ ] #2 Symlink lint in make ci (targets resolve inside repo)
- [ ] #3 Local install from the repo as a path marketplace verified for one bundle + one standalone
<!-- AC:END -->
