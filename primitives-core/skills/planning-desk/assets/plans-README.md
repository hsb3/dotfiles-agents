# _meta/plans

Build-ready planning docs — one subfolder per unit of work (`<slug>/plan.md`, plus any
screenshots/artifacts). The tracker holds STATE; this desk holds the build DETAIL.

This desk is **git-tracked** (`_meta/` is tracked by default), so the plans + `_utils/` scripts are
visible in a fresh clone, in worktrees, and in cloud sessions. A plan's tracking ref is the first
token in its `plan.md` `## Tracking` section that is a key on the tracker — the same rule the table
below is read by, so no ref syntax is baked into either.

See `_config.md` for THIS project's tracker binding, gate menu, and canonical docs to cite.

## Toolkit (`_utils/`)

Three dependency-free analysis scripts over a tracker snapshot + disk (never hand-maintained
state), each with `--json` and a non-zero exit on findings so it can gate a wave. Each reads the
tracker through an adapter in `_utils/adapters/`, or an already-exported `--snapshot FILE`:
`python3 _meta/plans/_utils/<script>`.

| Script | What it checks | Mutates? |
| ------ | -------------- | -------- |
| `reconcile.py` | plan-table rows vs tracker state vs disk folders vs `plan.md` Tracking | no |
| `conformance.py` | every open item body vs the task-authoring bar (acceptance + gates; close-when for epics) | no |
| `coverage.py` | open non-epic items with NO plan folder (the planning backlog) | writes a changeset TSV with `--changeset` |

The adapter is the only piece that talks to the tracker: `adapters/<name>.py export` writes a
snapshot, the scripts analyze it, and `adapters/<name>.py apply --changeset <file>` writes back —
dry-run until `--apply`.

## Status

The status tables below are hand-maintained, so they drift from live tracker state. Run
`python3 _meta/plans/_utils/reconcile.py` to cross-check every row against the tracker and the
folders on disk before trusting the table. It exits non-zero on any drift.

ACTIVE plans (associated with an OPEN item) — add a row per plan you draft:

| Plan | Tracker ref(s) | Status |
| ---- | -------------- | ------ |

> Example row (kept out of the table so a fresh desk reconciles clean):
> `| retry-backoff | xmwb | drafting |` — the ref cell holds the tracker's own key,
> plain or qualified (`myproject#xmwb`); a row that names no key on the tracker is drift.

ARCHIVED (item closed/merged; plan moved to `_meta/_archive/<ref>-<slug>.md`):

| Plan (archived path) | Tracker ref(s) | Why archived |
| -------------------- | -------------- | ------------ |

> Example row: `| _archive/p937-retry-backoff.md | p937 | shipped |` — an archived row whose ref
> is still open is drift too.

## The loop (how plans get produced)

A repeatable cycle: **draft in parallel** (one agent per plan, every claim cited to `path:line`) →
**review adversarially** against the rubric (a read-only verifier per plan, told to re-derive and
refute, run on your strongest model tier) → **fix** (handed the verified facts) → **augment the
rubric + re-review** → **apply and reconcile** (gate the wave on `reconcile.py` clean). Trust the
findings; treat any 1-5 scores as directional. A perfect sweep is a red flag, not a triumph.
