---
id: TASK-044
title: 'Decide: can Claude Code hooks be translated to opencode at all?'
status: To Do
assignee: []
created_date: '2026-08-07 01:10'
labels:
  - distribution
milestone: m-1
dependencies: []
priority: low
type: spike
ordinal: 23000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Split out of TASK-033 by owner ruling 2026-08-07, so the mechanical silent-subset fix is not blocked behind an unanswered design question.

TASK-033's AC#4 required that 'whether hooks can be translated to opencode at all is decided and the answer is recorded in the repo, not left implied'. Today it is implied only by their absence: the opencode laydown ships skills and agents, no hooks, and nothing states whether that is a deliberate limit or an unfinished feature. A reader cannot tell which.

This card answers that question and records the answer. It is an investigation, not a build — the deliverable is a recorded decision with its reasoning, whatever the answer turns out to be. 'No, and here is the specific reason' is a complete and successful outcome.

What it has to establish: whether opencode has a lifecycle-event surface at all comparable to Claude Code's hook events; if it does, which of this repo's shipped hook events have a counterpart and which do not; and for anything without a counterpart, whether the gap is opencode's or an artifact of how these hooks are written. The opencode-expertise skill in this repo already maps Claude Code surfaces to opencode ones and is the natural starting point.

Sequenced behind Claude Code per the owner's standing direction, same as its parent card.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A recorded decision states whether hooks can be translated to opencode, with the reasoning, in a durable location rather than a task comment
- [ ] #2 If yes: the event-by-event mapping is stated, including any shipped hook event with no counterpart
- [ ] #3 If no or partial: the specific blocking reason is named, so a future session does not re-open the question from scratch
- [ ] #4 translation.yaml and the installer's user-facing disclosure agree with the recorded answer
<!-- AC:END -->
