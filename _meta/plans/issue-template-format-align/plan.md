---
title: "project-workflow: planning-desk seeds .md issue templates; repo-meta-structure requires .yml issue forms"
type: spec
status: draft
created: 2026-07-12
purpose: Source-grounded build plan for #69 — align planning-desk's seeded issue-template format to what repo-meta-structure's checklist (GH-01..04) actually requires, honoring the issue's own "Corrected scope" split between the live template-format conflict and the invalid conformance.py sub-claim.
notes: Drafted 2026-07-12 in the plans-wave worktree. All source citations verified fresh against worktree HEAD 2026-07-12; corrects one issue-body line-number drift (SKILL.md's seed-templates sentence is at line 105, not 104-106 — the range in the issue spans the whole bullet, the load-bearing sentence is the single line cited here). PLAN-ONLY: no fix implemented.
---

# project-workflow: planning-desk seeds .md issue templates; repo-meta-structure requires .yml issue forms

_A repo that adopts planning-desk's own setup-mode defaults immediately fails the sibling
repo-meta-structure standard's own audit (GH-01..04). This plan scopes ONLY the live half of
#69: align the issue-template format planning-desk seeds/parses to the `.yml` issue-forms set
GH-01..04 expect. The issue's second sub-claim — that `conformance.py` breaks on `.yml` forms —
is INVALID per the issue's own "Corrected scope" section and this plan's fresh re-verification;
no code change is planned for `conformance.py`, and this plan records that explicitly as
deliverable C rather than silently dropping it._

Status: draft
Date: 2026-07-12

## Tracking

- Issue: #69 (`project-workflow: planning-desk seeds .md issue templates; repo-meta-structure
  requires .yml issue forms — fresh desk setup audits as GH-01..04 gaps`, OPEN).
  Staged body: `_meta/plans/issue-template-format-align/issue-body.md` (verbatim copy of the
  live issue body, including its own "Corrected scope" section — see Tracking note below).
- Origin: filed against plugin cache 0.1.0 from a live `raptorxai-infra` planning-desk setup
  run (2026-07-03); the issue body's own "Corrected scope (verified against plugin source
  0.2.4)" section re-verified the claim against current source and split it live/invalid.
  This plan re-verifies that split again, fresh, against the plans-wave worktree.
- Relations: independent of #68 (toolkit blind to body-only plan folders), #70 (desk artifacts
  lack PLANS-xx frontmatter), #83 (require both issue_body.md + plan.md per folder) — those
  three touch the planning-desk **toolkit** (`scripts/_utils/*.py`, plan-folder conventions);
  #69 touches planning-desk's **seeded assets** (`assets/ISSUE_TEMPLATE/*.md`) and its sibling
  skill's checklist. Does not depend on the #82 rename (`_meta/plans` -> `_meta/issues`) — the
  template-format question is orthogonal to the folder name.
- Contract impact: touches `primitives-core/skills/planning-desk/` (a distributed primitive)
  and `primitives-core/skills/repo-meta-structure/references/checklist.md` (the standard doc
  the compliance-audit skill reads verbatim) — both fire the targets drift guard once an
  execution PR lands (see Gate & contract hygiene).

## The problem (grounded in source)

**EXISTS — planning-desk seeds `.md` issue templates, no `.yml` forms, no `config.yml`:**

- `primitives-core/skills/planning-desk/assets/ISSUE_TEMPLATE/` contains exactly
  `bug.md`, `epic.md`, `feature.md` (verified on disk, worktree HEAD) — no `config.yml`,
  no `.yml` forms.
- `primitives-core/skills/planning-desk/SKILL.md:105` — the setup-mode instruction: "If the
  repo has **no** templates, offer to seed them from `assets/ISSUE_TEMPLATE/` (generic
  feature/bug/epic) — the conformance gate needs *some* template structure to check against."
  This is the seeding path that lands `.md` files in a fresh repo's `.github/ISSUE_TEMPLATE/`.
- `primitives-core/skills/planning-desk/assets/_config.template.md:18-20` — the config table
  planning-desk writes into every project's `_meta/plans/_config.md` points at
  `.github/ISSUE_TEMPLATE/{feature,bug,epic}.md` specifically (this repo's own
  `_meta/plans/_config.md:17-19`, produced by this exact template, mirrors it — dogfooding the
  `.md` assumption).

**EXISTS — repo-meta-structure's checklist requires the `.yml` issue-forms set:**

- `primitives-core/skills/repo-meta-structure/references/checklist.md:53-56`:
  ```
  GH-01 | .github/ | path-exists: .github/ISSUE_TEMPLATE/config.yml  | File exists
  GH-02 | .github/ | path-exists: .github/ISSUE_TEMPLATE/bug.yml     | File exists
  GH-03 | .github/ | path-exists: .github/ISSUE_TEMPLATE/feature.yml | File exists
  GH-04 | .github/ | path-exists: .github/ISSUE_TEMPLATE/epic.yml    | File exists
  ```
  This is a hard `path-exists` check with no `.md` fallback branch — the compliance-audit
  skill (which reads this checklist verbatim, per its own scope note) fails GH-01..04 flat
  whenever only `.md` templates are present.

**Consequence — confirmed, not hypothetical:** a repo that runs planning-desk setup mode on a
fresh checkout gets `.md` templates seeded by `SKILL.md:105`, then immediately fails
`repo-compliance-audit` GH-01..04 the moment that audit runs, because the checklist's
`path-exists` targets are `.yml`. This is exactly the sequence the issue's "What happened"
section describes and it still reproduces against current source — the LIVE half of #69.

**EXISTS — the `.yml` issue-forms set to align to already ships, ready to copy:**

- `primitives-core/skills/repo-meta-structure/assets/github/ISSUE_TEMPLATE/` contains all
  four files GH-01..04 need: `config.yml` (2 lines), `bug.yml` (55 lines), `feature.yml`
  (70 lines), `epic.yml` (44 lines) — verified on disk. (The issue text names only
  `bug.yml`/`feature.yml` as existing; `config.yml` and `epic.yml` are also already present —
  a positive drift from the issue's own claim, noted here rather than silently corrected.)
- These `.yml` forms already carry the exact section labels `conformance.py`'s regexes match:
  `bug.yml:36` and `feature.yml:42` both have `label: Acceptance criteria`; `bug.yml:48` and
  `feature.yml:54` both have `label: Dependencies & gates`; `epic.yml:37` has
  `label: Close when`. This means aligning planning-desk's seed source to these files is a
  copy, not an invention — the section-label contract `conformance.py` depends on is already
  satisfied by the standard's own `.yml` assets.

**INVALID — the `conformance.py` sub-claim does not hold (re-verified fresh, not just
carried from the issue's own correction):**

- The script lives at `primitives-core/skills/planning-desk/scripts/_utils/conformance.py`
  (the issue's bare `conformance.py:42-59` cite omits the path; the full path is load-bearing
  for anyone grepping fresh).
- `conformance.py:43-56` (`fetch_open_issues`) calls `gh issue list --state open --json
  number,title,labels,body` — it fetches **live issue bodies from the GitHub API**, not files
  from `.github/ISSUE_TEMPLATE/` on disk.
- `conformance.py:68-70` (`audit_issue`) regex-matches headings out of `issue.get("body")` —
  the fetched body text, never a template file path.
- Nowhere in the file is `.github/ISSUE_TEMPLATE/` read, globbed, or opened. The script is
  format-agnostic by construction: it doesn't care whether the repo's forms are `.md` or
  `.yml`, because it never looks at the form files at all — only at what issue authors
  actually typed as headings in their issue bodies.
- **Conclusion: no code change to `conformance.py` is in scope for this plan.** This is
  recorded as its own deliverable (C) precisely so the "toolkit source refutes part of the
  issue premise" finding survives as a decision, not a silent omission.

## Deliverables

**A — Planning-desk seeds the `.yml` issue-forms set (owner-recommended direction).**
Replace `primitives-core/skills/planning-desk/assets/ISSUE_TEMPLATE/{bug,feature,epic}.md`
with a `.yml` set matching GH-01..04's expected filenames, sourced from
`primitives-core/skills/repo-meta-structure/assets/github/ISSUE_TEMPLATE/*.yml` (copy/adapt
rather than re-author — the section labels already match what `conformance.py` parses). Add
`config.yml`. Update `SKILL.md`'s setup-mode seeding instruction (currently line 105) to
reference the `.yml` set and drop the "generic feature/bug/epic" `.md`-flavored wording.
**Acceptance:** a fresh repo with no `.github/ISSUE_TEMPLATE/` runs planning-desk setup mode,
then `repo-compliance-audit` on the same repo reports GH-01 through GH-04 as `PASS` (not
`GAP`) — independently verifiable by running the audit skill against a scratch repo before
and after the change and diffing the GH-01..04 rows.

**B — `SKILL.md` and `_config.template.md` no longer point only at `.md` paths.**
`primitives-core/skills/planning-desk/SKILL.md:105` and
`primitives-core/skills/planning-desk/assets/_config.template.md:18-20` (the table a fresh
`_meta/plans/_config.md` is written from) both currently hard-code `.md` filenames. Update
both to the `.yml` filenames (or, if the owner instead picks the checklist-accepts-either
alternative in Open Question 1, update them to state the format is project-detected rather
than assumed). This repo's own `_meta/plans/_config.md:17-19` was generated from the stale
template and should be refreshed in the same PR once A lands, since it is a live example of
the drift this deliverable fixes.
**Acceptance:** `grep -n '\.md' primitives-core/skills/planning-desk/SKILL.md
primitives-core/skills/planning-desk/assets/_config.template.md` returns no hits inside the
issue-template seeding/table context (a manual line-scope check, since `.md` appears
elsewhere in both files for unrelated reasons — e.g. doc-file references — so a bare
grep-count is not the right gate; the reviewer confirms the ISSUE_TEMPLATE-specific lines
are `.yml`).

**C — Confirm and record `conformance.py` needs no change.**
No code edit. The deliverable is the recorded finding itself: this plan's "The problem"
section above cites `conformance.py:43-56` and `:68-70` showing it reads `gh issue list
--json ...,body` and regexes the body text, never `.github/ISSUE_TEMPLATE/`. The execution
PR's description must carry this finding explicitly (not just this plan) so a future reader
doesn't reintroduce a needless format-detection branch into the toolkit.
**Acceptance:** the execution PR body contains an explicit statement that
`scripts/_utils/conformance.py` was reviewed and left unchanged, citing the same line ranges,
so the "toolkit source refutes part of the issue premise" finding is traceable from the
merged PR, not just this plan file.

## Gate & contract hygiene

| Gate | Fires on #69's execution PR? | Why |
| ---- | ----------------------------- | --- |
| CI aggregate (make ci) | yes | any PR to this repo |
| Roster drift guard (make check) | no | no primitive added/removed/renamed in `primitives-core.yaml`; this is an in-place asset edit to an existing skill |
| Targets drift guard (make build-check / make build) | yes | planning-desk's `assets/ISSUE_TEMPLATE/*` and `SKILL.md`/`_config.template.md` are distributed primitive content under `primitives-core/skills/planning-desk/`; any edit there requires `make build` to regenerate `targets/` before merge |
| Naming taxonomy | no | no new primitive or plugin named; filenames `config.yml`/`bug.yml`/`feature.yml`/`epic.yml` are fixed by the GH-01..04 checklist, not a naming choice this issue makes |
| YAML / workflow lint (yamllint) | yes | adding/editing `.yml` issue-form files fires the yamllint lane; `actionlint` does not fire (no `.github/workflows/` edit) |
| Canonical-doc amendment | yes, narrowly | `SKILL.md` is planning-desk's spine doc describing its own setup behavior; the seeding-instruction change must land in the same PR as the asset swap, which this plan's deliverable B already requires |

This plan itself (a document under `_meta/plans/`) fires none of the above — report-only,
per the plans-desk convention.

## Parallelism + landing order

| Unit | Scope | Depends on | Notes |
| ---- | ----- | ---------- | ----- |
| A - seed `.yml` forms | `primitives-core/skills/planning-desk/assets/ISSUE_TEMPLATE/*` (delete `.md`, add `.yml` + `config.yml`) | Open Question 1 resolved | must land before or with B; B's SKILL.md wording depends on which filenames A actually ships |
| B - update SKILL.md + _config.template.md pointers | `primitives-core/skills/planning-desk/SKILL.md`, `assets/_config.template.md`, this repo's own `_meta/plans/_config.md` | A | serialize after A; same PR is fine, same file scope as A both are planning-desk assets so no parallel-writer conflict risk |
| C - record conformance.py finding | PR description only, no file edit | none | can happen anytime; costs nothing, bundle into the same PR as A+B |

A and B share the same primitive (`planning-desk`) and are small enough to land as one PR
with one version bump — no benefit to splitting them across separate PRs or agents.

**Cross-plan serialization warning:** #68, #70, #82, and #83 also edit files under
`primitives-core/skills/planning-desk/` (the toolkit scripts and plan-folder conventions,
not the seeded assets this issue touches) and therefore share the same "edit planning-desk ->
`make build` -> `project-workflow` version bump" gate. Any edit to files under
`primitives-core/skills/planning-desk/` regenerates the same `targets/` output and bumps the
same plugin version — two PRs touching this skill in flight at once will conflict on the
version bump and the regenerated `targets/` diff even though their source-file scopes
(`assets/ISSUE_TEMPLATE/*` here vs `scripts/_utils/*.py` for #68/#83, plan-folder frontmatter
for #70) don't overlap. **Serialize the merges** — land one planning-desk PR, rebase+rebuild
the next, rather than merging two in parallel.

## Open questions / owner decisions

1. **Which format wins: ship `.yml` forms in planning-desk (align to the standard), or teach
   the repo-meta-structure checklist to accept either format?** This is the issue's own
   headline owner decision, carried forward unresolved. **Recommend: ship `.yml` forms in
   planning-desk** (deliverable A above) — the issue's own text already recommends this as
   the default, the `.yml` assets to copy from already exist and already carry the right
   section labels (verified above), and it keeps `repo-meta-structure`'s checklist as the
   single, unconditional standard rather than adding an either-format branch that every
   future consumer of GH-01..04 has to know about. **Alternative:** teach
   `checklist.md`'s GH-01..04 rows to accept `.md` OR `.yml` (a `path-exists-any:` check
   variant) — smaller diff, but weakens the standard's own conformance signal for every other
   repo that already ships `.yml` forms deliberately, and this plan does not scope that
   variant's implementation (checklist-schema change is out of this plan's file-scope unless
   the owner picks it, in which case Deliverable A's file targets change and B's file targets
   are unaffected).
2. **Does this repo's own stale `_meta/plans/_config.md:17-19` (generated from the pre-fix
   `_config.template.md`) get refreshed in the same PR as B?** **Recommend: yes** — it is a
   live instance of exactly the drift this issue fixes and costs nothing extra once B's
   template edit is done; flagging it here so the execution PR doesn't treat it as
   out-of-scope busywork.
