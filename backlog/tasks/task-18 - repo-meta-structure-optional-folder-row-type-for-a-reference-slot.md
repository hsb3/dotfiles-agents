---
id: TASK-18
title: 'repo-meta-structure: optional-folder row type for a reference/ slot'
status: To Do
assignee: []
created_date: '2026-08-04 00:43'
updated_date: '2026-08-06 21:33'
labels:
  - primitives
milestone: m-2
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/207'
priority: low
type: feature
ordinal: 1800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add an optional-folder row type to the shared `repo-meta-structure` standard (`primitives-core/skills/repo-meta-structure/references/layout.md` + its checklist) so it can express a `_meta/reference/` slot — secret-free durable runbooks, distinct from operations/ / research/ / briefings/ / docs/. Today every taxonomy row is a required machine-checkable path-exists row, so an optional or descriptive-only folder can't be expressed without breaking the standard's own contract; this repo declares it as per-repo variance in `_meta/mise-en-place.yml` as a workaround (which fully resolves the local need — hence Low). Then migrate this repo's variance declaration to the shared slot. Substance from closed GH #207 (follow-up to #149/PR #206).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 layout.md + checklist define an optional-row type that does not break the path-exists contract
- [ ] #2 This repo's `_meta/reference/` variance declaration migrated from mise-en-place.yml to the shared slot
<!-- AC:END -->
