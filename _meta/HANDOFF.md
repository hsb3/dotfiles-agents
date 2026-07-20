# HANDOFF — dotfiles-agents

_Cold-start bridge. Last updated: 2026-07-20. Refresh at session boundaries (/handoff). Secret-free._

## 0 · Orientation

dotfiles-agents is a Claude Code marketplace of coding-agent extenders, assembled from
`primitives-core/` into plugin bundles by `scripts/gen_marketplace.py`. `dev` = source, `main` =
CI-published (publish-only, ADR 0014). Task interface + source-of-truth rules: see CLAUDE.md (hot-loaded).

## 1 · Current standing

Both build epics are **DONE and CLOSED**; `make ci` is green; `dev` and `main` are level (a6c77e4).
- **#111** clean-room rebuild (D1–D8) — merged + **CLOSED** (install-smoke proof recorded on the issue).
- **#134** desk-set restructure / 0020 lineup (E1–E7) — merged + **CLOSED**, plus #147 (diagrams / obsidian-toolkit / owner-signoff).
- Multica mirrors **#121** (→#111) and **#135** (→#134) closed to match. **Open PRs: 0.**

Live marketplace lineup: code-desk · exec-desk · foreman-kit · github-project-board · opencode-expertise ·
pptx-themes · private-fork · diagrams · obsidian-toolkit · owner-signoff.

**Also active: the extender-db mini-project on branch `feat/extender-db`** (§2b) — separate
effort from the rebuild epics; do not fold it into dev without Henry's promotion decision.

## 2 · Recent deliveries (2026-07-20)

- **Epic close-out (this session):** ran #111's install-smoke proof — the only unrecorded acceptance item.
  Observed, not asserted: all **10 lineup plugins loaded from their generated `plugins/` artifacts** in fresh
  `claude --print --output-format stream-json` sessions (the harness `init` event enumerates loaded skills/agents;
  each session completed a real turn). Ran `make ci` locally — green (120 tests). Proof recorded on #111; closed
  #111/#134 + mirrors #121/#135 as completed.
- **PR/branch triage:** closed stale PR #148 (redundant, wrong base = main); deleted 11 orphaned remote
  branches + pruned 10 local; now on `dev`, clean. **Open PRs: 0.**
- **Backlog externalized to the exec desk** — planning for this repo now runs from the dev-tooling desk,
  not in-repo `_meta/plans/`.

## 2b · Extender-db mini-project (active, branch `feat/extender-db`, 2026-07-20)

PocketBase DB of all agent extenders + the mental models used to compose/evaluate them
(inventory ⋈ doctrine via assessments). **Self-describing — read
`_meta/extender-db/_structure/` CHARTER.md (canonical), PLAN.md, OPEN-ITEMS.md, INSIGHTS.md
(learnings for future docs), and `_meta/extender-db/README.md` (operator doc) first**; below
is only what they don't carry.

- **Branch:** off `origin/dev`, pushed through `eac4aa5`. No PR — Henry promotes when the
  charter gate (2/4 ticked) is satisfied.
- **Done:** W0 seed · W1 judged pass (6 judges + 2 blind reviewers + session adjudication) ·
  W2 hooks · W3 externals · W7 eval provenance (exact prompts + verbatim agent responses in
  `eval_runs`/`eval_responses`; all 662 assessments linked). Briefing deck + explainer:
  `_meta/briefings/2026-07-20-extender-db/`; artifact
  https://claude.ai/code/artifact/d3a884d2-441d-410d-a779-5503057c8669
- **Done (this session, 2026-07-20):**
  - **W9 taxonomy / EDB-13** (commit `b3d4248`) — `hsb3-jobs-to-be-done` framework loaded:
    24 solution-agnostic job elements, 7 families (new `framework_elements.category`), kind
    `job-taxonomy`, candidate. Authored with Henry at **deliverable altitude / all-work scope**.
  - **Trusted-source registry / EDB-15** (commit `0c7cd29`) — new `sources` collection
    (publisher-level: `trust_tier`, `publishes_evals`, cited `rationale`/`evidence_url`) +
    `extenders.source` relation; **8 publishers** seeded from an adversarially verified
    deep-research pass (anthropic + mcp-registry trusted; obra-superpowers/daymade/vinnie357/
    coleam00 provisional; skills-sh/tonsofskills watch = W8 comparator baselines). All 6
    externals linked to their publisher. Schema was **signed off by Henry** before build.
  - Both idempotent; 662 prior assessments untouched throughout.
  - **Adopt-external eval roadmap / EDB-17,18** (commit `3d348cd`) — Henry-approved
    revision. **Read the new CHARTER "Roadmap" section + decisions 6–8 and the PLAN
    "Milestone map".** Two tracks, six milestones (M1 coverage · M2 analysis · M3
    combine · M4 eval doctrine · M5 first comparative eval · M6 self-improvement loop,
    staged). Strategy: **adopt external eval methodology, don't build bespoke.** Two
    frameworks loaded (`evaluation-methodology` kind) after reading both repos at source:
    `skillopt` (Microsoft/MIT — scored rollout, validation-gated edit, cheap-model
    substrate, `skillopt_sleep`) for quantitative eval/improvement; `closedloop-judges`
    (Apache-2.0 — judge+rubric→CaseScore verdict, maps onto our `assessments`) for
    qualitative conformance. Two sources added (jeffallan, closedloop-ai). Cheap evals run
    on free models; the eval **execution harness is REUSED, not built** — Henry has a
    meta-harness for opencode + other coding-agent harnesses (EDB-19, likely = EDB-14), so
    do NOT build an `opencode_exec` backend. Repos cloned at
    `~/developer/tmp/{SkillOpt,claude-plugins-closedloop}` (untracked, kept for M5).
- **NEXT: M1 = the W9 mapping body** — map all 37 extenders → the 24 jobs as `assessments`
  (which extender serves which job), add pairwise relationships (dup/conflict/complement),
  produce the coverage matrix. **Two decisions there:** (a) the per-job **disposition**
  model author/vendor/reference/compare + where it's stored (`job_coverage` collection vs
  assessment metadata) — deferred; (b) don't default gaps to "author from scratch" — draw
  from the `sources` registry. Then M4 EDB-21 (formalize judge+CaseScore pattern) → M5
  EDB-20 (author first benchmark). Also open: EDB-9 (obsidian-cli phantom refs — ready
  catalog fix, doubles as W6 update proof).
- **Operational:** server `_meta/extender-db/serve.sh` (admin UI 127.0.0.1:8090/_/); creds
  in untracked `_meta/operations/extender-db.env`. `pb_data/data.db` is TRACKED — stop the
  server before committing (WAL checkpoint) and land the data.db delta in the same commit
  as its cause. `pb_migrations/` is gitignored on purpose: schema.py is the ONE schema source.
- **Gotchas:** PocketBase text fields default-cap at 5000 chars (set `max` explicitly);
  PATCHing a collection with field defs lacking ids drops+recreates columns — schema.py
  merges by name, never bypass it; a builder proving work on a throwaway PB instance can
  mask live-schema divergence (EDB-11) — re-run schema+ingest+gates on the live DB yourself.
- Also on this branch: pocketbase-best-practices skill install (`.agents/`,
  `skills-lock.json`, `.claude/skills/` symlink) — desk tooling, not a roster primitive.

## 3 · Next up (dotfiles-agents proper)

Backlog lives on the dev-tooling desk (`_meta/plans/dotfiles-agents/` + `extenders-estate/`), tracked via
`sequence.py`/`reconcile.py` there — do not freeze a list here.
- ~~**Close-out:** run #111's install-smoke proof, then close #111/#134 + mirrors #121/#135.~~ **DONE (this session).**
- **Forward skill wave (unblocked):** #138 release-loop (code-desk) · #137 decision-loop (exec-desk) ·
  #139 claude-code-expertise (standalone). Names/homes held pending the estate cohesion review (below).
- **Sequenced backlog:** #32 (retire hsb3-custom-plugins) · #36/#122 (clone-at-build externals) · #37.
- **New (filed 2026-07-20):** #149 — standard gap: no `_meta/` slot for secret-free runbooks/reference. Untriaged.
- No `gate:*` label carries an open issue — nothing gate-blocked.

## 4 · CROSS-REPO — the session pivoted to a desk-platform design effort (lives on the desk, NOT here)

Most of this session designed a **new product** on the dev-tooling desk, not dotfiles-agents. It's a toolkit
that integrates AI agents against ONE data model + workflows across three planes (**input · activity · output**),
stored in **PocketBase** (grow deskkit); v1 surface = a Claude Code persona (skills + MCP); files-mirror model
with held diffs (git-agnostic: fsnotify + go-diff). Design runs in **rounds** — R1 (requirements) + R2 (tech +
MIT-borrow survey) closed; **R3 (element model) drafted + both adversarial reviews done — awaiting Henry's IA approval.**

State (all on the desk): `~/Documents/EXECUTIVE_DESK/Projects/dev-tooling-desk/_meta/plans/desk-platform/`
(`plan.md` = round-by-round index; `spec-element-model.md` = the element proposal + both review findings) and
`extenders-estate/system-cohesion-and-datamodel.md`. Decks delivered:
`_meta/briefings/2026-07-20-desk-platform-r3-design/` (R3 design) + `.../2026-07-20-desk-platform-progress/`
(progress + IA-approval gate).

**OWNER'S COURT → NEXT ACTION:** reviews done, progress deck delivered (no agents running). Waiting on **Henry
to approve / adjust / veto the 5 major IA changes** — three-plane reframe · new entities goal/source/deliverable ·
research claim/citation/experiment · software code-PR/bug · registries→entities — and answer 4 open questions
(goal-vs-OKR · keep workstream tags · research loop · which exec outputs first). **On approval:** fold both
reviews into the revised final model (fixes in `spec-element-model.md` § "R3 review findings": promote a core
artifact per type into the spine, define output-plane relations, fix the §3 chain), then R4 = first prototype
slice. Nothing folds into the canonical model until Henry signs off (standing directive, §5).

## 5 · Conventions & gotchas

- Source-of-truth rules are in CLAUDE.md (hot-loaded) — not duplicated here.
- **`main` is publish-only** — never hand-commit/merge there; a CI guard fails PRs into main (that's what
  invalidated #148). Branch off `dev`, PR into `dev`.
- Planning/PM for this repo is run from the exec desk (dev-tooling-desk), not in-repo.
- Comms/decks: the exec-desk `comms` skill uses deck-builder MCP (boardroom theme); `SendUserFile` is absent
  in this env — deliver PDFs via `open`.
- **Henry signs off on major IA changes before they are finalized/built** (standing directive 2026-07-20;
  memory `approve-major-ia-changes`). Present IA changes as an approval gate, not a done deal.

## 6 · Map

- CLAUDE.md — task interface + rules · docs/decisions/ — ADR mirrors.
- **Exec desk** (planning + the desk-platform design): `~/Documents/EXECUTIVE_DESK/Projects/dev-tooling-desk/`
- **desk-standard** (the exec governor / deskkit source, a core co-product; opencode planned-deferred here):
  `~/Developer/desk-standard/`
- Extender census: `dev-tooling-desk/_knowledge/extenders.yaml`
