---
id: TASK-21
title: 'Extender database: remaining milestones M3-M6 + excalidraw follow-up'
status: To Do
assignee: []
created_date: '2026-08-04 00:43'
updated_date: '2026-08-10 02:24'
labels:
  - evals
milestone: m-3
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/154'
priority: medium
type: feature
ordinal: 1100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Epic for the remaining extender-database milestones. `evals/` (PocketBase) maps every agent extender against jobs and mental models; M1 (37 extenders x 24 jobs, coverage matrix) is complete. Two tracks remain: Track I (our IP) — M3 curation (TASK-21.1). Track II (adopted eval) — M4 judge+rubric formalization (TASK-21.2), M5 first with/without benchmark (TASK-21.3), M6 self-improvement loop (TASK-21.5) — plus the excalidraw residual-capability follow-up (TASK-21.4).

This track is self-managing: it runs from `evals/_structure/CHARTER.md` (roadmap + decisions), `PLAN.md`, `PROCEDURES.md` — do not fold into this repo's delivery planning. Standing rules for every child: `primitives-core/` is the only edit surface for extender content; schema changes go through `schema.py`; every DB-touching pass re-runs the gates; `data.db` commits with its cause, server stopped first. Secrets live in `_meta/operations/extender-db.env`. Relates to TASK-6 (evals extraction, deferred) — if `evals/` ever moves out of this repo, this family moves with it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every child task (TASK-21.1 through TASK-21.5) is Done with outcome notes, or explicitly descoped in the charter roadmap
- [ ] #2 `evals/_structure/CHARTER.md` roadmap shows M3-M6 delivered or descoped
<!-- AC:END -->
