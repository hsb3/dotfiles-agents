---
id: TASK-060
title: >-
  Bundle README skill tables are ungated — a skill can ship in a bundle without
  being listed
status: To Do
assignee: []
created_date: '2026-08-11 07:08'
labels:
  - gates
milestone: m-1
dependencies: []
priority: medium
type: feature
ordinal: 39000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Each bundle README (plugins/<id>/README.md) carries a hand-maintained table listing the bundle's skills. Nothing reads it. The catalog guard checks the ROOT README's counts and blurbs against the assembly on disk, and check_symlinks checks the assembly against marketplace.json, but no gate compares a bundle README's own table against the primitives actually symlinked into that bundle.

Observed 2026-08-11 shipping comment-hygiene: the skill was symlinked into plugins/solo-skills/skills/, counted correctly in the root README (30 -> 31), and passed every gate, while the solo-skills README skill table never gained a row. A reader installing the bundle would not find the skill listed. Caught by hand, not by CI.

This is the same failure class as the root-README catalog drift that TASK-031 and the catalog guard already closed, one level down. It matters most for solo-skills, whose README table is the only place its ~31 skills are enumerated for a user.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A gate compares every plugins/<id>/README.md skill/agent/hook table against the primitives actually symlinked into that assembly, and fails on a member missing from the table
- [ ] #2 The gate is derived from the assembly on disk, never from a recorded list (per the DERIVE-a-set rule)
- [ ] #3 The gate runs inside an existing 'make ci' job, since CI job names are pinned by branch protection
- [ ] #4 Running it against HEAD before the fix reproduces the comment-hygiene omission; running it after is clean
- [ ] #5 A bundle README that legitimately groups or omits a member has a documented, machine-readable way to say so, or the rule is scoped to exclude that case
<!-- AC:END -->
