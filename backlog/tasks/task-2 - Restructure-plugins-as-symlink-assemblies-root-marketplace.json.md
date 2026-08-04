---
id: TASK-2
title: 'Restructure: plugins/ as symlink assemblies + root marketplace.json'
status: Done
assignee: []
created_date: '2026-08-04 00:41'
updated_date: '2026-08-04 02:03'
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
Create plugins/<id>/ dirs (plugin.json, hooks.json hand-authored; skills/agents/hooks as symlinks into primitives-core/), move .claude-plugin/marketplace.json to repo root, add a symlink lint (every link under plugins/ resolves inside the repo). Multi-homing a skill = one more symlink. READMEs travel with their skill (owner ruling 2026-08-03, ADR 0017 §4): dissolve primitives-core/standalone-readmes/ into primitives-core/skills/<id>/README.md and make the standalone plugin's root README a symlink to it; bundle READMEs are hand-authored directly at plugins/<id>/README.md (bundles/ dissolves).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Symlink lint in make ci (targets resolve inside repo)
- [x] #2 Local install from the repo as a path marketplace verified for one bundle + one standalone
- [x] #3 standalone-readmes/ dissolved: each README lives at primitives-core/skills/<id>/README.md, symlinked to its plugin root; bundles/ READMEs moved to plugins/<id>/README.md
- [x] #4 All 15 current plugins reproduced as symlink assemblies; installed output byte-identical to today's dist output except the README relocation (README also present inside the skill dir)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Executed on branch feat/task-2-symlink-plugins. All 15 plugins as symlink assemblies (51 links); root .claude-plugin/marketplace.json; scripts/check_symlinks.py in make ci; standalone-readmes/ + bundles/ dissolved per ADR 0017 §4 (pptx-themes README merged with its attribution README — both consumer + license content preserved). Proofs: make ci green (163 tests); dereferenced assemblies byte-identical to dist output modulo gitignored litter; live path-marketplace install of foreman-kit + private-fork materializes fully (0 symlinks installed, hooks/agents/READMEs present). dist machinery untouched-but-repointed (README sources); retirement is task-3.
<!-- SECTION:NOTES:END -->
