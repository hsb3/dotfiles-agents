---
title: Project SOPs — the harness-agnostic process layer
status: active
created: 2026-07-01
---

# Project SOPs

Repeatable, **harness-agnostic** standard operating procedures for setting up and running a
software project. Each SOP is the *process* — the principles and steps, written to hold for any
project and any coding-agent harness (Claude Code, opencode, or otherwise). An **extender** in
this repo delivers each one as a runnable capability; skills render into every target harness, so
the same process works everywhere.

**Read the SOP for the *why* and the shape; invoke the extender for the *doing*.**

| SOP | What it standardizes | Delivered by |
| --- | --- | --- |
| [`milestones-and-board.md`](./milestones-and-board.md) | One project board + milestones as the single source of truth for work state | `github-project-board` (+ `board-reporting`, `board-triage`) |
| [`issues-and-plans.md`](./issues-and-plans.md) | How units of work become conformant issues + build-ready plans | `planning-desk` |
| [`session-continuity.md`](./session-continuity.md) | Making every agent session clearable via a durable handoff file | `handoff` |

## Design rules these SOPs share

- **Harness-neutral.** No step depends on one harness's memory, compaction, resume, or slash-command
  surface. State lives in files and in the board — both readable by any agent.
- **No personal or project names.** These are liftable into any repo unchanged.
- **The board and the repo are the single source of truth for work state.** Local planning desks
  hold *detail and rationale*; they never fork a parallel backlog.
- **Deliverables · acceptance criteria · parallelism — never timelines.** Owner deadlines are
  recorded as constraints, not schedules.
- **Externalize load-bearing state.** Nothing important lives only in an agent's context window.
