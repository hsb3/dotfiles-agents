# Sources — 2026-06-12 Friday briefing & week plan

_Hybrid artifact: morning briefing fused with the week's plan + an executive-brief audio.
The **live board is the source of truth** (github.com/<owner>/acme-platform); counts below are
as-of 2026-06-12 afternoon._

## Provenance per claim

- **Build state (slides 4, audio).** Carried forward unchanged from the 2026-06-12 morning
  brief (`_meta/briefings/2026-06-12-morning-status/`) and HANDOFF section 4s/4v: real .app
  cut from main, embedded Postgres boots on a real install (space-path fix), offline proven
  across 4 layers, CI builds the .dmg cross-machine. No commits since 04:11 changed this
  (`git log --since "2026-06-12 04:00"` = the #NNN-#NNN morning merges, already reflected).
- **Board restructure (slides 2, 3, 5; audio).** Done THIS session:
  - 53 unmilestoned issues binned into 6 themed milestones; 0 unmilestoned remaining
    (verified `gh issue list --json milestone | select(.milestone==null) | length` -> 0).
  - Milestones + open counts (as-of): Stage 9 — Desktop demo (PY2025) 10 [due 2026-06-15] ·
    Cockpit webapp — complete 14 · Stage 8 6 · Model/data/modeling completeness 8 ·
    Platform foundations 9 · Ops & observability 6 · Expert agent 8.
  - Stage 9 members: #NNN #NNN #NNN #NNN #NNN #NNN #NNN #NNN #NNN #NNN.
- **acme-labs feeders (slides 2, 6; audio).** Filed this session:
  acme-labs#93 (CMS-HCC ESRD model) + acme-labs#94 (PY2025 county ratebook), cross-linked into
  acme-platform #NNN/#NNN via comments. Gap verified 2026-06-12: acme-labs `platform/loaders/
  parse.py:193` excludes ESRD/RxHCC columns; `cache/` holds only `2026-ma-rate-book.zip`.
- **Branch prune 82 local + 27 remote = 109 (slide 3; audio).** Done this session:
  52 worktree-agent + 24 gone-upstream + 2 merged + 4 design = 82 local; 4 design + 2 merged +
  21 merged-remote-only = 27 remote. Final state: local = main + feat/vendor-kb (open PR #NNN);
  remote = origin/main + origin/feat/vendor-kb.
- **Critical-path chain + acceptance criteria (slides 6, 8; audio).** Lifted verbatim from
  the issue bodies: #NNN [BLOCKING] (owner 2026-06-12, parent #NNN) and #NNN (owner ask
  2026-06-11). The silent no-op detail: #NNN cites `20_score.sql:56-74` recompute no-op +
  `refdata_service.py:128` 503.
- **Gates (slides 6, 9).** `gate:audit-math` = #NNN/#NNN; `gate:onboarding` = #NNN
  (owner-external: real CMS bytes via NDA + CSSC paperwork, no engineering substitute).
- **Dependabot moderate = #NNN (slides 2, 3, 7, 10).** GitHub flagged 1 moderate on main's
  default branch (security/dependabot/2) during this session's branch-delete pushes; #NNN is
  the glib >=0.20 bump in `src-tauri/Cargo.lock`, now in the Stage 9 milestone.
- **Owner-gated poles (slides 4, 7, 9).** Developer ID signing, #NNN sidecar token,
  #NNN refdata model — from HANDOFF + the morning brief; unchanged.

## Calendar note

2026-06-12 is a **Friday**; the Stage 9 demo due date (2026-06-15) is the following
**Monday**. The "week plan" is framed as parallel lanes + deliverables + owner-gated
decisions converging on that one owner-set date — no day-by-day durations (per the
no-timelines convention).

## Artifacts in this folder

- `slides.json` — deliver.py bare slide array (11 slides, boardroom styling)
- `weekly-plan-briefing.pdf` — exported deck (autofit applied, repo-linkified #refs)
- `executive-brief.mp3` — quick executive brief (~3:54, briefing style)
- `sources.md` — this file
