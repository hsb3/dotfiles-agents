---
id: TASK-21
title: 'Extender database: remaining milestones M3-M6 + excalidraw follow-up'
status: To Do
assignee: []
created_date: '2026-08-04 00:43'
updated_date: '2026-08-06 21:33'
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
Epic for the remaining extender-database milestones. The database (`evals/`, PocketBase) maps every agent extender against jobs and mental models; Milestone 1 (coverage: 37 extenders x 24 jobs + relationships + generated matrix) is complete. Remaining, in two tracks — Track I (our IP): M3 curation (task-21.1). Track II (adopted eval): M4 judge+rubric formalization (task-21.2), M5 first with/without benchmark (task-21.3), M6 self-improvement loop (task-21.5) — plus the excalidraw residual-capability follow-up (task-21.4). Self-managing track: it runs from `evals/_structure/CHARTER.md` (roadmap + decisions 1-10), PLAN.md, PROCEDURES.md — do NOT fold into this repo's delivery planning. Standing rules for children: `primitives-core/` is the only edit surface for extender content; schema changes via `schema.py`; every DB-touching pass re-runs the gates; `data.db` commits with its cause and the server stopped. Secrets: `_meta/operations/extender-db.env`. Interacts with task-6 (evals extraction — deferred per decision-5; if evals/ ever moves out, this family moves with it). Substance carried in from closed GH epic #154 per decision-7.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Each child task (21.1, 21.2, 21.3, 21.4, 21.5) is Done with outcome notes, or explicitly descoped in the charter roadmap
- [ ] #2 `evals/_structure/CHARTER.md` roadmap shows M3-M6 delivered or descoped
<!-- AC:END -->
