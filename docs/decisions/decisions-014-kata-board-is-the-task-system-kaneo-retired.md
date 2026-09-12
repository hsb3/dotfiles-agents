---
id: "decision-014"
title: kata board is the task system; Kaneo board retired
date: '2026-09-02'
status: accepted
---
## Context

Owner ruling, 2026-09-02: "ensure this repo is fully transitioned to kata for task
management; close/delete any prior kaneo project; all incomplete work on the kata board."
The kata project `dotfiles-agents` already existed (bound by `.kata.toml`, GitHub sync on)
and held every GitHub-mirrored task; the Kaneo board DFA still held 48 open tasks that had
never reached GitHub (the pre-mirror TASK-/DRAFT-/Milestone cards).

## Decision

The kata board is the sole task-management system for this repo. GitHub issues remain bug
intake only (the surviving rule from decision-1, now decision-014) and flow onto the board through kata's GitHub sync.

Cutover, executed 2026-09-02:

- The 48 Kaneo-only open tasks were imported (kaneo-to-kata importer, `--only-numbers`),
  with `kaneo_*` metadata and a `kaneo-status:<lane>` label.
- The 54 open Kaneo tasks that already existed on kata via the GitHub mirror were stamped
  with the same metadata and label instead of duplicated; four of them were already closed on
  kata/GitHub, so Kaneo was stale, not kata.
- Kaneo's 100 closed tasks (Done + Documents lanes) were not imported: the Documents lane
  mirrored `docs/decisions/`, and Done history stays readable on the archived board.
- Kaneo's GitHub integration for this repo was deactivated, then project DFA was archived
  (not deleted); the `KANEO_*` values left `.claude/settings.local.json`.
- The session handoff is kata issue `8xyk` (mirror of GitHub #329), no longer Kaneo DFA-233.

## Consequences

- Supersedes former decision-011's Kaneo half; its Backlog.md retirement and bug-intake rule stand.
- Old `DFA-N` references resolve via `kata list --meta kaneo_task_number=N`.
- The shipped `kaneo` plugin and its primitives are unaffected — they are a product this
  marketplace distributes, not this repo's tracker.
