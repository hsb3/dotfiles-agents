# Sources — 2026-07-12 project status briefing

*Claim-by-claim provenance. The GitHub boards are the live source of truth
(github.com/hsb3/dotfiles-agents and github.com/hsb3/dotfiles-agents-workbench);
all counts as-of 2026-07-12 evening.*

| Claim | Source |
| --- | --- |
| Wave fully merged: 11 PRs across both repos in one day | `_meta/HANDOFF.md` section 2 (da #90 #88 #89 #91 #92 + wb #39 #40 #38 #41 + wb#42, da#94); `git log --since=2026-07-11` in both repos (10 da + 8 wb commits to main) |
| Compliance 70 pass / 0 gap (da), was 64/6 | repo-compliance-audit script run twice this session (before/after desk-cleanup PR #97) |
| Compliance 69 pass / 1 gap (wb); gap = docs/CHARTER.md, owned by wb#30 | same audit script run from the workbench root; wb#30 body |
| 14 da + 3 wb open issues, 0 unmilestoned | `gh issue list --limit 1000 --json milestone` both repos (unmilestoned filter = 0) |
| 100% template conformance (14/14 da, 3/3 wb) | `_meta/plans/_utils/conformance.py` (run from each repo root; wb pass after the wb#35 body edit this session) |
| 100% plan coverage (da) | `_meta/plans/_utils/coverage.py` exit 0 |
| Desk reconciles with zero drift after archiving #81/#84 plans | `_meta/plans/_utils/reconcile.py` exit 0 after PR #97 (merged, CI green) |
| Staged bodies byte-identical to GitHub; #48/#49 #TBD fixed | `_meta/plans/_utils/sync-bodies.py`: 7 in-sync, 0 differ (7 missing issue-body.md are #83's tracked backfill scope) |
| Evidence gaps 6 -> 0 | `_meta/plans/_utils/evidence-audit.py` before/after; comments posted on #2 #3 #4 #10 #71 #73 citing PR #12, PR #15, commits 7a7cec3 / e17d534 (spot-checked in git log) |
| fable-foreman live on main; PR #86 closed, findings fixed in PR #95 | `gh pr view 86` (CLOSED, mergedAt null), `gh pr view 95` (MERGED 2026-07-12T22:11Z), commit c8a63f7 on main, roster entry primitives-core.yaml:155 |
| Roster 65 primitives (agent=18, skill=47) | `make check` on main, 2026-07-12 evening |
| #32 top-ranked P1, unblocked; residuals + 8-symlink gotcha | `_meta/HANDOFF.md` section 2 item 1; gotcha recorded on issue #32 |
| #33 proof complete (0 create / 3 conflict / 1 manual / 66 ok); residual = charter draft + plan refresh | `_meta/HANDOFF.md` section 2 item 2; records attached to issue #33 |
| Ruled wave order #68 -> #83 -> #82; #48 paused on owner scope entries | `_meta/HANDOFF.md` section 2 (owner rulings, `_meta/briefings/2026-07-12-wave-decisions/brief.md`); `_meta/plans/frontend-extenders-curation/scope.md` |
| wb lane items (curate-memories J1, speak-summary wiring, web-setup rework) | `_meta/HANDOFF.md` workbench follow-ups; wb#35 owner-ruling comment (2026-07-12) + acceptance criteria added this session |
| Owner CANON TODOs (wb#32 ratification, raptorgpt-GO supersession, 2 standing policies) | `_meta/HANDOFF.md` section 2 owner-TODO line |
| fable-foreman re-triage watch-item | inference from the #81 precedent (PR #90 demoted 14 untested authored primitives); fable-foreman entered core via PR review without bench J1 evidence — flagged as a watch-item, not a ruling |

Audio: `project-status.mp3` (3 min 37 s, Gemini/Orus, briefing style) — script restored the
status look-back section that the narrate refinement pass had dropped, then matches the deck order.
