---
id: TASK-1
title: >-
  ADR: pointer-based marketplace architecture (one repo, symlink plugins, no
  tracked dist)
status: Done
assignee: []
created_date: '2026-08-04 00:41'
updated_date: '2026-08-04 01:52'
labels:
  - refactor
milestone: m-0
dependencies: []
priority: high
type: docs
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Formalize the 2026-08-03 restructure rulings as an ADR in docs/decisions/: plugins/<id>/ as thin symlink assemblies over primitives-core/, root .claude-plugin/marketplace.json, no tracked generated artifacts (claude-code installs natively; opencode generates at install time), one repo serving both targets. Supersedes ADR 0008's dist-lane design; amends ADR 0016. Grounded in the verified docs findings + live PoC (symlink dereference for skills/agents/hooks dirs confirmed; out-of-marketplace symlinks silently skipped).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ADR drafted in docs/decisions/ and approved by owner
- [x] #2 Covers: symlink mechanism + install-time materialization, one-repo two-target ruling, tripwires for a future repo split
- [x] #3 Names the publish-model and evals/harness-extraction decisions as linked open decisions
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
ADR drafted as docs/decisions/0017-pointer-based-marketplace.md, PR #227 into dev (2026-08-03). Includes the owner's README ruling (readmes travel with skills; standalone-readmes/ dissolves — also folded into task-2 scope/AC). ADR 0008 marked Superseded-by-0017 (flow guard survives). AC #1 completes when the owner merges #227.
<!-- SECTION:NOTES:END -->
