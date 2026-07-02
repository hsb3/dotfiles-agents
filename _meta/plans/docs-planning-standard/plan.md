---
title: "Build plan — docs/ planning-doc minimums (DOCS-xx) + apply + plugin refresh"
type: spec
status: draft
created: 2026-07-02
purpose: Source-grounded build plan for #40 — exact files, row design, scaffold mechanics, landing order, and the open owner decisions.
notes: Intaken 2026-07-02 from the cowork desk (deliverables/docs-planning-standard/). Filed as #40. The issue BODY's copy of record is the live issue + the cowork desk copy. Open question 6 RESOLVED 2026-07-02 — owner ruling, issue bodies are exempt from frontmatter requirements.
---

# docs/ planning-doc minimums — DOCS-xx standard rows, scaffold assets, apply, plugin refresh

_Extend the repo meta-structure standard so `docs/` has enforced minimums (orientation
README, CHARTER canonical page, decisions/ ADR directory with template + index), wire the
scaffold to produce them, bring dotfiles-agents itself to conformance, and bump/refresh the
project-workflow plugin so the standards skills reach installed machines. Everything is
additive: no new primitives, no new audit check types, no renames._

Status: draft
Date: 2026-07-02

## Tracking

- Issue: #40.
- Origin: cowork-desk standards-curation thread, follow-on to the shipped conformance pass
  (`_meta/plans/project-workflow-conformance.md`, status complete 2026-07-02, which already
  flagged a standards backlog).
- Relations: #27 (project-workflow v2 `pw-` renames — path-rebase coordination only);
  #34 / #35 (adjacent standards fixes, non-overlapping).
- Contract impact: edits the machine-consumable checklist (stable-ID contract — rows added,
  never changed/reused) and regenerates `targets/` (drift-guarded). No API/DB surface.

## The problem (grounded in source)

**What exists:**

- The standard triad is built and roster-assigned: `repo-meta-structure` (content),
  `repo-compliance-audit` (verdicts), `mise-en-place-scaffold` (creation), all
  `plugins: [project-workflow]` in `primitives-core.yaml` (anchor on the `id:` keys).
- The audit executes checklist rows generically: `audit.py::load_checklists` /
  `parse_checklist` (`primitives-core/skills/repo-compliance-audit/scripts/audit.py:107,130`)
  read every `ID | Area | Check | Pass condition` row from
  `repo-meta-structure/references/checklist.md`. The check-type vocabulary is closed
  (`path-exists`, `gitignore-*`, `frontmatter-has`, `no-inline-hooks`, `flag-if-present`);
  new rows using existing types require **zero audit-script change**.
- The scaffold sources content only from the standard's assets:
  `scaffold.py::template_source` (`primitives-core/skills/mise-en-place-scaffold/scripts/scaffold.py:528`)
  maps `.gitignore`, `lefthook.yml`, and `.github/*` — nothing else. `AUTHORED_FILES`
  (`scaffold.py:205`) marks README/CLAUDE/AGENTS as never-scaffolded (reported MANUAL).
  Directory rows get `mkdir` + `.gitkeep` (`PlanContext.finalize_gitkeeps`).
- Variance is **additive-only**: `_meta/mise-en-place.yml` `required_folders`/`required_files`
  add VAR-xx rows; there is no waiver mechanism for standard rows
  (`mise-en-place-scaffold/references/manifest.md:32-33`). Whatever DOCS requires must hold
  for every conforming repo.
- Exemplars: `ra-platform/docs/` has `README.md` + `decisions/{README.md, 0000-template.md,
  0001..0029}` but no CHARTER; `dotfiles-agents/docs/` has `CHARTER.md` (precedence line at
  `docs/CHARTER.md:9`) + `images/` + `sops/` but no `decisions/` and no `docs/README.md`.

**What's missing:**

- Any checklist coverage inside `docs/` — only ROOT-08 `path-exists: docs/`
  (`repo-meta-structure/references/checklist.md:77`).
- A home for the decisions the standard already cites by name (skills-over-commands at
  CLAUDE-07; hooks-as-script-plus-config in the HOOK-01 note) — they exist as prose in
  desk/conventions docs, not as ADRs anywhere in the repo.
- A plugin-version bump: `plugins.yaml` `project-workflow` is still `0.1.0`, identical to
  the installed cache (`~/.claude/plugins/cache/dotfiles-agents/project-workflow/0.1.0/`,
  9 skills, predating the standards work), so the built plugin
  (`targets/claude-code/plugins/project-workflow/skills/` — 13 skills including the four
  standards skills) never propagates to machines.

## Deliverables

**A — Standard content: DOCS-xx rows + layout section.**
Files: `primitives-core/skills/repo-meta-structure/references/checklist.md` (new
`## docs/ minimum planning docs` section) and `references/layout.md` (new `docs/` section).
Proposed rows (all `path-exists`, IDs permanent per the stable-ID contract):

| ID | Check | Pass condition |
| -- | ----- | -------------- |
| DOCS-01 | `path-exists: docs/README.md` | Orientation page: what docs/ holds, the docs-vs-_meta boundary |
| DOCS-02 | `path-exists: docs/CHARTER.md` | Canonical page with an explicit precedence rule |
| DOCS-03 | `path-exists: docs/decisions/` | ADR directory exists |
| DOCS-04 | `path-exists: docs/decisions/README.md` | ADR convention (append-only, supersede-vs-correct) + index |
| DOCS-05 | `path-exists: docs/decisions/0000-template.md` | ADR template exists |

layout.md states: these five are the floor; workspace subdirs (design, operations, api,
images, sops) are per-repo shape, guidance only. Acceptance: audit of a bare fixture repo
reports all five as GAP; `parse_checklist` yields them with no duplicate IDs (existing
`tests/test_audit.py` duplicate-ID assertion covers this).

**B — Scaffold assets + mapping.**
Files: `primitives-core/skills/repo-meta-structure/assets/docs/README.md`,
`assets/docs/decisions/README.md`, `assets/docs/decisions/0000-template.md` (content modeled
on `ra-platform/docs/decisions/` — the template's Status/Context/Decision/Consequences/Affects
shape and the append-only + correction-erratum convention); plus in
`mise-en-place-scaffold/scripts/scaffold.py`: a `docs/` branch in `template_source`
(structure-preserving, mirroring the `.github/` branch at `scaffold.py:536-540`) and
`"docs/CHARTER.md"` added to `AUTHORED_FILES` with owner note "authored content — the repo's
canonical precedence page; never scaffolded". Acceptance: `--plan` on a repo missing docs/
plans the three templated files + reports CHARTER as MANUAL; `--apply` additive-only
(existing conflict-diff behavior untouched).

**C — Tests.**
Files: `tests/test_audit.py`, `tests/test_scaffold.py`. Cover: DOCS rows parsed and executed
(fixture pass + gap), template-backed docs files created by scaffold, CHARTER manual
behavior, broken-install error when a docs asset is missing (existing
`standard template asset missing` path). Acceptance: `make ci` green; new tests fail if any
DOCS row or asset is removed.

**D — Apply to dotfiles-agents.**
Run scaffold `--apply` from the built plugin; author real content for `docs/README.md`
(short index: CHARTER, sops/, decisions/, images/); seed `docs/decisions/` with `0001`..`0003`
backfilling skills-over-commands, hooks-as-script-plus-config, externals-tracked-not-vendored
(each sourced from its existing prose home; the ADR cites where it was first decided);
update the checklist's CLAUDE-07/HOOK-01 prose to point at the new ADR paths. Acceptance:
re-audit exits 0 GAP including DOCS rows; the three ADRs conform to `0000-template.md`.

**E — Plugin refresh.**
Files: `plugins.yaml` (project-workflow `version: 0.1.0` -> `0.2.0`), regenerate via
`make build`. Machine-side: reinstall/update the plugin so the cache advances past 0.1.0.
Acceptance: installed cache lists 13+ skills including the four standards skills. If #27
lands first, E is subsumed by its version bump — verify, don't double-bump.

## Gate & contract hygiene

| Gate | Fires? | Why |
| ---- | ------ | --- |
| make ci (aggregate, required) | yes | always |
| Targets drift guard (make build-check) | yes | every edit under primitives-core/ regenerates targets/; never hand-edit targets/ |
| Roster drift guard (make check) | no | no primitive added, removed, or renamed |
| Naming taxonomy | no | no new primitive names |
| yamllint / actionlint | no | no workflow or YAML-lane edits (plugins.yaml edit is value-only; confirm yamllint scope before skipping) |

Checklist stable-ID contract: rows are added, no existing ID is touched. `.in_use` markers in
the plugin cache mean the refresh (E) should happen outside live sessions.

## Parallelism + landing order

| Unit | Owner | Depends on | Notes |
| ---- | ----- | ---------- | ----- |
| A + B | one builder | none | same standard family; checklist, layout, assets, scaffold mapping move together |
| C | one builder | A + B merged locally | can draft in parallel against A/B's staged diff |
| D | one builder | B built (scaffold works) | serialize after B; touches repo root docs/ only |
| E | foreman | A-D landed | one-line version bump + make build + machine update; check #27 first |

Land as **one PR** (A+B+C+D) plus the E follow-through — the conformance-pass precedent
(both repos in one gated wave) applies. If #27's rename PR is in flight simultaneously, land
this first (small, additive) and let #27 carry the mechanical `pw-` path moves.

## Open questions / owner decisions

1. **Is `docs/CHARTER.md` universally required (DOCS-02)?** Variance is additive-only — no
   waivers — so a required row must hold for every conforming repo, and ra-platform doesn't
   have one today. **Recommend: yes, require it** — the "one canonical page with a stated
   precedence rule" is the spine of the docs discipline; ra-platform gains one file when it's
   next audited. Alternative: demote DOCS-02 to layout guidance.
2. **`docs/README.md`: templated or authored?** **Recommend: templated skeleton** (headings +
   the docs-vs-_meta boundary paragraph, repo fills the index) — unlike root README.md, an
   orientation stub has standard shape. Alternative: add to AUTHORED_FILES like CHARTER.
3. **ADR backfill depth (D).** **Recommend: exactly the three load-bearing decisions** the
   standard cites; a fuller historical backfill (e.g. the desk's decision 0001 on gate-exempt
   primitives) is a separate curation task.
4. **Version bump size (E).** **Recommend: 0.2.0** — membership changed (9 -> 13 skills) plus
   new standard content; and adopt the rule "any roster-membership change bumps the plugin
   minor version" (worth a line in the charter or a scaffold/translate warning later; out of
   scope to automate here).
5. **Workbench + other repos.** **Recommend: out of scope here**, follow-up wave reusing D's
   mechanism (the issue's out-of-scope section already says this) — confirm.
6. **Standards clash surfaced during intake: staged issue bodies vs PLANS frontmatter.**
   `sync-bodies.py` diffs a staged `<slug>/issue-body.md` RAW against the live GitHub body
   (`_meta/plans/_utils/sync-bodies.py:67` — no frontmatter stripping), while PLANS-01..06
   require frontmatter on every `*.md` under `_meta/plans/` — a staged body cannot satisfy
   both. **RESOLVED 2026-07-02 (owner ruling): issue bodies are exempt from the frontmatter
   requirements** — a staged `issue-body.md` carries the raw publishable body; the exemption
   is implemented on the audit side (exclude `issue-body.md` from the PLANS scope at
   `repo-compliance-audit/scripts/audit.py:327`, plus the scope prose in the checklist and
   `planning-docs.md`); `sync-bodies.py` stays raw. Implementation tracked as #45.
