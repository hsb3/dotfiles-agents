---
id: TASK-044
title: 'Decide: can Claude Code hooks be translated to opencode at all?'
status: To Do
assignee: []
created_date: '2026-08-07 01:10'
updated_date: '2026-08-10 02:26'
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
Split from TASK-033 (owner ruling 2026-08-07) so the mechanical silent-subset fix isn't blocked on this open question. Today the opencode laydown ships skills and agents, no hooks, with nothing stating whether that's a deliberate limit or an unfinished feature.

This is an investigation, not a build: establish whether opencode has a lifecycle-event surface comparable to Claude Code's hooks; if so, which of this repo's shipped hook events have a counterpart and which don't; and for any without one, whether the gap is opencode's or an artifact of how these hooks are written. Start from the opencode-expertise skill's existing surface mapping. "No, and here is the specific reason" is a complete, successful outcome. Sequenced behind Claude Code, same as TASK-033.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A recorded decision states whether hooks can be translated to opencode, with reasoning, in a durable location — not a task comment
- [ ] #2 If yes: the event-by-event mapping is stated, including any shipped hook event with no counterpart
- [ ] #3 If no or partial: the specific blocking reason is named, so the question isn't reopened from scratch
- [ ] #4 translation.yaml and the installer's user-facing disclosure agree with the recorded answer
<!-- AC:END -->
