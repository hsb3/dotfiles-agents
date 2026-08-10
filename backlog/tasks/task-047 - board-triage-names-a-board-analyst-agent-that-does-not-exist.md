---
id: TASK-047
title: board-triage names a board-analyst agent that does not exist
status: To Do
assignee: []
created_date: '2026-08-07 01:52'
updated_date: '2026-08-10 02:25'
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
primitives-core/skills/board-triage/SKILL.md:68-69 documents a hand-off variant for harnesses that can't list board items: the local side runs board-export, a "board-analyst" agent produces the changeset, the local side runs board-apply. That agent doesn't exist — the roster has four agents (scout, builder, reviewer, manager) and board-analyst appears nowhere in primitives-core.yaml or any plugin assembly.

The parenthetical "(this plugin)" claims the agent ships with the skill. A consumer hitting exactly the situation this section is written for — a harness that can't list the board — follows the instruction and finds nothing to dispatch.

Fix either by building the agent, or by rewriting the section to describe the hand-off without inventing a name (most likely: any capable agent given the snapshot).

Adjacent finding, same pass: board-triage also references a sibling skill by path at SKILL.md:31 (`S="${CLAUDE_PLUGIN_ROOT}/skills/github-project-board/scripts"`), which breaks if the sibling isn't installed — one of two reasons board-triage isn't standalone-eligible. Fix here or split out.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Determine whether board-analyst was ever built; record the answer either way
- [ ] #2 The hand-off variant either names an agent that exists, or describes the hand-off without naming a nonexistent one
- [ ] #3 No shipped skill body names an agent absent from the roster — checked by grep across all skills, not just board-triage
- [ ] #4 Consider a gate that fails when a shipped body names an agent id not in the roster, since this defect class is invisible until a user hits it
<!-- AC:END -->
