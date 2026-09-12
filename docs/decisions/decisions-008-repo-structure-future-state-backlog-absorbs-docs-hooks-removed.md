---
id: decision-008
title: Repo structure future-state — backlog absorbs docs/, _meta removed
date: '2026-08-06'
status: accepted (partly superseded by decision-011 and decision-014)
---

> **Amendment note (2026-09-09):** Decision-011 returned documentation to `docs/` when Backlog.md retired; decision-014 later moved task tracking to kata. The `_meta/` removal remains repo policy. Historical `backlog/` paths below are provenance, not current navigation.

## Context

The 2026-08-06 cleanup removed the empty top-level `hooks/` placeholder and dissolved
`docs/` into the backlog: the ADR mirrors moved to `backlog/decisions/` (beside the
`decision-N` series), and the extender-dev SOP, `FLOW.md`, and `vendoring-rule.md` to
`backlog/docs/`. Backlog.md was already THE task system (decision-1); this makes
`backlog/` the decision and working-docs home too. `backlog/config.yml` carries
`harness` / `evals` area labels so those workbenches' work is tracked in the same backlog.

## Decision (owner sign-off 2026-08-06; all items approved as recommended, `_meta`
removal strengthened by the owner from "wind down" to "remove entirely")

Top level converges to five groups, every path homed in `flow.yaml`:

- **sources** — `primitives-core/` + `primitives-core.yaml` + `externals.yaml` +
  `translation.yaml`
- **distribution** — `plugins/` + `.claude-plugin/`
- **toolchain + gates** — `scripts/`, `tests/`, `Makefile`, `flow.yaml`, `.github/`
- **workbenches** — `backlog/`, `harness/`, `evals/`, `.claude/`
- **entry docs** — `README.md`, `AGENTS.md`, `CLAUDE.md`

`_meta/` is **removed entirely** (supersedes ADR 0006's tracked-desk policy for this
repo): secrets/live-ops live in untracked `.claude/operations/`; future briefings will go
to a separate meta-planning directory where project design considerations are handled
(created when needed); the harness design docs travel with their component
(`harness/docs/`, ex `_meta/research/agent-harness/`); everything else lives in git
history. New planning work starts as backlog tasks and docs, not desk folders.

The published repo-meta-structure checklist was amended under the same sign-off: META-06
accepts the handoff hooks' three precedence paths, DOCS-03..05 accept
`backlog/decisions/` as the ADR home, and IGNORE-05 follows the handoff's actual path.
This repo's remaining divergence from the `_meta` taxonomy (META-01..05, META-07) is
deliberate; the taxonomy stays available for repos that use the desk convention.

## Consequences

- Historical records (ADR bodies, completed task cards, archived trails) keep their
  original path citations; they resolve through git history.
- Harness/evals extraction (decision-5, task-6) is unchanged — still deferred.
- `backlog/docs/FLOW.md`'s hand-authored homes table predates parts of this change;
  task-7 owns the refresh.
- The comms skill's briefing-output convention (`_meta/briefings/`) needs a new home in
  this repo once the meta-planning directory exists.
