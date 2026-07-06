# Sources — roadmap briefing 2026-07-05

_Claim-by-claim provenance. The **board is the live source of truth**:
github.com/hsb3/dotfiles-agents (project #9). Counts are as-of 2026-07-05._

| Claim | Source |
| --- | --- |
| Phases 0-5 all closed | `gh api repos/hsb3/dotfiles-agents/milestones?state=all` — each Phase milestone shows 0 open |
| Pipeline model (one source copy -> targets, drift guard) | `docs/CHARTER.md` "What this repo is" + "Targets & portability" |
| 12/12 issues conformant (was 4/12) | `_meta/plans/_utils/conformance.py` — run start-of-session (4/12) and end (12/12) |
| Priority spread P0×1 / P1×2 / P2×8 / P3×1 | board snapshot via `board-export.py` -o hsb3 -n 9, post-triage |
| Four gates, 0 unmilestoned | `gh issue list --state open --json milestone` (empty null set) + milestones P1/P2/P3/P4 |
| Gate 2 = Pilot proven, active via #33 | milestone "P2 — Pilot proven" description + issue #33 (P0, Up Next) |
| #68 live bug; #69/#70 re-scoped | Explore-agent source verification this session: `reconcile.py:122-125`, `sync-bodies.py:32`, `conformance.py:42-59`, `checklist.md:132-140`, `references/plan.md:14-31` |
| Gate 4 (Cross-tool parity) filed today | milestone #10 created this session; #59 assigned; `gate:cross-tool` label |
| #69 format decision = .yml | decision comment posted to #69, 2026-07-05 |
| #36 open decisions 1-7 | `_meta/plans/externals-clone-at-build/plan.md` |
| No hard blocked-by edges open | `_meta/plans/_utils/sequence.py` — BLOCKED tier empty |
| Gate-2 pilot = hsb3/fleet-dashboard (superseded raptorgpt) | Decision update 2026-07-05: #33 title/body/comment, plan `fleet-dashboard-pilot/` callout, P2 milestone description, HANDOFF. Vault `hsb-2026/DECISIONS.md` still records the raptorgpt GO — owner to update |

**Deck source:** `slides.json` (deck-builder, boardroom theme). **Written brief:** `brief.md`
(the fuller readout this deck condenses). **Audio:** `roadmap-brief.mp3` (~2.3 min, Gemini/Orus).

**Honest-framing notes:** "proven" is explicitly *not yet* claimed — Gate 2 is open and the deck
says so. The pilot tail (#68/#69/#70) is called out as the signal that proving is incomplete.
No dates are committed (gate-driven, per the no-timelines rule).
