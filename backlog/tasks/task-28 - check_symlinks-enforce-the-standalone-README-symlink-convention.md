---
id: TASK-28
title: 'check_symlinks: enforce the standalone-README symlink convention'
status: Done
assignee:
  - '@claude'
created_date: '2026-08-06'
updated_date: '2026-08-07 00:55'
labels:
  - gates
milestone: m-1
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
- [x] #1 `check_symlinks.py` fails a standalone plugin whose `README.md` is a regular file rather than a symlink
- [x] #2 The check distinguishes standalone from bundle assemblies by a stated rule, and that rule is written in the checker's docstring
- [x] #3 Bundle assemblies (code-desk, diagrams, foreman-kit, obsidian-toolkit) still pass with regular-file READMEs
- [x] #4 A test in `tests/test_check_symlinks.py` covers both the passing and failing shapes
- [x] #5 `make ci` green
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Deciding "standalone vs bundle" mechanically: a plugin whose assembly contains exactly one
skill and no agents/hooks is a standalone. Worth confirming that rule holds across all 19
plugins before encoding it — `pptx-themes` and `project-memory` are single-skill but carry
scripts, and `owner-signoff` is single-skill standalone-only.

Test-first. Red run: all 9 new ReadmeConvention tests errored with AttributeError: module 'check_symlinks' has no attribute 'readme_problems', while the 7 pre-existing SymlinkLint tests still passed — proving the new tests exercise not-yet-built code rather than a broken harness. Green: 16 tests OK.

Rule encoded at scripts/check_symlinks.py:14-21 (docstring) and :90-97 (is_standalone): a plugin is standalone iff its assembly has exactly one entry under skills/ and no non-hidden entries under agents/ or hooks/. Standalones must symlink README.md to primitives-core/skills/<skill-id>/README.md. Anything else is a bundle and is untouched.

Error paths covered: missing README entirely; regular-file README on a standalone; dangling README symlink (caught by the new check AND independently by the pre-existing generic symlink walk); symlink resolving to the wrong skill's README; symlink resolving outside primitives-core. Negative cases confirmed clean: multi-skill bundle, single-skill+agent, single-skill+hook, all with regular-file READMEs.

Real-tree check: python3 scripts/check_symlinks.py exits 0 against the live repo — all 21 plugins pass, no exceptions needed, nothing escalated. Additionally sanity-checked end-to-end by copying the real plugins/, primitives-core/, and .claude-plugin/ trees to a tempdir, confirming zero problems on the untouched copy, then corrupting claude-code-config's README symlink into a regular file and confirming the checker fired naming that exact path.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
check_symlinks now enforces the ADR 0017 standalone-README convention, closing the hole where a standalone plugin could ship a hand-written README that silently drifts from the skill's own. Rides the existing make symlinks target, so no new CI job name is introduced (branch protection pins those). Verified with a captured red run, 9 new tests including the four bundle negative cases, and a real-tree run that all 21 current plugins pass.
<!-- SECTION:FINAL_SUMMARY:END -->
