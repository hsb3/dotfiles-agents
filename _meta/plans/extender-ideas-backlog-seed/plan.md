---
title: "Build plan — seed the use-case-driven extender backlog with captured ideas (#49)"
type: spec
status: draft
created: 2026-07-03
purpose: Source-grounded plan for #49 — verify the 8 captured ideas' source assets, pick the interim backlog home (T-23 has not run), and land each idea as a use-case-driven entry with asset pointers.
notes: Drafted 2026-07-03 against fresh disk/gh state. Key deltas vs the issue body — _meta/NOTE.md no longer exists on disk; #31 (openspec provenance) closed 2026-07-03; vault task T-23 verified todo, so an interim home is required. Owner decisions 1-4 below block the write; everything after them parallelizes.
---

# feat: seed the use-case-driven extender backlog with captured ideas (2026-07-02)

_Residual: eight extender ideas from Henry's 2026-07-02 notes must land in the use-case-driven
backlog — but the notes file (`_meta/NOTE.md`) has since vanished from disk, the vault task that
establishes the backlog's home (T-23) has not run, and one idea's named source material (the
ra-platform API-documentation notes) cannot be located cold. The ideas themselves are safe: they
are fully captured in issue #49's body and in the cowork desk's `analyses/backlog.md`
(pre-decision form, updated 2026-06-30). What remains is a pure capture/curation move — pick the
interim home, rewrite each idea as a use-case entry with verified existing-asset pointers (all
roster line numbers re-cited fresh below), frame the five duplicate-coverage ideas as
enhancements, and resolve two source-pointer gaps with Henry. No code, no gates._

Status: draft
Date: 2026-07-03

## Tracking

- Issue: #49 (open, `enhancement`, staged body at `_meta/plans/extender-ideas-backlog-seed/issue-body.md` — in sync with the live body except the `#TBD` tracking line).
- Origin: Henry's 2026-07-02 notes, `_meta/NOTE.md` ("ideas for future extenders"). **Verified 2026-07-03: the file no longer exists** — not in `_meta/`, not in `_meta/_archive/`, never git-tracked (no history). The capture survives in two places: the issue #49 problem statement (the 8 ideas verbatim) and the cowork desk `~/Documents/Claude/Projects/dotfiles-agents-cowork/analyses/backlog.md` ("Source: `dotfiles-agents/_meta/NOTE.md`", updated 2026-06-30). Issue #49's body is now the authoritative capture.
- Relations:
  - Vault decision `use-case-driven-backlog` — **accepted 2026-07-02**, verified at `<VAULT>/1_Engineering/decisions/use-case-driven-backlog.md` and indexed in `<VAULT>/1_Project_Management/DECISIONS.md:25`, where `<VAULT>` = `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/hsb-2026/02_Projects/02_DEVTOOLS`. Ruling: an extender enters the backlog because a named project or workflow needs it; ranked by how soon the need is real; the vendor-resources list is a sourcing catalog, not a backlog.
  - Vault task **T-23** — verified at `<VAULT>/1_Project_Management/TASKS.md:37`, status **todo** ("Route the 2026-07-02 goals/wishlist journal into the extenders backlog as ranked use-cases ... + draft the core-milestone-set standard"). **T-23 has NOT run**, and no `extenders-backlog` artifact exists anywhere in the vault (searched) — so the backlog has no established home today; this plan must pick an interim one (owner decision 1). T-23's own input (the `2026-07-02 Goals and Capability Wishlist` journal) is a different, complementary list (12 "build good X" use cases); the 8 ideas here are supply-side seeds that T-23's ranking should absorb.
  - #31 (Q-13 bootstrap-triage sweep) — **closed 2026-07-03**. The issue body's "provenance pending under #31" for the openspec skills is resolved: all four remain `origin: authored`, `disposition: grandfathered-pending-use`.
  - #48 (frontend-extenders-curation) — adjacent capture thread, staged body only; no file overlap.
- Contract impact: **none.** Backlog seeding only — no code, no roster edit, no `targets/` regeneration, no checklist rows.

## The problem (grounded in source)

**The origin file is gone.** `_meta/NOTE.md` does not exist (verified 2026-07-03: absent from `_meta/`, `_meta/_archive/`, both sibling repos, and git history — it was untracked). The issue's premise "eight ideas exist only in a personal notes file" is stale in both directions: the file is gone, AND the ideas were already mirrored to the cowork desk's `analyses/backlog.md` on 2026-06-30 (all 8 appear there under "Near-term enhancements" and "Future extenders"). Acceptance criterion 2 ("zero remain only in `_meta/NOTE.md`") is therefore vacuously true; the real intent — each idea living where the ranking process can see it, with use case + asset pointers — is not yet met, because the desk entries pre-date the `use-case-driven-backlog` decision and carry neither use-case framing nor complete pointers.

**The backlog has no home yet.** T-23 (todo) is what establishes the ranked backlog; no vault backlog artifact exists. Candidate interim homes today: (a) the cowork desk `analyses/backlog.md` — already holds the 8 ideas, header rule "never a parallel backlog; concrete items graduate to GitHub issues via planning-desk"; (b) a new vault note pre-empting T-23; (c) direct-to-GitHub-issues ranked by the board's Impact/Effort rubric. See owner decision 1.

**Idea-by-idea asset verification (2026-07-03, all citations fresh):**

| # | Idea | Existing asset (verified) | Source material (verified) |
| - | ---- | ------------------------- | -------------------------- |
| 1 | openspec expertise add-on | 4 roster skills, all in plugin `openspec`: `openspec-apply-change` (`primitives-core.yaml:483`), `openspec-archive-change` (:493), `openspec-explore` (:503), `openspec-propose` (:513); provenance resolved via #31 (closed, stayed authored) | `~/dotfiles/_docs/reference/openspec/` EXISTS - 5 files: README, brownfield-adoption, example-project-report, human-readable-reports, reverse-engineering-existing-projects |
| 2 | claude-code expertise add-on | none on roster; nearest incubator item is workbench `claude-exchange` (relationship unconfirmed) | none given in the notes |
| 3 | api-server-design enhancement | roster skill `api-server-design` (`primitives-core.yaml:32`, shelf core, no plugin) | ra-platform API-documentation notes **NOT LOCATED** - no local ra-platform checkout found under `~/Developer`; `ra-platform-cowork` desk holds an `openapi.json` artifact but no authored API-doc notes. Owner decision 3 |
| 4 | comms improvements | roster skill `comms` (`primitives-core.yaml:102`, plugin project-workflow, requires local-mcp); pairs with `pptx-henry` (:533); workbench incubator `presentation-designer` + `style-canon` | presentation-preference material candidates verified: cowork desk `_meta/presentation-deliverable-norms.md` |
| 5 | CMS data-mart trio | all three on roster: `cms-bigquery-etl-generator` (`primitives-core.yaml:72`), `cms-json-data-dictionary` (:82), `cms-pdf-to-markdown` (:92); plus agent `cms-data-engineer` (:657) and workbench incubator `cms-data-pipeline` | the evaluate-vs-Google's-BigQuery-skill question is captured in desk `analyses/backlog.md` |
| 6 | dbt expert | **nothing exists** - zero `dbt` hits in `primitives-core.yaml` and `externals.yaml` (verified) | driving use case: CMS data mart + vault wishlist "analytic data models - using dbt" |
| 7 | dlt-pipelines expert | roster skill `dlt-pipelines` (`primitives-core.yaml:181`); summary already claims "production-ready ETL/ELT data pipelines using dlt" - coverage assessment is the entry's first task | none beyond the skill itself |
| 8 | diagrams consolidation | roster skill `diagrams` (`primitives-core.yaml:171`, plugin project-workflow) | the "scattered utilities/experiments/draft skills" are UNINVENTORIED - the entry must carry the inventory sweep as its first task |

All eight roster entries verified `origin: authored`, `disposition: grandfathered-pending-use` (post-#31 state; 84-entry roster per `_meta/HANDOFF.md`).

## Deliverables

**A — Each idea landed as a backlog entry in the chosen home.**
One entry per idea (8 total, or 7 + one explicit decline per owner decision 4), each carrying:
the driving use case (named project or workflow, per the `use-case-driven-backlog` decision),
what already exists (the verified roster/workbench pointers from the table above, with
`primitives-core.yaml` line cites), and the source-material pointers (idea 1: the openspec
reference dir path; idea 4: the presentation-norms file + pptx-henry pairing; idea 5: the desk
backlog note; idea 3: whatever owner decision 3 names). The home's header gets a one-line flag:
"interim wishlist — T-23 absorbs this into the ranked backlog when it runs."

> Entry shape + minimum fields follow the **backlog-entry form** standard (#84):
> `planning-desk` skill `references/entry-forms-and-milestones.md` (Part 1, Application A). The three
> fields above (use case, existing assets, source pointers) are that form's shared core.

Acceptance (maps to issue checkboxes 1 and 2):
- All eight ideas appear in the chosen home with use case + existing-asset pointers, or are explicitly declined with a one-line reason.
- None of the eight exists only in a location the ranking process cannot see (NOTE.md is already gone; the check is that the chosen home + issue #49 body are consistent).
- Independently verifiable: open the home file, count entries 1-8, confirm each has the three fields (use case, existing assets, source pointers).

**B — Duplicate-coverage ideas framed as enhancements, not new extenders.**
Ideas 3, 4, 5, 7, 8 (roster coverage exists) are written as enhancement entries against the
named existing primitive — e.g. "enhance `api-server-design` (primitives-core.yaml:32) with ..."
— never as new-extender entries. Ideas 1 (add-on over 4 existing skills), 2, 6 are the only
net-new candidates.

Acceptance (maps to issue checkbox 3):
- Entries for ideas 1, 3, 4, 5 cite their named source material concretely enough that a builder can find it cold: idea 1 = `~/dotfiles/_docs/reference/openspec/` (verified path); idea 4 = cowork desk `_meta/presentation-deliverable-norms.md` + `pptx-henry` pairing; idea 5 = desk `analyses/backlog.md` evaluation note; idea 3 = the pointer Henry supplies under owner decision 3 (this is the one criterion that cannot be met without him).
- Each of 3, 4, 5, 7, 8 names the primitive it enhances with a fresh line cite; a reviewer can grep the entry for `primitives-core.yaml:` and hit all five.

## Gate & contract hygiene

**No repo gates fire — this is capture/planning only, and it must stay that way.**

| Gate | Fires? | Why |
| ---- | ------ | --- |
| CI aggregate (make ci) | no | no PR needed if the home is the cowork desk or vault; if the home lands in-repo, the change is markdown-only under `_meta/` and CI still passes trivially |
| Roster drift guard (make check) | no | no primitive added, removed, or renamed |
| Targets drift guard (make build-check) | no | zero edits under `primitives-core/` or to any yaml source; `targets/` untouched |
| Naming taxonomy | no | no new primitive names are minted - backlog entries name candidates, they do not register ids |
| yamllint / actionlint | no | no yaml or workflow edits |

Two hygiene rules from `_meta/plans/_config.md` that DO apply: outward-facing GitHub edits
(filing per-idea issues, closing #49) get owner approval first; and if the desk's plans README
status table gains a row for this plan, that edit happens in the landing PR, not before.

## Parallelism + landing order

| Unit | Depends on | Notes |
| ---- | ---------- | ----- |
| 0. Home decision | owner decisions 1-2 | serializes everything - nothing can be written until the home is chosen |
| 1. Entries 1, 4, 5, 6, 7, 8 | unit 0 | fully parallelizable (or one writer in a single pass - each entry is a paragraph); asset pointers are pre-verified above |
| 2. Entry 3 (api-server-design) | unit 0 + owner decision 3 | blocked on the source pointer; land it last or land with a "pointer TBD from Henry" marker if he defers |
| 3. Entry 2 (claude-code add-on) | unit 0 + owner decision 4 | lands as either an unranked entry or an explicit decline |
| 4. Close-out | units 1-3 | tick the three issue checkboxes with evidence links; update the plans README ACTIVE table row; close #49 (owner-approved); leave the T-23 absorption flag in the home's header |

The B-framing is a constraint on how units 1-2 are written, not a separate unit. No timelines.

## Open questions / owner decisions

1. **Interim backlog home (blocks everything).** Options: (a) restructure the cowork desk
   `analyses/backlog.md` in place — it already holds all 8 ideas, the desk is the ecosystem's
   strategy layer, and T-23 can absorb from there; its "never a parallel backlog" header rule is
   compatible if entries stay rationale-layer (graduating to issues only when scheduled);
   (b) create the vault `extenders-backlog` note now — but that pre-empts T-23's design;
   (c) file straight to GitHub issues — conflicts with the desk rule and floods the board with
   unranked items. **Recommended default: (a)** — restructure `analyses/backlog.md` into
   use-case-driven entries with the T-23 absorption flag in its header.
2. **File per-idea GitHub issues now or after ranking?** The `use-case-driven-backlog` decision
   ranks by "how soon the need is real"; the board rubric (Impact/Effort) applies at issue time.
   **Recommended default: after ranking** — only entries a named near-term use case claims (the
   CMS data mart plausibly claims 5, 6, 7 first) graduate to issues via the planning desk;
   filing all 8 now recreates the coverage-driven anti-pattern the decision rejected.
3. **Where are the ra-platform API-documentation notes (idea 3)?** Not locatable cold: no
   ra-platform checkout under `~/Developer`, and the `ra-platform-cowork` desk has only an
   `openapi.json` artifact. Henry must name the repo path or desk file. **Recommended default:**
   land the entry with an explicit "source pointer: ASK HENRY — candidates exhausted" marker
   rather than blocking the wave; acceptance checkbox 3 stays unticked until he answers.
4. **Idea 2 (claude-code expertise add-on): enter or decline?** No source pointer, no driving
   use case named, no existing asset. **Recommended default: enter as an unranked wishlist
   entry** (one line, "no use case claimed yet — per the decision, it waits until one does")
   rather than declining — it costs nothing in the rationale layer and preserves the capture.
