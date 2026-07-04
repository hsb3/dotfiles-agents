# _meta/plans

Build-ready planning docs — one subfolder per unit of work (`<slug>/plan.md`, plus
`<slug>/issue-body.md` and any screenshots/artifacts). The board tracks STATE; this desk holds the
build DETAIL.

This desk is **git-tracked** (negated in `.gitignore`), so the plans + `_utils/` scripts are visible
in a fresh clone, in worktrees, and in cloud sessions; the rest of `_meta/` stays local. A plan's
tracking issue is the first `#NNN` in its `plan.md` `## Tracking` section.

See `_config.md` for THIS project's gate menu, issue-template sections, and canonical docs to cite.

## Toolkit (`_utils/`)

Seven dependency-free scripts, each a generated VIEW over `gh` + disk (never hand-maintained state),
each with `--json` and a non-zero exit on findings so it can gate a wave. Run them from the main tree
where `gh` is authed: `python3 _meta/plans/_utils/<script>`.

| Script | What it checks | Mutates? |
| ------ | -------------- | -------- |
| `reconcile.py` | plan-table rows vs live issue state vs disk folders vs `plan.md` Tracking | no |
| `conformance.py` | every open issue body vs its `.github/ISSUE_TEMPLATE` required sections | no |
| `coverage.py` | open non-epic issues with NO plan folder (the planning backlog) | no |
| `sequence.py` | tiers ALL open issues into NOW / NEXT / BLOCKED / DEFERRED | no |
| `deps-suggest.py` | candidate native blocked-by edges harvested from prose `#refs` (advisory) | no |
| `sync-bodies.py` | each folder's `issue-body.md` vs the live GitHub body | only `--push`/`--pull` |
| `evidence-audit.py` | recently-closed issues that closed with no linked PR and no evidence | no |

## Status

The status tables below are hand-maintained, so they drift from live issue state. Run
`python3 _meta/plans/_utils/reconcile.py` to cross-check every row against GitHub and the folders on
disk before trusting the table. It exits non-zero on any drift.

ACTIVE plans (associated with an OPEN issue) — add a row per plan you draft:

| Plan | Issue(s) | Status |
| ---- | -------- | ------ |
| project-workflow-v2 | #27 | drafted 2026-07-03; design of record on the cowork desk; owner decisions 1-6 open |
| retire-hsb3-custom-plugins | #32 | drafted 2026-07-03; symlink half already shipped, residual = 16-command disposition + CLI retirement; decisions 1-6 open |
| raptorgpt-pilot | #33 | drafted 2026-07-03; pilot ran 2026-07-02 (rgpt#541), residual = round-2 close-out + vault sign-off; decisions 1-6 open |
| externals-clone-at-build | #36 | drafted 2026-07-03; 36 entries, 31 null upstreams; decisions 1-7 open |
| ra-platform-commands-skill | #37 | drafted 2026-07-03; skill half shipped as planning-desk, residual = adoption + retirement; decisions 1-6 open |
| roster-provenance-field | #39 | drafted 2026-07-03; decide-first (field vs ratify summary); decisions 1-5 open |
| frontend-extenders-curation | #48 | plan drafted 2026-07-03 beside the staged body; decisions 1-6 open |
| extender-ideas-backlog-seed | #49 | plan drafted 2026-07-03 beside the staged body; T-23 unrun, home decision open |
| agnostic-base-format | #59 | drafted 2026-07-03; survey -> spec -> incremental migration; decisions 1-5 open |

ARCHIVED (issue closed/merged; plan moved to `_meta/_archive/<issue>-<slug>.md`):

| Plan (archived path) | Issue(s) | Why archived |
| -------------------- | -------- | ------------ |
| `_meta/_archive/6-translation-deferred-adapters.md` | #6 | shipped via #18/#20/#21; #6 closed |
| `_meta/_archive/22-test-qa-procedures.md` | #22 | A-C shipped via #23; D spun out to #24; #22 closed |
| `_meta/_archive/41-board-scripts-bundling.md` | #41 | shipped via PR #43 (staged body archived; no deep plan) |
| `_meta/_archive/40-docs-planning-standard.md` | #40 | shipped via PR #62 (DOCS-01..05 rows, scaffold assets, apply, plugin 0.2.0); #40 closed |
| `_meta/_archive/79-portability-conformance-wave.md` | #79 (+ workbench#32) | shipped via PR #80 (dependency contract, mirror checks, in-place fixes, demotions) + wb#33 (gate amendments ratified); both closed 2026-07-04 |

## The loop (how plans get produced)

A repeatable cycle: **draft in parallel** (one agent per plan, every claim cited to `path:line`) →
**review adversarially** against the rubric (a read-only verifier per plan, told to re-derive and
refute, run on your strongest model tier) → **fix** (handed the verified facts) → **augment the
rubric + re-review** → **apply bodies + reconcile** (gate the wave on `reconcile.py` clean). Trust
the findings; treat any 1-5 scores as directional. A perfect sweep is a red flag, not a triumph.
