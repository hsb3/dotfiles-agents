---
title: "fix: planning-desk toolkit is blind to issue-body-only plan folders"
type: spec
status: draft
created: 2026-07-12
purpose: Source-grounded build plan for #68 — make reconcile.py and sync-bodies.py recognize a plan folder that has only issue-body.md (no plan.md yet), distinguish plan.md-missing (warn) from folder-missing (drift), and document the pre-plan row state in the plans-README template.
notes: Drafted 2026-07-12 in worktree plans-wave. All source citations verified fresh against this worktree's checkout of primitives-core/skills/planning-desk/scripts/_utils/. Cross-references #83 (REQUIRE half of the same toolkit) and #82 (_meta/plans -> _meta/issues rename) for landing order; this plan does not implement either.
---

# fix: planning-desk toolkit is blind to issue-body-only plan folders

_The planning-desk skill's own issue-mode workflow stages `issue-body.md` before `plan.md`
exists — that's the documented normal order (`primitives-core/skills/planning-desk/references/issue-body.md:1-5`
lands the body first; `plan.md` follows "if the work needs build detail"). But the toolkit's
folder-membership test only recognizes `plan.md`, so a folder in that normal intermediate
state is invisible to both governance scripts: `reconcile.py` reports it as a missing folder
(misleading drift) and `sync-bodies.py` never diffs its staged body against the live issue
(false assurance of "nothing to sync"). This plan's three deliverables: (A) fix
`disk_folders()` in `reconcile.py` to count either artifact and add a `plan.md missing` warn
distinct from `folder missing` drift; (B) fix `sync-bodies.py` to classify/diff on
`issue-body.md` presence so staged-body drift against live GitHub is caught; (C) document a
pre-plan row state in the `plans-README.md` template asset. No part of this has shipped —
this is a fresh build, not a residual. This plan itself is report-only: it lands a doc under
`_meta/plans/`, and fires no gates. The gates below describe the FUTURE fix these deliverables
specify._

Status: draft
Date: 2026-07-12

## Tracking

- Issue: #68 (`planning-desk: governance toolkit is blind to issue-body-only plan folders
  (reconcile 'row-no-folder' misleading, sync-bodies compares nothing)`, OPEN).
  Staged body: `_meta/plans/toolkit-body-only-folders/issue-body.md` (verbatim copy of the
  live issue, fetched 2026-07-12).
- Origin: real-world use in `mhi-raptorxai/raptorxai-infra` (2026-07-03) — a fresh desk staged
  three `issue-body.md` files per issue mode; `reconcile.py` and `sync-bodies.py` both failed
  to see them (issue body, "What happened").
- Relations: **same-toolkit siblings #83 and #82** — see Dependencies & gates below for
  ordering. Not blocked on either; sequencing is a landing-order recommendation, not a hard
  dependency.
- Contract impact: this plan document is report-only (no `primitives-core/`, `targets/`, or
  manifest edit). The FIX it specifies, once built, touches
  `primitives-core/skills/planning-desk/scripts/_utils/reconcile.py`,
  `.../sync-bodies.py`, and `primitives-core/skills/planning-desk/assets/plans-README.md` —
  all distributed primitives, so the fix (not this plan) fires the targets drift guard.

## The problem (grounded in source)

**EXISTS — the gate that makes a folder invisible.** `disk_folders()` in
`primitives-core/skills/planning-desk/scripts/_utils/reconcile.py:122-125`:

```
def disk_folders() -> set[str]:
    return {
        p.name for p in PLANS_DIR.iterdir() if p.is_dir() and (p / "plan.md").is_file()
    }
```

A folder is only "on disk" to the toolkit if `plan.md` exists. A folder holding only
`issue-body.md` is excluded from the returned set entirely.

**EXISTS — the resulting misleading drift.** `reconcile()` at
`primitives-core/skills/planning-desk/scripts/_utils/reconcile.py:171-177` checks, for every
ACTIVE README row, `if slug not in folders:` and emits `kind: "row-no-folder"`,
`detail: "ACTIVE row has no plan folder on disk"`. Because `disk_folders()` excludes
issue-body-only folders, any ACTIVE row for such a folder trips this branch even though the
folder — and its staged `issue-body.md` — exists on disk. The inverse check at
`reconcile.py:218-226` (`folder-no-row`, folders with no ACTIVE row) has the same blind spot
in the other direction: an issue-body-only folder with no README row yet is silently invisible
from both checks, not flagged either way.

**EXISTS — a `plan.md`-missing signal already exists and ALREADY FIRES for this case,
alongside the misleading drift.** `plan_body_issue()` (`reconcile.py:74-98`) returns
`(None, "no plan.md")` at lines 80-81 when `plan.md` is absent. The per-row ACTIVE loop
(`reconcile.py:138`) iterates README ROWS, not disk folders: the `slug not in folders`
check (`reconcile.py:172`) appends `row-no-folder` drift but does NOT `continue`, so
execution falls through to `plan_body_issue(slug)` at `reconcile.py:181-183` regardless,
and the `"no plan.md"` warn lands in `warns` — displayed (`reconcile.py:254`, `WARN`
lines) but never gating the exit code (only `drift` does: `reconcile.py:244` on the
`--json` path, `reconcile.py:256-262` on the text path). Empirically verified during
review with a fixture (an ACTIVE row whose folder holds only `issue-body.md`): BOTH
signals fire together — `drift: [row-no-folder]` and `warns: ["no plan.md"]`. So the
defect is NOT a dead code path: the correct warn already fires; the bug is that the
REDUNDANT, MISLEADING `row-no-folder` drift fires beside it (claiming a folder that
exists on disk is absent) and gates the exit code to 1.

**EXISTS — sync-bodies.py inherits the same gate.** `sync-bodies.py:32` imports
`disk_folders` directly from `reconcile`: `from reconcile import PLANS_DIR, disk_folders,
plan_body_issue`. `main()` (`sync-bodies.py:122`) builds its worklist as
`records = [classify(slug) for slug in sorted(disk_folders())]` — so any issue-body-only
folder is excluded from `records` before `classify()` ever runs.

**EXISTS — classify() already keys the body diff correctly, when reached.** `classify()`
(`sync-bodies.py:55-73`) reads `body_path = PLANS_DIR / slug / "issue-body.md"` (line 59) and
diffs local vs remote (`sync-bodies.py:67-72`) purely on `issue-body.md` presence — it never
touches `plan.md`. The bug is entirely in the upstream folder-membership filter
(`disk_folders()`), not in `classify()`'s own logic. This narrows deliverable B: the fix is
`sync-bodies.py`'s worklist source, not its classification function.

**EXISTS — the toolkit's own README documents `sync-bodies.py`'s stated purpose as "each
folder's issue-body.md vs the live GitHub body"**
(`primitives-core/skills/planning-desk/assets/plans-README.md:26`) — the current behavior
silently fails to deliver on that stated contract for any body-only folder.

**MISSING — no fixture/test harness for `_utils/` scripts.** Confirmed by search: no test
files matching `*test*` under any `planning-desk` path in this worktree, and no CI workflow
step invokes `reconcile.py` or `sync-bodies.py` by name (checked `.github/workflows/*.yml` —
zero hits for `planning-desk`, `reconcile`, or `_utils`). These scripts run manually per
`_meta/plans/_config.md:54` ("Run the `_utils/` scripts from the main working tree"). This
means deliverable A's "add a fixture folder + assert reconcile exits clean" (per the issue's
own acceptance wording) has no existing harness to extend — the fix must decide whether to add
one (see open question 3).

**MISSING — no documented pre-plan row state in the README template.**
`primitives-core/skills/planning-desk/assets/plans-README.md:35-38` defines exactly one ACTIVE
table shape (`| Plan | Issue(s) | Status |`) with no distinct column, marker, or worked example
for a folder that has only `issue-body.md`. The live issue's "Workaround used" paragraph
(issue body) describes an ad hoc "PUBLISHED, plan pending" prose list invented outside this
schema — evidence the template has no blessed home for this state today.

**EXISTS — `_meta/plans/_utils/` mirrors `primitives-core/skills/planning-desk/scripts/_utils/`
byte-for-byte** (confirmed: `diff -q` on both `reconcile.py` and `sync-bodies.py` between the
two paths returns no differences in this worktree). Per CLAUDE.md, the mirror is a deployed
copy, not the source; a fix edits the primitive and runs `make build`, which regenerates
`_meta/plans/_utils/*.py` (if the build treats it as a deploy target) and the generated
`targets/` copies. `find targets -path '*planning-desk*_utils*' -name '*.py'` returns
32 files across FOUR distinct copies — `targets/claude-agents/skills/planning-desk/`,
`targets/claude-code/skills/planning-desk/` (bare), `targets/claude-code/plugins/
project-workflow/skills/planning-desk/` (plugin bundle), and
`targets/opencode/skills/planning-desk/` — each carrying all 8 `.py` files (`_repo.py`
plus the seven scripts). A builder's `make build` verification step must account for all
four copies, including the easy-to-miss plugin-bundle copy under `claude-code/plugins/`.

## Deliverables

**A — `reconcile.py`: recognize either artifact, split the warn from the drift.**
`disk_folders()` (`reconcile.py:122-125`) must count a folder as "on disk" if it has EITHER
`plan.md` OR `issue-body.md`. The per-row ACTIVE check (`reconcile.py:171-177`) must then stop
conflating "folder missing" with "plan.md missing": a folder present with only
`issue-body.md` must NOT emit `row-no-folder` (that kind is reserved for a folder that truly
does not exist on disk). The correct signal already fires: `plan_body_issue()`'s
`"no plan.md"` warn (`reconcile.py:80-81`) reaches the `warns` list today even for this case
(see problem section — verified with a fixture). The fix is therefore to SUPPRESS the
redundant `row-no-folder` drift when the folder exists via `issue-body.md`, leaving the
already-firing warn as the sole signal. The distinction: `row-no-folder`
(kind, in `drift`) = folder does not exist on disk at all; `plan.md missing` (new or reused
warn) = folder exists (via `issue-body.md`) but has no `plan.md` yet.
**Acceptance:** add a fixture folder under a controlled test path (see open question 3) with
only `issue-body.md` plus a matching ACTIVE README row; assert `reconcile.py`'s exit code is 0
(clean) and the JSON output (`--json`) shows this folder in `warns` with a `plan.md missing`
(or equivalently worded, see open question 1) detail, NOT in `drift` under `row-no-folder`.
A second fixture asserts the genuinely-absent-folder case still emits `row-no-folder` drift
(regression guard so the fix doesn't over-correct and swallow real drift).

**B — `sync-bodies.py`: fix the worklist source, not `classify()`.**
`sync-bodies.py:32`'s import of `disk_folders` and `main()`'s `sorted(disk_folders())`
(`sync-bodies.py:122`) must draw from the same corrected `disk_folders()` from deliverable A
(shared import — no duplicate logic). `classify()` itself (`sync-bodies.py:55-73`) requires NO
change: it already keys purely on `issue-body.md` presence once it's given the slug. The fix
is narrowly scoped to the worklist source.
**Acceptance:** a fixture folder with only `issue-body.md` staged, whose content differs from
a live GitHub issue's body (mocked or fixture-fetched, see open question 3 on harness), is
included in `sync-bodies.py`'s `records` and reported `status: "DIFFERS"` — today it is
excluded from `records` entirely (0 folders compared, per the issue body's observed output).
A second case with a matching body reports `"in-sync"`. A third fixture (folder + `plan.md`
only, no `issue-body.md`) still reports `"no issue-body.md"` (existing branch,
`sync-bodies.py:64-66`) — regression guard.

**C — `plans-README.md` template: document the pre-plan row state.**
`primitives-core/skills/planning-desk/assets/plans-README.md:35-38` gains either (i) a
documented convention for how an issue-body-only folder appears in the ACTIVE table (e.g. a
`Status` cell value like "staged, plan pending" using the EXISTING one-table schema), or (ii)
an explicit blessing of the ad hoc prose-list workaround the issue describes, written down as
the sanctioned pattern instead of an invented workaround. Open question 2 carries the
recommendation between these two.
**Acceptance:** the template asset names the pre-plan state explicitly (grep for it finds a
non-empty match); a fresh desk scaffolded with only staged `issue-body.md` files (no `plan.md`
anywhere) and README rows following the documented convention reconciles clean under the
deliverable-A fix (exit 0, no `row-no-folder` drift, only `plan.md missing` warns).

## Gate & contract hygiene

_This plan document itself:_

| Gate | Fires on this plan doc? | Why |
| ---- | ------------------------ | --- |
| CI aggregate (make ci) | no | report-only: lands a doc under `_meta/plans/`, no code surface |
| Roster drift guard (make check) | no | no primitive added, removed, or renamed |
| Targets drift guard (make build-check) | no | no edit to `primitives-core/`, `primitives-core.yaml`, or `plugins.yaml` |
| Naming taxonomy | no | no new primitive or plugin named |
| YAML / workflow lint | no | no `*.yaml`/`*.yml` or `.github/workflows/` edit |
| Canonical-doc amendment | no | no spine doc (`CLAUDE.md`, `AGENTS.md`, `docs/CHARTER.md`) altered |

_The FUTURE fix these deliverables specify (not built by this plan) will fire:_

| Gate | Fires on the fix? | Why |
| ---- | ------------------- | --- |
| CI aggregate (make ci) | yes | any PR against `primitives-core/` runs the full aggregate |
| Targets drift guard (make build-check / make build) | yes | deliverables A/B/C edit `primitives-core/skills/planning-desk/scripts/_utils/*.py` and `assets/plans-README.md`, distributed primitives; `targets/` (4 copies each, incl. the `claude-code/plugins/project-workflow` bundle) and `_meta/plans/_utils/` (deployed mirror) must be regenerated, never hand-edited |
| Roster drift guard (make check) | no | no primitive added, removed, or renamed, this is an in-place bugfix to existing scripts |
| Naming taxonomy | no | no new primitive or plugin name introduced |
| YAML / workflow lint | no | no `*.yaml`/`*.yml` edit anticipated (C touches a `.md` asset, not YAML) |
| project-workflow plugin version bump | yes | planning-desk ships inside the `project-workflow` plugin; a behavior change to its scripts is a version bump per repo convention |

## Parallelism + landing order

| Unit | Scope | Depends on | Notes |
| ---- | ----- | ---------- | ----- |
| A - reconcile.py fix | `primitives-core/skills/planning-desk/scripts/_utils/reconcile.py` | none | can start immediately; owns `disk_folders()` which B imports |
| B - sync-bodies.py fix | `primitives-core/skills/planning-desk/scripts/_utils/sync-bodies.py` | A (imports `disk_folders` from reconcile, `sync-bodies.py:32`) | serialize after A lands its `disk_folders()` shape; B's own code change is small (worklist source only) |
| C - plans-README.md template | `primitives-core/skills/planning-desk/assets/plans-README.md` | none (design-independent of A/B's code) | parallel with A and B; needs open question 2 resolved before writing prose |
| Build + regenerate | `make build` regenerates `targets/` (4 copies x 8 scripts) and updates `_meta/plans/_utils/` mirror | A + B + C merged | serialize last; single regeneration after all source edits land, not per-unit |

A and C are file-disjoint and can run as parallel units. B is a one-file, few-line change
gated only on A's shape (the corrected `disk_folders()` signature/return), not on A's full
completion — a builder could stub A's return shape and start B in parallel, then reconcile.
No timelines; landing order only. The cross-issue ordering (#68 vs #83 vs #82) is a separate
concern — see Dependencies & gates below, and Open Questions 4-5.

## Dependencies & gates — cross-issue ordering

Three open issues touch the same toolkit surface
(`primitives-core/skills/planning-desk/scripts/_utils/` and its `_meta/plans/` desk
conventions):

- **#68 (this plan) — the SEE half.** Makes `reconcile.py`/`sync-bodies.py` recognize a folder
  that has only `issue-body.md`. Without this, an issue-body-only folder is invisible to the
  toolkit.
- **#83 — the REQUIRE half.** Its own body states explicitly: "Complements #68 (governance
  toolkit blind to issue-body-only folders): #68 makes the toolkit SEE body-only folders; this
  issue makes both artifacts REQUIRED so neither is skipped" (gh issue view 83, body,
  paragraph 2). #83's deliverable is a NEW check (in `coverage.py` or similar) that flags any
  folder missing EITHER `issue_body.md` OR `plan.md` with a non-zero exit. #83's "Blocks on"
  section says, in full: "best sequenced with #68 (same toolkit) and after the `_meta/issues`
  rename (sibling issue) to avoid double-touching the scripts" — note the second clause: #83's
  own body asks to land AFTER #82, which CONTRADICTS this plan's recommended order below
  (#82 last). That contradiction is surfaced as Open Question 5, not silently resolved.
- **#82 — the rename.** Renames `_meta/plans/` to `_meta/issues/` and touches the SAME seven
  `_utils/*.py` scripts (its body explicitly lists `reconcile.py`, `coverage.py`,
  `sync-bodies.py`, `sequence.py`, "etc." as hardcoding `_meta/plans`). #82's own "Blocks on"
  section says "coordinate with the both-files rule (sibling issue) since both edit the same
  toolkit + skill" — i.e. #82 acknowledges it collides with #83 (and by the same logic, #68).

**Recommended order: #68, then #83 (or landed together in one coordinated PR), then #82
last.** Rationale: #68 and #83 both edit `disk_folders()`/the folder-membership concept in
`reconcile.py` and `sync-bodies.py` — landing #68 first gives #83 a `disk_folders()` that
already recognizes both artifacts, so #83's "require both" check can build on a toolkit that
correctly SEES both artifacts first, rather than #83 building a require-check against a
folder-detection function that's still blind to issue-body-only folders. Landing #82 (the path
rename `_meta/plans` -> `_meta/issues`) last avoids rebasing #68's and #83's line-level edits
across a directory rename that touches every `_utils/*.py` script's hardcoded path constants —
#82's body itself flags this exact collision risk with #83 and, transitively, #68.

## Open questions / owner decisions

1. **Exact wording of the new warn.** The issue's suggested direction says distinguish
   `plan.md missing` (warn) from `folder missing` (drift) but doesn't pin exact string.
   **Recommend:** reuse the existing `plan_body_issue()` return value `"no plan.md"`
   (`reconcile.py:81`) verbatim as the warn detail — it already exists, already fires for this
   case, and is already wired to the `warns` list; deliverable A only suppresses the redundant
   drift beside it. Alternative: a more explicit `"plan.md missing (issue-body.md present)"` if the terser
   existing string reads ambiguously next to the "no `## Tracking` section" warn that shares
   the same function.

2. **New README table state vs blessing the existing prose-list pattern.** The issue itself
   offers both options ("Give the plans-README template a documented state for pre-plan rows
   (or bless the prose-list pattern)"). **Recommend: extend the existing single ACTIVE table**
   with a documented `Status` cell convention (e.g. a row present with `Status` text like
   "staged, plan pending") rather than adding a second table or blessing a free-floating prose
   list — the existing schema (`plans-README.md:35-38`) is already one row per unit of work
   with a free-text `Status` column, so a pre-plan folder fits without a schema change; a
   prose list outside the table is exactly the ungoverned workaround the issue is trying to
   retire. Alternative (if the owner disagrees): formally bless the prose-list pattern instead,
   documenting its exact heading and format so it stops being ad hoc.

3. **Fixture/test harness: new, or extend an existing one?** Confirmed no existing test files
   for `_utils/` scripts (see problem section, "MISSING"). The issue's acceptance criteria
   explicitly demand "add a fixture folder... assert reconcile exits clean" and analogous
   assertions for sync-bodies — this requires SOME harness. **Recommend:** a minimal
   stdlib-only test script (consistent with the `_utils/` scripts' own "no third-party deps"
   convention, `reconcile.py:5`) that builds fixture folders under a temp dir, monkeypatches
   `PLANS_DIR`, and asserts on `reconcile()`'s/`classify()`'s return dict directly (both
   already return structured data, not just print) rather than shelling out and parsing
   stdout. Keep it out of `make ci` unless the owner wants these gated automatically (today
   they run manually per `_config.md`); note in the fix's PR whether it wires into `make ci`
   or stays a manual `_utils/` script.

4. **Land #68+#83 as one coordinated PR or two sequential PRs?** Both touch
   `disk_folders()`/folder-membership logic in the same two files. **Recommend: two PRs,
   sequential** (#68 first) rather than one combined PR — keeps the SEE fix and the REQUIRE
   policy independently revertable and reviewable, and #83's own body only asks to be "best
   sequenced with #68," not merged with it. Alternative: a single PR if the owner judges the
   review overhead of two small sequential PRs isn't worth it for such tightly coupled edits.

5. **Does #82's rename wait for both #68 and #83, or just #68?** The recommended order above
   places #82 last after both — but note the recorded contradiction: #83's own body asks to
   land "after the `_meta/issues` rename", i.e. after #82, which inverts this. The owner must
   pick one ordering for the pair. **Recommend: #82 waits for both #68 and #83 to land** — #82's
   own body says it must "coordinate with the both-files rule (sibling issue)," implying it is
   already aware it should not race #83; extending that same reasoning to #68 (which touches
   the identical `disk_folders()` function #82 will also touch via the path rename) avoids a
   third collision. Alternative: if #83 stalls indefinitely, #82 could proceed after #68 alone
   with a rebase accepted as the cost of not waiting.
