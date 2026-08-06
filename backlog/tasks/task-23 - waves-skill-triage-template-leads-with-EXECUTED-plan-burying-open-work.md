---
id: TASK-23
title: 'waves skill: triage template leads with EXECUTED plan, burying open work'
status: Done
assignee: []
created_date: '2026-08-04 00:44'
updated_date: '2026-08-06'
labels:
  - foreman-kit
  - waves
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/215'
priority: medium
type: bug
ordinal: 900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Work item for GH bug #215 (stays open as the report; close on fix). Reorder the seeded template + Phase 2/6 rules so open work leads and executed plans collapse into a history block; add the every-issue-appears-once invariant. Product fix for consumers running waves on GH-issue repos.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Template + Phase 2/6 edits shipped in waves SKILL.md
- [x] #2 GH #215 closed on merge
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Fixed in `primitives-core/skills/waves/SKILL.md`: (1) `/waves init` template reordered — open-work sections lead (Now section gains a `# | Title | State | Blocked by` table), delivery plans moved to a trailing `# Delivery history — shipped, provenance only` block; (2) Phase 6 now moves the just-executed plan below the open sections and collapses it in `<details>` (not just prior plans); (3) Phase 2 names where a PLANNED plan is written (history block, expanded while PLANNED, collapsed on EXECUTED); (4) Maintenance protocol carries the structure rule + every-issue-appears-once invariant as standing invariants. foreman-kit bumped to 0.7.1. GH #215 closed by hand after merge per the bug-intake convention.
<!-- SECTION:NOTES:END -->
