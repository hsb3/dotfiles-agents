---
id: TASK-062
title: kaneo brownfield adoption skill - move existing in-repo work onto a board
status: To Do
assignee: []
created_date: '2026-08-11 08:20'
labels:
  - primitives
milestone: m-2
dependencies:
  - TASK-061
priority: medium
type: feature
ordinal: 41000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A repo that already tracks work in TODO.md, backlog.md, a Backlog.md project, or GitHub issues cannot adopt the kaneo skill today: the skill says 'the board replaces in-repo task files' and 'never create backlog.md or TODO files', but it gives no procedure for the work already sitting in those files. Adoption is therefore a manual, ad-hoc migration every time, and in practice the two systems run in parallel until one rots.

This card is the adoption half of the pair (see the provisioning card for standing up a NEW board). Scope is a repo that already has a Kaneo project and needs its existing tracked work moved onto it.

The skill should cover: inventory what the repo currently tracks and where; decide what actually migrates vs what is dead and gets dropped; search the board first so re-runs do not duplicate; create tasks whose bodies are actionable with no conversation context (the kaneo skill already requires this); preserve status and priority where the source carries them; and retire the in-repo files rather than leaving them to drift alongside the board.

Trigger phrasing to design for: 'adopt kaneo in this repo', 'move our TODOs onto the board', 'we track work in backlog.md, switch us to kaneo'.

Open questions for whoever picks this up: whether it handles GitHub issues at all (this repo's own convention treats issues as bug intake only, which may or may not generalise), and whether retiring the in-repo files means deleting them or leaving a tombstone pointing at the board.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The skill names its sources explicitly - which in-repo formats it can read and which it refuses - rather than promising to handle 'existing task files' generically
- [ ] #2 Re-running the adoption on a partly-migrated repo creates no duplicate board tasks
- [ ] #3 The skill leaves the repo in one state, not two: the in-repo tracking files are retired or tombstoned, never left live alongside the board
- [ ] #4 It ships with the kaneo plugin assembly and carries a per-primitive README per primitives-core/README.md
- [ ] #5 make ci exits 0 including the identity lint and the solo-skills membership gate (which must agree with wherever the skill is or is not homed)
<!-- AC:END -->
