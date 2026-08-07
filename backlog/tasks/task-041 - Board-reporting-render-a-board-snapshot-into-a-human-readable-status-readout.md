---
id: TASK-041
title: 'Board reporting: render a board snapshot into a human-readable status readout'
status: To Do
assignee: []
created_date: '2026-08-07 00:46'
labels:
  - primitives
milestone: m-2
dependencies: []
priority: low
type: feature
ordinal: 20000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Gap confirmed 2026-08-07 by a cold read of both board skills (closes the question TASK-16 asked). Neither shipped skill turns board state back into something a person reads.

github-project-board owns setup and mechanics; board-triage owns the weekly prioritization routine. They divide cleanly with no overlap (board-triage/SKILL.md:19-21 states it does not redefine the other). Neither claims reporting, and neither README mentions it.

What exists today stops one step short. board-export.py (github-project-board/SKILL.md:262-267) already produces a compact JSON snapshot of project/fields/items, but it is explicitly machine input for triage judgment (SKILL.md:253-255), not a readout. board-apply.py (SKILL.md:273-276) reports per-cell pass/fail on writes, which is write-confirmation, not board state. The only status-shaped guidance is the operating cadence at SKILL.md:241-246 ('Daily: open the focus view...'), which delegates reporting to GitHub's UI views — and the skill's own capability matrix classifies Views as UI-only and unscriptable (SKILL.md:44, SKILL.md:213-215). So the documented API surface cannot produce a scripted readout at all; the skill hands that job to manual eyeballing.

Consequence for a consumer: to answer 'what is the state of my board' they either read the Roadmap/board views by eye in the GitHub UI, or run board-export.py and parse raw JSON themselves. The snapshot half is already built and reusable; only the render layer is missing.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A documented procedure or script takes a board-export.py snapshot and renders a human-readable status summary, without re-querying the API
- [ ] #2 The readout covers at least: counts per Status and per Priority, items currently Blocked, and what reached Done since a given date
- [ ] #3 It consumes board-export.py's existing output shape rather than defining a second snapshot format
- [ ] #4 Which skill owns the render layer (github-project-board vs board-triage) is decided and stated, consistent with the existing division of labor between them
<!-- AC:END -->
