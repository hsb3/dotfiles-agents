---
id: TASK-056
title: >-
  atelier: the delegation watermark fires hardest during the phase where solo
  work is correct
status: To Do
assignee: []
created_date: '2026-08-10 02:46'
labels:
  - primitives
milestone: m-2
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/281'
priority: medium
type: bug
ordinal: 35000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The watermark counts un-delegated execution by the strategist without excluding the never-delegated floor — the work doctrine says the session must keep. Triage, the merge decision, the handoff, and closeout are floor work by design, so the nudge is loudest exactly when the session is doing the right thing, and an operator learns to dismiss it.

A signal that fires on correct behavior stops being read, which costs more than the signal was worth. Either the floor is excluded from the count, or acknowledging the nudge suppresses it for the phase.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Work that doctrine assigns to the never-delegated floor does not raise the watermark
- [ ] #2 The distinction is derived from something observable at hook time, not from the model self-reporting which phase it is in
- [ ] #3 A test covers a floor-only session and asserts the watermark stays silent, and a genuinely under-delegated session and asserts it fires
<!-- AC:END -->
