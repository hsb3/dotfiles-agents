---
id: decision-011
title: Kaneo board is the task system; Backlog.md retired
date: '2026-08-11'
status: superseded
---
> **SUPERSEDED 2026-09-02 by decision-014** — the kata board replaced the Kaneo board.
> The issues-are-bug-intake half and the Backlog.md retirement stand; everything Kaneo-specific here is history.

## Context

Owner ruling, 2026-08-11, delivered in-session in two parts: migrate this repo onto the
Kaneo board (the last of the fleet, held back because it was the most Backlog-coupled),
and "retire all backlog.md related items" rather than repointing them at the board.

The repo's 101 backlog items (74 tasks, 8 drafts, 19 decisions) were imported to project
DFA / dotfiles-agents (`l2k5zzte5qo9amu79tr8e6iy`, workspace hsb3) and verified by
re-export against source markers — including a wipe-and-reimport after the first pass
was found to drop every acceptance-criteria section (importer fix: kaneo 0.9.1). The
three active milestones were converted to board tasks by hand, since Kaneo has no
milestone primitive.

## Decision

The Kaneo board is the sole task-management system for this repo. GitHub issues remain
bug intake only — that half of decision-1 survives unchanged. The Backlog.md tooling is
retired: the CLI workflow block in AGENTS.md, the `check_backlog_labels` gate, the
`backlog/` tree, and the project-manager-backlog agent. Standing law that lived under
`backlog/` (FLOW.md, the vendoring rule, the diagram standard, these decision records)
is rehomed to `docs/`, which the flow DAG homes as `repo-law`.

Board workflow — claim ritual, levels, label vocabulary, decision handling — is the
`kaneo` skill's law, not this repo's; AGENTS.md points at it and adds nothing.

## Consequences

- Supersedes decision-1's Backlog.md half; its issues-are-bug-intake half is restated
  above and stays in force.
- Decisions are now recorded here as plain files (this record is the first) and mirrored
  to the board's Document lane; the file is authoritative.
- The closed label vocabulary and per-board conventions live on the meta workspace's
  migration board, shared by every migrated repo, instead of per-repo config.
- Session credentials are the five KANEO_* values in gitignored
  `.claude/settings.local.json`; the repo operates as the `dotfiles-agents` agent
  account, never the owner identity.
