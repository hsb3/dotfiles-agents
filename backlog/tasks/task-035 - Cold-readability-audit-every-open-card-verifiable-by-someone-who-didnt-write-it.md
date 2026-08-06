---
id: TASK-035
title: >-
  Cold-readability audit: every open card verifiable by someone who didn't write
  it
status: To Do
assignee: []
created_date: '2026-08-06 21:33'
labels:
  - governance
dependencies: []
priority: medium
type: chore
ordinal: 13000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Carried over from milestone m-0, whose final unchecked commitment was: 'Every open card is cold-readable with verifiable acceptance criteria, assessed by someone who didn't write it.' m-0 closed on task completion without this being done, so it is tracked here rather than dropped.

A card is cold-readable when a session with no prior context can pick it up and know what done looks like. The independence requirement is the point: the assessor must not be whoever wrote the card, because the author cannot see their own missing context.

Scope is the open cards across m-1, m-2, and m-3.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every open card has acceptance criteria that state a checkable outcome, not an activity
- [ ] #2 Each card names the files, commands, or decisions a cold session needs to start
- [ ] #3 The assessment is done by an agent or session that did not author the card, and its findings are recorded per card
- [ ] #4 Cards that fail the audit are either rewritten or explicitly dropped
<!-- AC:END -->
