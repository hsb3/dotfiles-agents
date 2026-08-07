---
id: TASK-047
title: board-triage names a board-analyst agent that does not exist
status: To Do
assignee: []
created_date: '2026-08-07 01:52'
labels:
  - primitives
milestone: m-1
dependencies: []
priority: medium
type: bug
ordinal: 26000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found 2026-08-07 during the standalone-eligibility inventory, verified independently twice.

primitives-core/skills/board-triage/SKILL.md:68-69 documents a hand-off variant for harnesses where listing board items overflows the context: 'the local side runs board-export, the **board-analyst** agent (this plugin) produces the changeset from the snapshot + repo plans, and the local side runs board-apply.'

There is no board-analyst agent. The roster carries exactly four agents — scout, builder, reviewer, and manager (renamed from lead 2026-08-07) — and a grep across primitives-core.yaml and every plugin assembly returns nothing for board-analyst.

The parenthetical is what makes this a defect rather than a loose reference: '(this plugin)' asserts the agent ships alongside the skill. A consumer hitting the exact situation the section is written for — a harness that cannot list the board — follows the instruction and finds nothing to dispatch. The failure lands on the user precisely when the normal path has already failed them.

Two possible fixes, and the choice is a real one rather than a formality. Either the agent was intended and never built, in which case the hand-off variant has never worked and the section describes a feature that does not exist; or the wording is stale from an earlier design, in which case the section should describe the hand-off in terms of whatever actually performs it (any capable agent given the snapshot, most likely) and drop the invented name.

Adjacent finding from the same pass, worth fixing here or separately: board-triage also references a sibling skill BY PATH at SKILL.md:31 — S="${CLAUDE_PLUGIN_ROOT}/skills/github-project-board/scripts". That breaks if the sibling is not installed, and it is one of the two reasons board-triage is not standalone-eligible.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Determine whether board-analyst was ever built; the answer is recorded either way
- [ ] #2 The hand-off variant either names an agent that exists, or describes the hand-off without naming a nonexistent one
- [ ] #3 No shipped skill body names an agent absent from the roster — checked by grep across all skills, not just this one
- [ ] #4 Consider a gate: a shipped body naming an agent id that is not in the roster should fail, since this class of defect is invisible until a user hits it
<!-- AC:END -->
