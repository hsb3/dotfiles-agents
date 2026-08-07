---
id: TASK-16
title: 'Board tooling: confirm board-reporting coverage or file the gap'
status: Done
assignee:
  - '@claude'
created_date: '2026-08-04 00:43'
updated_date: '2026-08-07 00:47'
labels:
  - governance
milestone: m-3
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/211'
priority: low
type: chore
ordinal: 1600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Migrated from GH #211. Check whether the board-triage / github-project-board skills cover board reporting; file the gap if not. Re-scope note: with Backlog.md now managing this repo's tasks, the check applies to the DISTRIBUTED skills (for consumers on GH boards), not this repo's own workflow.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Coverage confirmed or gap filed as its own task
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verified 2026-08-07 by a cold read of both board skills' SKILL.md and references (assessor had not authored either). Verdict: GAP, not coverage. board-export.py produces a machine-readable snapshot (github-project-board/SKILL.md:262-267) but explicitly as triage input, not a readout; board-apply.py reports write pass/fail only; the sole status-shaped guidance (SKILL.md:241-246) delegates to GitHub UI views, which the skill's own capability matrix marks UI-only and unscriptable (SKILL.md:44, 213-215). The two skills divide cleanly with no overlap (board-triage/SKILL.md:19-21). Scope guard held: judged for a consumer on a GH board, not against this repo's Backlog.md workflow.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Answered the coverage question and filed the gap. Board reporting is NOT covered: both shipped board skills change a board, neither renders its state back out for a human. Snapshot tooling already exists (board-export.py); only the render layer is missing. Gap filed as TASK-041 with the evidence citations, satisfying this card's 'confirm coverage or file the gap' criterion.
<!-- SECTION:FINAL_SUMMARY:END -->
