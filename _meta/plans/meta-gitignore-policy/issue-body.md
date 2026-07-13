> **Tracking:** #99, owner directive 2026-07-12 ("the broad ignore policy seems to create quite a
> few issues"). Decide-first: evaluate the `_meta/` broad-ignore + negation gitignore policy, pick a
> successor, amend the repo-meta-structure STANDARD it comes from, then migrate this repo + adopters.

## Problem

The `_meta/` gitignore policy is ignore-by-default (`_meta/*`) with tracked items re-included by
negation. The stanza has grown to 27 lines (`.gitignore:16-42`) and the pattern keeps biting:

- **Negation fragility.** Every tracked subtree needs paired `!dir/` + `!dir/**` lines, each
  re-inclusion re-admits Finder/Python litter past the global rules (4 extra `.DS_Store` rules at
  `.gitignore:24-25,30-31,41-42`; the `__pycache__` section must stay ORDERED after the negations,
  `.gitignore:44`), and the base ignore must be the `_meta/*` form or negations silently fail
  (git cannot negate inside a wholly-ignored directory). 18 compliance rows (IGNORE-01..18) exist
  largely to police this fragility.
- **Content invisible where it is needed.** `_meta/research/` is gitkeep-only (`.gitignore:37`):
  the 2026-07-12 ecosystem survey could not be linked from the owner's decision brief (delivered
  as a file attachment instead), and research is invisible to worktree agents and lost on clone.
  `_meta/NOTE.md` (ignored via `.gitignore:17`) held the idea list that spawned #48/#49 — load-bearing
  content in an ignored file.
- **Tracked-by-negation still needs manual discipline.** Briefings flipped to fully-tracked
  2026-07-05, but folders sit untracked until someone remembers to `git add` (the wave-decisions
  rulings brief sat untracked for a day; the 2026-07-12 governance brief is untracked now).
  Ignore policy and commit discipline are entangled.
- **The policy is a packaged STANDARD, not just this repo's file.** The stanza is defined by
  repo-meta-structure (`primitives-core/skills/repo-meta-structure/references/checklist.md`
  IGNORE rows), seeded by mise-en-place-scaffold, measured by repo-compliance-audit, and already
  enacted in adopters (workbench, fleet-dashboard pilot #33). Changing it here without amending
  the standard recreates the CLAUDE.md-vs-charter drift the third-party-disposition proposal
  just flagged.

## Deliverables

- **A — evaluation + decision (ADR in `docs/decisions/`).** Compare at least: (1) status quo
  broad-ignore + negation; (2) track-by-default inside `_meta/` with targeted ignores only
  (`operations/`, caches, OS litter); (3) relocating the secret-holding dir out of `_meta/` so the
  whole desk tracks cleanly. The ADR states the chosen policy and the secret-safety argument.
- **B — this repo migrated.** `.gitignore` rewritten to the chosen policy; a pre-flip secrets scan
  of everything newly tracked (operations/ content must remain untracked under every option);
  existing local-only content (research docs, NOTE.md) explicitly committed or explicitly ruled
  local, none left ambiguous.
- **C — the standard amended in the same change.** repo-meta-structure reference + IGNORE checklist
  rows + the mise-en-place-scaffold gitignore template + the planning-desk setup instructions all
  updated together; `make ci` drift guards prove the packaged skills regenerate.
- **D — adopter migration notes.** A short apply note for workbench + fleet-dashboard (and the
  memory-hygiene stanza in the dotfiles instructions that mirrors this pattern).

## Acceptance criteria

- [ ] The ADR exists and is Accepted; the policy statement appears in exactly one canonical place,
      and repo-meta-structure / CLAUDE.md / scaffold template all point at it without contradiction.
- [ ] `git check-ignore` behavior on this repo matches the ADR for every `_meta/` subtree; a
      secrets scan of the newly tracked set is clean; `_meta/operations/` content remains ignored.
- [ ] The compliance audit's IGNORE rows are updated to test the NEW policy and pass on this repo
      and the workbench (no orphaned rows testing the old pattern).
- [ ] Research artifacts cited by comm packages are clone-survivable (linkable on GitHub) or the
      ADR explicitly rules them local — the 2026-07-12 brief's attachment workaround cannot recur
      silently.
- [ ] `make ci` green: roster/targets drift guards prove the amended skills regenerated.

## Dependencies & gates

- Sequencing: coordinates with the ruled toolkit wave (#68 -> #83 -> #82) — #82 renames
  `_meta/plans/` -> `_meta/issues/` and edits the SAME standard files; land this before or after
  #82, not interleaved.
- Related: #33 (pilot re-audit consumes the updated IGNORE rows), #69/#70 (sibling standards
  fixes), the third-party-disposition proposal (same one-canonical-rule discipline).
- Gates: `make ci` (validate + names + build drift); ADR discipline per project protocol;
  compliance audit green on both repos post-change.

## Open owner decisions

1. **The successor policy** — recommended default: option 2 (track-by-default inside `_meta/`
   with explicit ignores for `operations/`, caches, and OS litter), which deletes most of the
   negation machinery and makes new desk content clone-survivable without per-subtree ceremony.
2. **Whether `_meta/operations/` stays inside `_meta/`** (option 3 moves it out entirely so no
   secret-holding path lives under a tracked-by-default tree).
