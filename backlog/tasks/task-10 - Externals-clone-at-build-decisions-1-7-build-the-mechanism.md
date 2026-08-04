---
id: TASK-10
title: 'Externals clone-at-build: decisions 1-7 + build the mechanism'
status: To Do
assignee: []
created_date: '2026-08-04 00:43'
labels:
  - decision
  - externals
milestone: m-0
dependencies:
  - TASK-2
  - TASK-26
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/36'
priority: high
type: feature
ordinal: 10000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Migrated from GH #36 (carried its GH milestone). Third-party skills recorded in externals.yaml (upstream + pinned SHA) get materialized at build/install time instead of being copied in (ADR 0015). Blocked on decisions 1-7: network-at-build in CI, drop policy, ref-pin format, null-upstream semantics. Under the new architecture this becomes clone-at-INSTALL for claude-code (a plugin dir populated from externals.yaml) — re-scope the design to the symlink model. Also the compliant path for the parked visual-planning skills and the mechanism home for vendored-skill provenance (task-11).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Decisions 1-7 ruled and recorded
- [ ] #2 Mechanism materializes externals per pin, ADR 0015 clean
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Decisions ruled 2026-08-03 (decision-6, AC#1 satisfied): materialization = pinned-vendored-copy, superseding clone-at-build (#36 / ADR 0003). D1-D7 resolved per memo `_meta/plans/externals-clone-vs-vendor/memo.md`. Also: drop the 4 plugin externals (install-from-upstream, not re-hosted) — only pptx stays vendored; vendoring gains a minimum-bar rule (task-26, blocks this build). Remaining AC#2 build scope: amend ADR 0015 + add `origin: vendored` class + check_provenance vendored arm + drop the 4 entries + reclassify `pptx-themes/base` + optional `make externals-drift`. Now depends on TASK-26.
<!-- SECTION:NOTES:END -->
