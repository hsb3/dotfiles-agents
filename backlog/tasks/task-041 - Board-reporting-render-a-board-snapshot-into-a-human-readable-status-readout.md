---
id: TASK-041
title: 'Board reporting: render a board snapshot into a human-readable status readout'
status: To Do
assignee: []
created_date: '2026-08-07 00:46'
updated_date: '2026-08-10 02:26'
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
Gap confirmed 2026-08-07 by a cold read of both board skills (closes the question TASK-16 asked): neither shipped skill turns board state back into something a person reads.

github-project-board owns setup/mechanics; board-triage owns weekly prioritization. Clean split, no overlap (board-triage/SKILL.md:19-21), and neither claims reporting.

board-export.py (github-project-board/SKILL.md:262-267) produces a compact JSON snapshot of project/fields/items, but it's machine input for triage judgment (SKILL.md:253-255), not a readout. board-apply.py (SKILL.md:273-276) reports per-cell pass/fail on writes — write-confirmation, not board state. The operating cadence at SKILL.md:241-246 ("Daily: open the focus view...") delegates reporting to GitHub's UI Views, which the skill's own capability matrix classifies as UI-only and unscriptable (SKILL.md:44, SKILL.md:213-215). The documented API surface can't produce a scripted readout; it hands that job to manual eyeballing.

Consumers today either eyeball the Roadmap/board views in the GitHub UI or run board-export.py and parse raw JSON themselves. The snapshot half is built and reusable; only the render layer is missing.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A documented procedure or script renders a board-export.py snapshot into a human-readable status summary without re-querying the API
- [ ] #2 The readout covers at minimum: counts per Status and per Priority, items currently Blocked, and what reached Done since a given date
- [ ] #3 It consumes board-export.py's existing output shape rather than defining a second snapshot format
- [ ] #4 Render-layer ownership (github-project-board vs board-triage) is decided and stated, consistent with their existing division of labor
<!-- AC:END -->
