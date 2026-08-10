---
id: TASK-055
title: >-
  atelier: dispatch preconditions check that a gate exists, not that it covers
  the change
status: To Do
assignee: []
created_date: '2026-08-10 02:45'
labels:
  - primitives
milestone: m-2
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/283'
priority: medium
type: feature
ordinal: 34000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The pre-dispatch preconditions are structural and one-time: they confirm a gate is named and a brief is scoped. Two things they never re-check, both reported from the field:

1. The brief premise may have gone stale between writing and dispatch. Another worker landing first, or the strategist editing the tree, can invalidate the reading the brief was built on, and the worker discovers it mid-flight or not at all.
2. A named gate may not actually exercise the change. A gate that exists and passes proves nothing if the diff sits outside what it reads — the standing example in this repo is `check_symlinks` standalone-README rule, green with zero real subjects.

Distinct from the liveness cluster: that one is about a worker that never finishes, this one is about a worker that finishes against a contract that was already wrong. Both were reported the same night, which is why they are easy to conflate.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The preconditions require the dispatcher to re-derive the brief premise against the current tree at dispatch time, not at authoring time, and say what to do when it has moved
- [ ] #2 A named gate must be shown to have the change in its subject set — a gate that would pass identically with and without the diff does not satisfy the precondition
- [ ] #3 The rule distinguishes a gate that passes from a gate that has subjects, and gives the check an agent runs to tell them apart
<!-- AC:END -->
