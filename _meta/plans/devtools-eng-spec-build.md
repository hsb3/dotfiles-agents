# Build run — DEVTOOLS engineering-specs (11 approved work orders)

_Status: **complete** — all 11 specs landed 2026-07-02 (dotfiles-agents fea9736..1c87a33; workbench 7993666..1cfa18c); final gates green (`make ci` 158 tests, 84 primitives; promote-check 7/15 expected). Henry-gated residue in the vault close-out (Q-04 ratification, brownfield table approval, TC sign-offs, Gate-2 pilot). Started 2026-07-02. Foreman-run crew build executing the 11 approved eng-specs from the vault (`hsb-2026/02_Projects/02_DEVTOOLS/1_Engineering/engineering-specs/`) against this repo (track A) and `dotfiles-agents-workbench` (track B). Landing mode per Henry: **direct to main**, `make ci` (A) / `promote-check` + residue greps (B) locally before every push. Builders edit files only; the foreman runs gates and commits one commit per spec._

## Slots (serial per repo, parallel across repos)

| Slot | Track A (dotfiles-agents) | Track B (workbench) |
|---|---|---|
| 1 | migrate-roster-provenance-and-capability-fields (P0, G1) | revise-cowork-desk-skill-to-v0-2 (P0, G1) |
| 2 | package-repo-meta-structure-standard (P0, Gate 1) | establish-promotions-log-and-registry-dispositions (P1, G3) |
| 3 | wire-naming-lint-into-core-and-promote-check (P0, G1 — spans BOTH repos) | harden-desk-scaffold-template-assets (P1) |
| 4 | package-memory-taxonomy-standard (P1, Gate 1) | amend-promotion-gate-for-sourced-retirement-and-requalification (P1, G3 — after naming lint: shared `promote_check.py`) |
| 5 | build-repo-compliance-audit-skill (P0, Gate 2) | add-brownfield-adoption-mode-to-cowork-desk-skill (P0, G2 — SKILL.md serialized after harden; proof run may need Henry) |
| 6 | build-mise-en-place-scaffold-skill (P0, Gate 2/3 — last: consumes audit + both standards) | — |

## Orderings that must hold (from the specs' own Dependencies sections)

- Roster migration first in A: naming lint says "land first"; all new roster entries must be written post-migration.
- `promote_check.py`: naming lint → promotion-gate amendment (serialize, both edit it).
- `REGISTRY.md`: promotions-log adds `disposition` column → naming lint flips snapshot rows → gate amendment adds its paragraph.
- Cowork `SKILL.md`: v0.2 rename → harden (one line) → brownfield (section rewrite).
- mise-en-place last: reads meta-structure assets, memory-taxonomy stub shape, and the audit's gap list; defines the shared `_meta/mise-en-place.yml` manifest.

## Reconciliations (spec text vs post-migration reality — apply in every affected brief)

1. New roster entries use `origin: authored` (NOT the specced `origin: internal` — that enum dies in the migration).
2. New roster entries carry the now-required `disposition:` field, value per the migrated schema's header comment.
3. The four new skill ids (`repo-meta-structure`, `memory-taxonomy`, `repo-compliance-audit`, `mise-en-place-scaffold`) are kebab-case and pass the naming lane as-is.

## Gates (foreman-run, never asserted by a crew)

- Track A, every slot: `make ci` green (check · validate · names once wired · build-check · test); regenerated `targets/` committed with source.
- Track B: `make promote-check ITEM=cowork-desk` where relevant; residue greps `repo-state` / `strategy-partner` after slots 1/3; REGISTRY column integrity after each edit.
- End of run: full `make ci` + `promote-check-all` + vault reconciliation (flip task rows, update CURRENT_STATE/HANDOFF).

## Out of scope for this run

Q-13 disposition sweep execution (T-20), item renames beyond cowork-desk, clone-at-build externals (G4), #24/#25 follow-ups, any promotion/retirement of actual items.
