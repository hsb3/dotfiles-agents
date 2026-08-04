---
id: TASK-10
title: 'Externals clone-at-build: decisions 1-7 + build the mechanism'
status: To Do
assignee: []
created_date: '2026-08-04 00:43'
updated_date: '2026-08-04 02:55'
labels:
  - decision
  - externals
milestone: m-0
dependencies:
  - TASK-2
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/36'
priority: high
type: feature
ordinal: 700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Migrated from GH #36 (carried its GH milestone). Third-party skills recorded in externals.yaml (upstream + pinned SHA) get materialized at build/install time instead of being copied in (ADR 0015). Blocked on decisions 1-7: network-at-build in CI, drop policy, ref-pin format, null-upstream semantics. Under the new architecture this becomes clone-at-INSTALL for claude-code (a plugin dir populated from externals.yaml) — re-scope the design to the symlink model. Also the compliant path for the parked visual-planning skills and the mechanism home for vendored-skill provenance (task-11).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Decisions 1-7 ruled and recorded
- [ ] #2 Mechanism materializes externals per pin, ADR 0015 clean
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Owner 2026-08-04: session to draft a decisions-1-7 memo (each with a recommended call) for a focused second sign-off round, THEN build. Owner note to weigh in the memo: 'might just be simpler to keep a pinned, vendored copy in the repo' — i.e. the memo must compare clone-at-install vs pinned-vendored-copy, which reopens ADR 0015. Decisions 1-7 not yet ruled.
<!-- SECTION:NOTES:END -->
