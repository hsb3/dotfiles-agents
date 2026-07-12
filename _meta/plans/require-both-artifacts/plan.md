---
title: "feat: require both issue-body.md and plan.md in every desk folder"
type: feat
status: draft
created: 2026-07-12
purpose: Source-grounded build plan for #83 -- make the planning desk REQUIRE both issue-body.md (contract) and plan.md (build detail) per folder, so neither artifact is silently skipped; complements #68 (which makes the toolkit SEE body-only folders).
notes: Drafted 2026-07-12 in the plans-wave worktree. Filename discrepancy (issue says `issue_body.md`, all code/disk use `issue-body.md`) is an open question, not silently resolved. Sequencing depends on #68 (same toolkit files) and #82 (renames _meta/plans -> _meta/issues).
---

# feat: require both issue-body.md and plan.md in every desk folder

_Today a desk folder under `_meta/plans/<slug>/` can carry only `plan.md` with no
`issue-body.md` staged alongside it -- the contract half of the two-artifact convention goes
unstaged and un-diffed against the live GitHub issue body. This issue makes both files
REQUIRED: a new/extended check flags any folder missing either one and exits non-zero so it
can gate; authoring guidance states the requirement explicitly; the current desk gets
backfilled. No code has shipped yet -- this is a from-scratch plan, not a residual of prior
work. It directly complements #68, which makes the toolkit merely SEE issue-body-only
folders (`disk_folders()` today keys on `plan.md` alone); #83 goes one step further and treats
a one-file folder as a gate failure, not just a visible state._

Status: draft
Date: 2026-07-12

## Tracking

- Issue: #83 (`require every issue folder under the desk to carry BOTH issue_body.md and
  plan.md`, OPEN). Staged body: `_meta/plans/require-both-artifacts/issue-body.md` (copied
  verbatim from the live issue).
- Relations: **complements #68** (`planning-desk: governance toolkit is blind to
  issue-body-only plan folders`, OPEN, staged at
  `_meta/plans/toolkit-body-only-folders/`, drafted with both artifacts in this same
  plan wave) -- #68 teaches
  `disk_folders()` to count a folder with EITHER artifact; #83 teaches a check to REQUIRE
  BOTH. They touch the same toolkit files and are not in tension: #68's fix (see a body-only
  folder instead of misreporting `row-no-folder` drift) is a precondition for #83's fix
  (flag that same folder as incomplete rather than crashing or silently ignoring it).
- Relations: **sequenced against #82** (`Rename _meta/plans -> _meta/issues`, OPEN) -- #82
  renames the desk directory and touches the same toolkit surface area. This issue's own
  body states the intended order explicitly (see Dependencies below); this plan carries that
  order forward rather than re-deciding it.
- Contract impact: touches `primitives-core/skills/planning-desk/scripts/_utils/` (a
  distributed primitive skill) and its `targets/` mirrors -- **targets drift guard fires**
  (see Gate & contract hygiene).

## The problem (grounded in source)

**EXISTS today -- `coverage.py` checks issue coverage, not artifact completeness.**
`coverage.py`'s `compute()` (`primitives-core/skills/planning-desk/scripts/_utils/coverage.py:100-122`)
reports which OPEN GitHub issues have NO plan folder at all (the planning backlog). It does
NOT check whether a folder that DOES exist carries both files. Its `planned_issue_numbers()`
(`coverage.py:60-67`) treats a folder as "planned" the moment `reconcile.plan_body_issue(slug)`
resolves an issue number from `plan.md`'s `## Tracking` section -- so a folder with only
`plan.md` (no `issue-body.md`) already counts as fully covered by this script's own
semantics; a folder with only `issue-body.md` (no `plan.md`) is invisible to it entirely,
because `plan_body_issue()` (`reconcile.py:74-82`) returns `(None, "no plan.md")` for
anything lacking `plan.md` -- coverage.py has no path that even looks at `issue-body.md`.

**EXISTS today -- the artifact gate is `plan.md`-only, inherited from `reconcile.py`.**
`coverage.py` reuses `reconcile.disk_folders()` via `_load_sibling` (`coverage.py:49`, calls
at `coverage.py:60-67`). `reconcile.disk_folders()` is defined at `reconcile.py:122-125`:

```python
def disk_folders() -> set[str]:
    return {
        p.name for p in PLANS_DIR.iterdir() if p.is_dir() and (p / "plan.md").is_file()
    }
```

This is a single gate on `plan.md` presence -- a folder holding only `issue-body.md` is not a
"folder" by this function's definition at all, so it is invisible to both `reconcile.py` and
(transitively) `coverage.py`. This is exactly the defect #68 targets fixing (see #68's
issue-body.md, "Suggested direction": count a folder with EITHER artifact,
`toolkit-body-only-folders/issue-body.md`). #83 is a different, additional requirement: even
after #68 makes the toolkit SEE a body-only folder, nothing today FLAGS it as incomplete --
#83 adds that gate.

**EXISTS today -- `sync-bodies.py` independently keys on `issue-body.md`.**
`sync-bodies.py:59` reads `body_path = PLANS_DIR / slug / "issue-body.md"` and reports
`"no issue-body.md"` (`sync-bodies.py:65`) as a per-folder status when absent -- but it never
turns that into a non-zero exit or a completeness gate; it iterates over whatever
`reconcile.disk_folders()` already found (i.e. only `plan.md`-bearing folders to begin with,
per the same defect above), so a folder with only `issue-body.md` never reaches
`sync-bodies.py`'s reporting loop at all today.

**EXISTS today -- the desk convention already states "two artifacts per unit of work."**
`primitives-core/skills/planning-desk/SKILL.md:36-40`:

> **Two artifacts per unit of work, with distinct jobs.** The `issue-body.md` is the
> *contract* a builder picks up cold ... The `plan.md` is the *build detail* ... The board
> tracks STATE; the desk holds DETAIL.

This is descriptive prose, not an enforced requirement -- no script checks it, and the setup
flow at `SKILL.md` "Setup" section stages the two files as parallel bullets in the file tree
diagram (`SKILL.md:25-32`) without stating either is mandatory. So requiring both files
codifies existing stated intent; it does not invent a new convention.

**EXISTS today -- the desk's own folders prove the gap is real, not hypothetical.** A direct
inventory of the COMMITTED desk (main-tree `_meta/plans/`, 2026-07-12 -- deliberately
excluding this plan wave's in-flight folders, which were being written concurrently and
made any worktree snapshot instantly stale) shows the mixed population predicted by the
issue:

| Folder | issue-body.md | plan.md | Note |
| ------ | -------------- | ------- | ---- |
| agnostic-base-format | no | yes | plan-only |
| extender-ideas-backlog-seed | yes | yes | both -- conformant |
| externals-clone-at-build | no | yes | plan-only |
| fleet-dashboard-pilot | no | yes | plan-only |
| frontend-extenders-curation | yes | yes | both -- conformant |
| project-workflow-v2 | no | yes | plan-only |
| ra-platform-commands-skill | no | yes | plan-only |
| retire-hsb3-custom-plugins | no | yes | plan-only |
| roster-provenance-field | no | yes | plan-only |

Of the 9 committed folders (excluding `_utils/`, which is the toolkit itself, not a plan
unit), only 2 carry both files -- the backfill's real debt is 7 missing `issue-body.md`
files (or documented exemptions). The current plan wave (#68/#69/#70/#82/#83) adds 5 more
folders, each carrying BOTH artifacts from the start, so the wave adds no debt. **This
table is a point-in-time snapshot of the committed desk, not a live re-run** -- the actual
backfill (Deliverable C) must re-run this inventory at build time, since folder state will
have moved (see Deliverable C below and the flagged build-time caveat).

**MISSING today -- no filename convention check.** Neither the issue's own prose
(`issue_body.md`, underscore) nor any script agrees on one consistent name across every
reference; see "Open questions" #1 below -- this is a real discrepancy, not a typo to paper
over silently.

## Deliverables

**A -- Completeness check: flag any folder missing either artifact, non-zero exit.**
File scope: `primitives-core/skills/planning-desk/scripts/_utils/` (new script or an
extension of `coverage.py`; see Open question #2 for the tradeoff). The check must:
- Enumerate every folder under the desk root (post-#82: `_meta/issues/`; pre-#82:
  `_meta/plans/`) excluding `_utils/` and any documented-exempt folder (see Open question #3).
- For each, test `(folder / "issue-body.md").is_file()` and `(folder / "plan.md").is_file()`
  independently -- NOT via `reconcile.disk_folders()`'s current single-gate definition, since
  that function itself needs the #68 fix first (or this check must not depend on the
  unfixed version -- see Dependencies).
- Report folders missing ONE of the two (distinguish "missing plan.md" from "missing
  issue-body.md" in output, mirroring `sync-bodies.py`'s existing per-file status pattern at
  `sync-bodies.py:65`).
- Exit non-zero if any non-exempt folder is incomplete; exit 0 when clean. Support `--json`
  for machine consumption, matching the house pattern of every existing `_utils/` script
  (`coverage.py:134-136`, `reconcile.py:242-244`).

**Acceptance** (matches issue criterion 1): running the check against a folder holding only
one file exits non-zero and names the missing file; running it after Deliverable C's backfill
(or with documented exemptions applied) exits 0 / reports "0 folders missing either file."

**B -- Authoring guidance states the two-file requirement explicitly.**
File scope: `primitives-core/skills/planning-desk/SKILL.md`,
`primitives-core/skills/planning-desk/references/issue-body.md`,
`primitives-core/skills/planning-desk/references/plan.md`. Changes:
- `SKILL.md:36-40` already describes the two artifacts descriptively; add a sentence making
  the requirement explicit ("both files are required for every folder; a folder with only
  one is incomplete until the desk's completeness check passes, or the folder is a
  documented exemption").
- `references/issue-body.md` (issue mode): state that issue mode stages `issue-body.md` as
  its output but the folder is not considered complete until `plan.md` also exists (even a
  thin one) -- so a builder following issue-mode-only doesn't stop believing the folder is
  done.
- `references/plan.md` (plan mode): symmetric statement -- plan mode assumes an
  `issue-body.md` already exists (per its own Procedure step 1, `references/plan.md:33-38`,
  which already reads `issue-body.md` as an input) and should flag if it is missing rather
  than silently proceeding without a contract to plan against.

**Acceptance** (matches issue criterion 2): grep of the three files for the two-file
requirement language returns a hit in each; a fresh reader of `SKILL.md` alone (no other
context) can state the requirement in one sentence.

**C -- Backfill the current desk.**
Inventory every existing folder (re-run the `ls`-based table above fresh at build time, since
this plan-wave's own PR is landing new folders concurrently) and for each folder missing one
file: either author the missing file (pull `issue-body.md` from the live GitHub issue via
`gh issue view <n> --json body --jq .body` for plan-only folders whose `plan.md` names a
tracking issue; author a minimal `plan.md` stub -- or a fuller one -- for body-only folders),
or add it to a documented exemption list with a one-line reason (see Open question #3 for the
mechanism). **This plan does not execute the backfill** -- it names the deliverable and the
method; the actual per-folder work is build-time (the exact set of folders needing backfill
will have shifted by the time this lands, since #82's rename and this very plan-wave both
touch the folder population concurrently).

**Acceptance** (matches issue criterion 3, and ties to Deliverable A's acceptance): after
backfill, Deliverable A's check reports 0 folders missing either file (net of documented
exemptions).

## Gate & contract hygiene

| Gate | Fires on #83? | Why |
| ---- | -------------- | --- |
| CI aggregate (make ci) | yes | any PR touching `primitives-core/` runs the full aggregate |
| Roster drift guard (make check) | no | no primitive added, removed, or renamed in `primitives-core.yaml` -- this issue edits an existing skill's scripts and docs, not the roster |
| Targets drift guard (make build-check) | yes | edits `primitives-core/skills/planning-desk/scripts/_utils/*.py` and `SKILL.md`/`references/*.md` -- `targets/` mirrors must be regenerated (`make build`) and the drift guard re-checked |
| Naming taxonomy | only if Deliverable A adds a NEW script file | a new `_utils/<name>.py` must clear `docs/naming.md`'s prefix/slug conventions before landing; extending `coverage.py` in place avoids this entirely (see Open question #2) |
| YAML / workflow lint | no | no `.yaml`/`.yml` or `.github/workflows/` edit |
| Canonical-doc amendment | yes, but self-contained | `SKILL.md` is itself the spine doc for the planning-desk skill; Deliverable B amends it in the same PR as the surface change it describes, per the convention |

Also required per the issue body's own gates line and repo precedent (sibling plans cite
the same convention; it is NOT a row in `_config.md`'s six-gate menu): `project-workflow`
plugin version bump (the planning-desk skill is distributed inside it; any script or SKILL.md
edit is a content change to that plugin).

## Parallelism + landing order

| Unit | Scope | Depends on | Notes |
| ---- | ----- | ---------- | ----- |
| A -- completeness check | new/extended script in `_utils/` | none to start; final form depends on how #68 lands (see Dependencies) | can be drafted in parallel with B; do not merge until #68's `disk_folders()` fix is either landed first or this check is written to not depend on the unfixed function |
| B -- guidance updates | `SKILL.md` + 2 `references/*.md` | none | fully parallel with A -- disjoint files, no shared state |
| C -- backfill | per-folder `issue-body.md`/`plan.md` authorship across the desk | A (need the check to verify the backfill worked) and the concurrent folder population from this plan-wave settling | serialize after A; re-inventory at build time since folders are moving under this same PR wave and under #82 |

No timelines; landing order only. Recommended sequencing across the three related issues
(from the issue's own Dependencies section, carried forward): **#68 first** (toolkit learns
to SEE body-only folders) **-> #83 second** (toolkit REQUIRES both, using #68's now-fixed
`disk_folders()` as its foundation) **-> #82 last** (directory rename, so the rename touches
settled script logic rather than landing mid-change on two other in-flight edits to the same
files). Landing #83 before #68 is possible but forces Deliverable A's check to re-implement
the both-files scan independently of `reconcile.disk_folders()` rather than building on it
-- extra work with no benefit, since #68's fix is a strict subset of what #83 needs.

## Open questions / owner decisions

1. **Filename: `issue_body.md` (issue's prose, underscore) vs `issue-body.md` (all code and
   disk, hyphen)?** Verified: the issue's own text reads `issue_body.md` in three places (the
   opening sentence, the Deliverable bullet, and the Acceptance criterion). Verified against
   disk and code: `_meta/plans/frontend-extenders-curation/` and every other folder on disk
   uses the hyphenated `issue-body.md`; `sync-bodies.py:59` hardcodes
   `PLANS_DIR / slug / "issue-body.md"` (hyphen); `SKILL.md:32,36` and
   `references/issue-body.md:5,51,64,68` all use the hyphen. **Recommend: keep the hyphen
   everywhere; treat the issue body's underscore as a typo from drafting, not a rename
   signal.** Rationale: renaming would touch every existing folder + every script + every
   doc reference for a purely cosmetic change, with zero functional benefit, and would
   collide with #82's already-planned rename (touching the same files twice for unrelated
   reasons multiplies risk with no payoff). Alternative (not recommended): if the owner
   wants underscore for cross-project consistency with some other convention, say so
   explicitly -- this plan does not silently pick a side.

2. **New standalone script vs extend `coverage.py` in place?** `coverage.py`'s own docstring
   (`coverage.py:6-16`) frames it narrowly as "which OPEN issues have NO plan folder" --
   backlog semantics, keyed on GitHub issue state via `fetch_open_issues()`
   (`coverage.py:70-87`). Deliverable A's check is different in kind: it is a pure
   disk-completeness scan with no GitHub dependency at all (a folder can be incomplete
   whether or not its issue is open, closed, or even exists yet). **Recommend: a new small
   script** (e.g. `artifact-completeness.py`, subject to `docs/naming.md` and the Naming
   taxonomy gate) rather than overloading `coverage.py` -- keeps `coverage.py`'s "backlog"
   semantics clean per its own docstring, keeps the new check dependency-free of `gh` (faster,
   works offline), and follows the existing `_utils/` pattern of one script per concern
   (`reconcile.py` for table drift, `coverage.py` for backlog, `sync-bodies.py` for body
   sync). **Tradeoff flagged:** a new script adds an 8th `_utils/` entry to maintain and to
   list in `SKILL.md`'s toolkit table and `README.md`'s toolkit table (both need a new row);
   extending `coverage.py` avoids that doc surface but blurs its stated scope and forces
   every `coverage.py` invocation to also shell out or scan disk for a concern its docstring
   says it doesn't own. Alternative (not recommended but viable): add a `--completeness` flag
   to `coverage.py` that runs the disk-only check as a secondary mode, sharing the CLI entry
   point but keeping the compute functions separate.

3. **Trivial-issue exemption mechanism?** The issue explicitly allows "a documented exemption
   for trivial issues." No existing script or doc defines what "trivial" means for this
   purpose (contrast `coverage.py`'s own separate, unrelated `maybe_trivial()` heuristic at
   `coverage.py:90-97`, which tags issues as advisory-trivial for the DIFFERENT question of
   whether they need a plan folder AT ALL -- not whether an existing folder needs both
   files). **Recommend: an explicit exemption list**, not a heuristic -- a small
   allowlist file or a frontmatter marker (e.g. a `exempt-single-artifact: true` line in
   the one file that does exist, or a flat list in `_config.md` alongside the gate menu) so
   the completeness check can skip named folders with a visible, auditable reason attached
   inline. Default: **no folder is pre-exempted** -- the backfill (Deliverable C) either adds
   the missing file or the owner explicitly names an exemption; an empty default list keeps
   the bar high and makes every exemption a deliberate, reviewable choice rather than a
   silent default. Alternative (not recommended): reuse `coverage.py`'s
   `maybe_trivial()` title-regex heuristic for this unrelated purpose -- rejected because it
   answers a different question (needs-a-plan-at-all vs needs-both-files-in-an-existing-folder)
   and repurposing it would conflate two independently tunable policies.
4. **Final #82/#83 ordering -- honor the issue's literal "after the rename" or the wave's
   "#82 lands last"?** The live #83 body asks to land after #82; this plan (with #68's and
   #82's plans) recommends the reverse, #68 -> #83 -> #82, for the single-file-touch
   rationale in Dependencies. **Recommend: #68 -> #83 -> #82** and amend #83's live body
   sequencing note (via sync-bodies, owner-approved) once decided, so the body and the
   plans agree. Alternative: honor the body literally (#68 -> #82 -> #83) and accept #83
   rebasing onto renamed paths.

## Dependencies

- **Sequencing (from the issue body's own Dependencies & gates section, carried forward
  verbatim in intent):** "best sequenced with #68 (same toolkit) and after the `_meta/issues`
  rename (sibling issue) to avoid double-touching the scripts." This plan resolves that into
  a concrete order: **#68 -> #83 -> #82**, reasoned in Parallelism above -- #68's
  `disk_folders()` fix is the substrate #83's completeness check builds on (both-files
  requires first being able to SEE both kinds of single-artifact folder), and #82's rename
  should land last so it touches settled logic rather than racing two other edits to the
  same `_utils/` files. **This REVERSES the issue's literal sequencing** -- the live body
  says "best sequenced with #68 (same toolkit) and after the `_meta/issues` rename
  (sibling issue)", i.e. #82 before #83, whereas this plan (and #68's and #82's plans,
  which surface the same conflict) recommends #83 before #82. Rationale for the reversal:
  sequencing #83 before #68 would force Deliverable A to reimplement #68's fix inline to
  even function, while sequencing #82 before #83 forces #83 to rebase onto renamed paths
  mid-flight -- the recommendation optimizes for touching each shared file once and
  letting the rename sweep settled logic. The owner picks the final order (Open question
  #4); this plan records the divergence rather than silently overriding the issue text.
- **Complementary, not conflicting, with #68:** once #83's completeness check lands, it will
  retroactively flag every incomplete folder that #68 taught the toolkit to merely see --
  in practice the 7 plan-only committed folders in the inventory above, plus any
  body-only folder a future issue-mode session stages. That is intended
  behavior, not a bug: #68 makes those folders VISIBLE; #83 makes their incompleteness
  ACTIONABLE; Deliverable C (backfill) is exactly the mechanism that clears the resulting
  debt rather than leaving the check permanently red.
- **No blocking dependency on Deliverable A's design** for #82's rename to proceed
  independently -- #82 is a path rewrite across the same scripts, not a semantic change, so
  landing order is a risk/efficiency call (fewer merge conflicts, one file-touch each) rather
  than a hard technical blocker in either direction.
