---
name: planning-desk
description: >-
  Stand up and run a source-grounded planning desk under _meta/plans/ - deep build plans driven
  through a multi-round draft -> review -> fix -> reconcile loop over a tracker read through a
  pluggable adapter, plus analysis scripts for conformance, coverage, and reconciliation. Use
  whenever the user wants to plan a feature or epic before building, run a planning or
  backlog-grooming session, organize work under _meta/plans/, audit plan/tracker drift, or set the
  desk up in a repo - even phrased as "plan this out", "groom the backlog", or "get this repo's
  planning organized". It enforces deliverables/criteria/parallelism (never timelines) and grounds
  every claim in cited source. Not for writing the body of a tracked work item (task-authoring),
  not for creating a repo's meta-structure or filling audit gaps (mise-en-place-scaffold), and not
  the layout standard itself (repo-meta-structure).
---

# Planning desk

Turn fuzzy intent into build-ready, source-grounded plans on a local `_meta/plans/` desk, over a
tracker read through a pluggable adapter. **The tracker holds STATE and the contract; the desk
holds the build DETAIL.**

```
_meta/plans/
  README.md        # the live ACTIVE / ARCHIVED status index
  _config.md       # THIS project's gates, tracker binding, canonical docs
  _utils/          # tracker.py loader + adapters/ + conformance, coverage, reconcile
  <slug>/plan.md   # the build plan - and nothing else
```

## Pick the mode

| If the user wants to...                         | Mode       | Read                    |
| ----------------------------------------------- | ---------- | ----------------------- |
| set up the desk in a repo that lacks one        | **setup**  | Setup, below            |
| produce a deep, source-grounded build plan      | **plan**   | `references/plan.md`    |
| run a multi-round planning session over a batch | **loop**   | `references/loop.md`    |
| groom the backlog, audit drift, gate a wave     | **govern** | `references/toolkit.md` |

**For the body of a tracked work item - title, acceptance criteria, thresholds, scope - use the
`task-authoring` skill**; its rules are not restated here. Desk absent? Set up first, then
proceed. `references/entry-forms-and-milestones.md` carries the queue-entry forms and the
milestone/gate vocabulary a board speaks.

## First, always: orient

1. **Confirm a tracker adapter resolves** - `references/adapters/contract.md` is the
   backend-neutral snapshot/changeset contract, `references/adapters/kata.md` the shipped backend.
   Without one, plan mode still helps but govern mode will not run.
2. **Check for the desk**; if `_meta/plans/_config.md` exists read it for this project's gates
   before authoring, if not you're in setup.
3. **Run from the main working tree**, where the tracker CLI is configured - not a bare worktree.

## Setup

1. `mkdir -p _meta/plans/_utils/adapters`; copy `tracker.py`, the three analysis scripts, and
   `adapters/` out of `scripts/_utils/`, and `assets/plans-README.md` to `_meta/plans/README.md`
   (its `ACTIVE plans` / `ARCHIVED (` markers are parsed - keep them). No install.
2. Keep the desk tracked: `_meta/` is tracked by default (ADR-0006), so add only
   `_meta/plans/_utils/__pycache__/`, and secrets-scan whatever a removed broad `_meta/` ignore
   newly exposes before committing.
3. Write `_meta/plans/_config.md` from `assets/_config.template.md` - the step that makes the desk
   portable. Investigate, don't assume: this repo's real gates and drift guards, the canonical
   docs a plan must cite, which tracker it is bound to. `TODO(owner):` what you could not resolve.
4. Confirm it runs (`reconcile.py` reconciles an empty desk clean, `conformance.py` audits live
   item bodies), then report what you scaffolded and every `TODO(owner):` gap.

## The non-negotiables (every mode)

- **Cite `path:line` for every load-bearing claim, never a stale checklist** - the backlog is
  mostly partly-shipped and its framing routinely wrong, so state the true residual.
- **Subagent findings are hypotheses** - re-derive from source anything that would move a plan's
  core recommendation; right-citation/wrong-mechanism is the classic failure.
- **Deliverables, acceptance criteria, parallelism - NEVER timelines**, and criteria are checkable
  by someone who didn't write the code, not "works well".
- **Keep genuine owner decisions OPEN** as numbered questions, each with a recommended default.
- **Outward-facing actions get confirmation** - the desk is free, a live tracked item is
  publishing: present it, get approval, push that one item.
- **ASCII-only inside table cells**, and no literal `|` in a cell.

## The toolkit at a glance

Three read-only analysis scripts over one adapter, each with `--json` and a non-zero exit on
findings, so any one can gate a wave. Detail and conventions: `references/toolkit.md`.

| Piece                | Answers                                                                       |
| -------------------- | ----------------------------------------------------------------------------- |
| `adapters/<name>.py` | the tracker adapter - `export` a snapshot, `apply` a changeset (dry-run first) |
| `conformance.py`     | does every open item body carry acceptance criteria and its gates section?     |
| `coverage.py`        | which open non-epic items have NO plan folder? (the planning backlog)          |
| `reconcile.py`       | do the README rows agree with live tracker state and the folders on disk?      |
