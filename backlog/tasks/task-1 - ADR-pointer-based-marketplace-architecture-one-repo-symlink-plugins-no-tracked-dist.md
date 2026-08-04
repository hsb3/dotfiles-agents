---
id: TASK-1
title: >-
  ADR: pointer-based marketplace architecture (one repo, symlink plugins, no
  tracked dist)
status: To Do
assignee: []
created_date: '2026-08-04 00:41'
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
- [ ] #1 ADR drafted in docs/decisions/ and approved by owner
- [ ] #2 Covers: symlink mechanism + install-time materialization, one-repo two-target ruling, tripwires for a future repo split
- [ ] #3 Names the publish-model and evals/harness-extraction decisions as linked open decisions
<!-- AC:END -->
