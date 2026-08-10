---
id: TASK-057
title: >-
  Hooks have no shared log identity: one partitioned root, one envelope, one
  append helper
status: To Do
assignee: []
created_date: '2026-08-10 02:46'
labels:
  - primitives
milestone: m-3
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/290'
priority: medium
type: feature
ordinal: 36000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Each hook invents its own logging. They disagree on where rows land, what a row looks like, and whether anything is written at all — `primitives-core/hooks/worktree-isolation/hook.py` logs nothing (grep for log/jsonl returns empty), so the one hook that silently rewrites a dispatch leaves no record that it did.

That makes cross-hook analysis a per-file exercise and blocks the measurement work generally: a ledger you have to normalize before reading is a ledger nobody reads. The scheme is already worked out on the opencode side per the issue — this card is the port, not a new design.

Two constraints that are easy to lose. Hooks stay stdlib-only and zero-install. And `logs/delegation.jsonl` history before 2026-08-07 is not trustworthy — it inflates the parent session and uses the pre-rename `lead` label — so any migration must truncate rather than reinterpret.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 All hooks append through one helper rather than each writing its own rows
- [ ] #2 Rows share one envelope, with a timestamp format that sorts and parses without per-consumer handling
- [ ] #3 Log location is one partitioned root, and a reader can find every hook log without knowing which hook wrote it
- [ ] #4 The worktree-isolation hook records the dispatches it rewrites and the ones it leaves alone
- [ ] #5 The helper is stdlib-only and the hooks still run with zero install
- [ ] #6 Pre-2026-08-07 delegation rows are truncated or quarantined rather than migrated into the new envelope
<!-- AC:END -->
