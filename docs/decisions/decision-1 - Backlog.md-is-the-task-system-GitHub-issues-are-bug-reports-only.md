---
id: decision-1
title: Backlog.md is the task system; GitHub issues are bug reports only
date: '2026-08-04 00:44'
status: accepted
---
## Context

Owner ruling, 2026-08-03. Task management previously lived in GitHub issues with a pinned
triage issue (#192) as the ranked view, maintained by the foreman-kit waves loop. The owner
adopted Backlog.md in other projects (e.g. learn-pocketbase) and ruled to commit fully here.

## Decision

Backlog.md (this `backlog/` tree) is the sole task-management system for this repo. GitHub
issues are reserved for bug reporting — the intake channel. A reported bug gets a backlog
task (type `bug`) referencing the issue when the work is planned; the issue closes when the
fix ships.

## Consequences

- All 2026-08-03 open GH issues were migrated: tasks/drafts/decisions here, then closed with
  pointer comments. The three open bug reports (#172, #215, #222) stay open with work items
  task-22/23/24.
- The pinned triage issue #192 is closed and unpinned — the board (`backlog board`) replaces it.
- Governance docs and issue templates need the sweep (task-8). foreman-kit's waves skill
  assumes a GH-issue backlog; its backlog-aware mode is part of the same task.

