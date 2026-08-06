---
id: TASK-28
title: 'check_symlinks: enforce the standalone-README symlink convention'
status: To Do
assignee: []
created_date: '2026-08-06'
updated_date: '2026-08-06'
labels:
  - gates
  - tech-debt
dependencies:
  - TASK-9
priority: medium
type: chore
ordinal: 2800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ADR 0017 and `flow.yaml`'s `plugin-assemblies` node both state the convention: in a plugin
assembly, **bundle READMEs are regular files, standalone READMEs are symlinks to the skill's
own README** (`primitives-core/skills/<id>/README.md`). All 15 standalones on disk follow it.
`scripts/check_symlinks.py` does not enforce it — the string "readme" does not appear in the
checker at all.

Found 2026-08-06 while building task-9: three new standalone plugins were first created with
regular-file READMEs and `make ci` passed clean. The deviation was caught by eye, not by the
gate. A future assembly can ship the same violation undetected, which matters because the
symlinked README is what makes a standalone's docs travel with its source instead of drifting
from it.

Related gap found at the same time: those three skills had no `README.md` in
`primitives-core/` at all, so nothing would have flagged a standalone whose symlink target
does not exist either (the symlink-resolves check would catch a dangling link, but only once
someone writes the symlink).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `check_symlinks.py` fails a standalone plugin whose `README.md` is a regular file rather than a symlink
- [ ] #2 The check distinguishes standalone from bundle assemblies by a stated rule, and that rule is written in the checker's docstring
- [ ] #3 Bundle assemblies (code-desk, diagrams, foreman-kit, obsidian-toolkit) still pass with regular-file READMEs
- [ ] #4 A test in `tests/test_check_symlinks.py` covers both the passing and failing shapes
- [ ] #5 `make ci` green
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Deciding "standalone vs bundle" mechanically: a plugin whose assembly contains exactly one
skill and no agents/hooks is a standalone. Worth confirming that rule holds across all 19
plugins before encoding it — `pptx-themes` and `project-memory` are single-skill but carry
scripts, and `owner-signoff` is single-skill standalone-only.
<!-- SECTION:NOTES:END -->
