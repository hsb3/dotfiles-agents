# HANDOFF — dotfiles-agents

_Cold-start bridge. Last updated: 2026-07-22. Refresh at session boundaries (/handoff). Secret-free._

## 0 · Orientation

dotfiles-agents is a Claude Code marketplace of coding-agent extenders, assembled from
`primitives-core/` into plugin bundles by `scripts/gen_marketplace.py`. `dev` = source, `main` =
CI-published (publish-only, ADR 0014). Task interface + source-of-truth rules: see CLAUDE.md (hot-loaded).

## 1 · Current standing

Both build epics are **DONE and CLOSED**; `make ci` is green. `dev` now also carries the
extender-db merge (#176), the harness (#169), the #174 telemetry lane (PR #177), and the
campaign runner (PR #178, §2c); `main` is CI-published and lags until publish.
- **#111** clean-room rebuild (D1–D8) — merged + **CLOSED** (install-smoke proof recorded on the issue).
- **#134** desk-set restructure / 0020 lineup (E1–E7) — merged + **CLOSED**, plus #147 (diagrams / obsidian-toolkit / owner-signoff).
- Multica mirrors **#121** (→#111) and **#135** (→#134) closed to match. **Open PRs: 0.**

Live marketplace lineup: code-desk · exec-desk · foreman-kit · github-project-board · opencode-expertise ·
pptx-themes · private-fork · diagrams · obsidian-toolkit · owner-signoff.

**Also live: the extender-db mini-project, MERGED to dev 2026-07-21 (owner promotion decision)** (§2b) — separate
effort from the rebuild epics; do not fold it into dev without Henry's promotion decision.

## 2 · Recent deliveries (era pointers — blow-by-blow lives in issues/git)

- 2026-07-20: #111 install-smoke proof recorded + epics closed (see §1); branch triage → Open PRs 0;
  planning externalized to the exec desk (see §3).
- 2026-07-21: epic #154 Waves 0–3 executed on `feat/extender-db` (see §2b).
- 2026-07-21 (later session): harness follow-ups delivered — PR #177 (#174 telemetry lane) +
  PR #178 (campaign runner + `weekly-20260721` proof run + PB ingest); briefing
  `_meta/briefings/2026-07-21-weekly-harness-campaign/report.html`.
- 2026-07-22: **ADR 0008 executed, W1–W4** (owner ruling "proceed as proposed"; old-desk 0014
  amended in lockstep — 0008 *restores* its §3 clean-main intent). PRs #180 (foreman-kit 0.6.0:
  new `waves` skill + `.claude/skills/publish-to-main` runbook), #181 (flow.yaml + `make flow`
  guard + generated `docs/FLOW.md` DAG), #182 (filtered **parented** publish; one-time
  `reset=orphan` cutover used), #183 (root artifacts → `dist/claude-code/`), #184
  (`dist/opencode/` laydown lane: `translation.yaml` matrix, targets enum, 24 skills + 4
  remapped agents + installer + generated exclusions manifest). Three publishes verified:
  `main` = distributable surface only, append-only ledger (`publish: dev@<sha>` commits),
  `opencode/` live on main. Suite 157 tests; flow: 17 nodes / 15 edges, 0 planned nodes.

## 2b · Extender-db mini-project (merged to dev 2026-07-21)

PocketBase DB of all agent extenders + the mental models used to compose/evaluate them
(inventory ⋈ doctrine via assessments). **Re-housed 2026-07-21 (owner decision): moved from
`_meta/extender-db/` to root `evals/` — same layout, project name unchanged; pre-move
briefings/issues cite the old path.** **Self-describing — read
`evals/_structure/` CHARTER.md (canonical), PLAN.md, OPEN-ITEMS.md, INSIGHTS.md
(learnings for future docs), `evals/README.md` (operator doc), and
`evals/PROCEDURES.md` (runbook: script run order, the evaluated-pass pattern,
gates, data.db commit discipline) first**; below is only what they don't carry.

- **Promotion: DECIDED + EXECUTED 2026-07-21** — Henry chose merge-to-dev (the charter
  gate was 4/4). The former `feat/extender-db` branch (through `4e5ecb3` + `fb0e69f`) was
  merged with dev (which had independently taken the agent-harness, PR #169 @ `7b0bfd1`);
  the predicted 2-file overlap resolved as planned (.gitignore union; both HANDOFF §2b
  blocks kept). Extender-db and the harness now share one lane on dev. NOTE: the harness
  (#169, follow-ups #172–#174) looks like a candidate for the EDB-14/19 "meta-harness
  pointer" that blocks #165/M5 — Henry confirms, don't assume.
- **State (2026-07-21): epic #154 Waves 0–3 DONE** (wave map + per-wave DoD in PLAN.md;
  evidence on the epic's comments; commits `ab3e2e6`→`c7eacc6`). Coverage now
  **0 gap / 2 partial** over 24 jobs; 8 sub-issues functionally complete (#155–#162,
  #167) and left open for Henry's review/close; #168 filed (excalidraw residual value).
  Era pointers, oldest first — full records in PLAN DONE blocks, OPEN-ITEMS resolved log,
  eval_runs provenance, git: W0 seed → W1 judged pass → W2 hooks → W3 externals → W7
  provenance → W9 taxonomy+sources → adopt-external roadmap (CHARTER decisions 6–8;
  harness is REUSED, never built — EDB-14/19) → M1 coverage body (2026-07-20, eval_runs
  `m1-coverage-*`) → #153 decision batch (A–E accepted, F reversed; DECISIONS-NEEDED.md
  is the record) → epic waves 0–3 (2026-07-21, eval_runs `w2-coverage-*`).
- **Findings a next session should know (details in OPEN-ITEMS):** EDB-25 — the three
  promoted skills are authored ORIGINALS (harness-shipped namesakes have no distributable
  source). **Honest negative:** migrate-at-scale STAYS partial — judge + blind reviewer
  independently declined to rate the playbook-bearing foreman `present`; #158's
  upgrade-to-covered intent was not ratified. typescript-lsp is a declarative LSP config
  with no invokable surface (EDB-23) — its re-judge is queued for the #164 v2 pilot.
- **NEXT:** Wave 4 = #164 (M4 judging-criteria v2 + the EDB-23 externals re-judge via
  `load_coverage.py --extenders`). Then Wave 5 = #163 (M3 curation — unblocked).
  #165 waits on Henry's meta-harness pointer. Owner court: promotion decision + that
  pointer + review/close of the 8 done issues.
- **Operational:** server `evals/serve.sh` (admin UI 127.0.0.1:8090/_/); creds
  in untracked `_meta/operations/extender-db.env` (env file stayed in `_meta/operations/` —
  secrets home is policy-bound, only the project moved). `pb_data/data.db` is TRACKED — stop the
  server before committing (WAL checkpoint) and land the data.db delta in the same commit
  as its cause. `pb_migrations/` is gitignored on purpose: schema.py is the ONE schema source.
  SkillOpt + ClosedLoop reference clones live untracked at
  `~/Developer/EVAL_WORKBENCH/{SkillOpt,claude-plugins-closedloop}` (re-housed 2026-07-21
  from `~/developer/tmp`) — kept for M5/#165.
- **Gotchas:** the PB gotcha list (EDB-1 idless-PATCH column drops · EDB-2 5000-char text
  cap · EDB-11 live-proof mandate · EDB-26 scoped deltas · json first-byte string coercion ·
  file fields need `create_multipart`) lives in `evals/PROCEDURES.md` — read it, don't
  re-derive. Handoff-only extra: **stop the PB server before BRANCH SWITCHES, not just
  commits** — a live server had its tracked data.db checked out from under it (2026-07-21;
  SQLite recreated a hollow data.db that blocked switching back); pattern:
  `pgrep -fl pocketbase` → kill → checkout → restart `evals/serve.sh`.
- Also on this branch: pocketbase-best-practices skill install (`.agents/`,
  `skills-lock.json`, `.claude/skills/` symlink) — desk tooling, not a roster primitive.

## 2c · Agent-harness (delivered 2026-07-21, PR #169 → dev)

Reusable extender-eval harness at root `harness/` (self-contained uv project): drives **Claude Code
or opencode** headlessly against fixture workspaces with a candidate injected per kind, grades
two-tier (deterministic `check.py` + pinned-Haiku rubric), appends to the tracked append-only
ledger `harness/results.jsonl` keyed `campaign|harness|model|candidate|case|config|trial`.
**Self-describing — read in order:** `_meta/research/agent-harness/DESIGN.md` (signed-off design +
wave plan) · `handoff-w1/w2/w4.md` (build evidence; w1 §8b auth gotchas) ·
`battle-test-w3-findings.md` (adversarially verified grid findings) · `runlog-data-shape.md`
(corpus profile + proposed PocketBase collections for #174) · `harness/README.md` (operator doc +
extraction checklist). Owner intent: battle-test here, later extract to its own repo.
- **Auth for live runs:** `export ANTHROPIC_API_KEY="$(secret get ANTHROPIC_API_KEY)"` (claude
  invocation uses per-run apiKeyHelper + fresh CLAUDE_CONFIG_DIR — Option Z, handoff-w4 §1; `--bare`
  was dropped deliberately: it strips the Skill tool).
- **Eval signal (stable across two campaigns — battle-test W3 + `weekly-20260721`):**
  readme-value-and-proof +1.0 doctrine delta on BOTH harnesses; mermaid's reserved-node-id
  rule fires but isn't fully held under prompt pressure; scout case at ceiling for
  sonnet-4-5 (persona never engages). Ledger: 120 rows (48 legacy pre-Skill-fix claude rows
  confounded — campaign labels `""`/`skillfix`/`weekly-20260721` disambiguate). Weekly
  results briefing: `_meta/briefings/2026-07-21-weekly-harness-campaign/report.html`.
- **CI:** marketplace lanes untouched; path-filtered `harness-test` lane + stdlib coupling gate
  in `make ci`. Open follow-ups: #172 (hermeticity/env-pinning bundle), #173 (candidate-quality
  findings — the weekly campaign data strengthens both cases). ~~#174~~ **DONE 2026-07-21
  (PR #177, issue CLOSED):** four PB collections (`runs`/`artifacts`/`run_events`/`tool_calls`)
  via the schema.py lane + `evals/load_harness_runs.py` ingester; both corpora ingested
  (120 runs / 5,054 events / 1,646 tool_calls / 26 blobs in tracked `pb_data/storage/`);
  decision record on #174; runbook = PROCEDURES "ingesting a harness campaign".
- **Campaign runner DONE 2026-07-21 (PR #178):** `make harness-campaign` (full grid,
  `weekly-YYYYMMDD` resume label, pinned claude-sonnet-4-5) + weekly LaunchAgent
  **installed and live on this machine** (Mon 09:00, `com.hsb3.dotfiles-agents.harness-campaign`;
  install/uninstall/status targets; kickstart-once-after-install rule in `harness/README.md`).
  The scheduled path NEVER auto-ingests into PB — **after each Monday run, a session ingests
  deliberately** (`load_harness_runs.py --campaign weekly-YYYYMMDD`, per PROCEDURES) and
  commits data.db+storage with cause. Script is bash-3.2-safe on purpose (launchd resolves
  /bin/bash — see the script header before restructuring it).

## 3 · Next up (dotfiles-agents proper)

**PLANNING ROUND DONE + 4 RULINGS EXECUTED (2026-07-22 session).** The `/waves` mise-en-place ran
to completion and Henry ruled the owner queue in-session; D1/D2/D4/D5 shipped, D3 + O1–O3 remain.
- Plugins already current (foreman-kit **0.6.0**, `waves` live). Pinned **triage issue #192** created
  (the in-repo ranked backlog + waves plan + owner queue); refresh it at boundaries alongside `/handoff`.
- **NOTE.md fully folded in** (source: `_meta/operations/NOTE.md`, updated with per-item status):
  - item-a (pocketbase→`.claude/`, drop `skills-lock.json`) — was Henry's 42ccc12/b07a534, which
    **reddened `make ci`** (deleted `hooks/.gitkeep` + stale flow homes) → repaired **PR #187 (merged)**.
  - **D1 #189** memory folder — RULED rename+redirect → **PR #194 (merged)**: `.claude/agent-memory`
    → `.claude/memory` + `autoMemoryDirectory` in tracked `.claude/settings.json`; auto-memory now
    in-repo/transferable (**effective next session**). 9 topic files (old 4 + migrated hidden 5).
  - **D2 #188** bundles — RULED top-level → **PR #195 (merged)**: `primitives-core/bundles`→`bundles/`,
    homed under the `bundle-metadata` flow node; output-invariant (`make build` = zero drift).
  - **D5** npx-skills rule — RULED global → added to `~/.claude/instructions/tools.md`. **⚠ needs a
    dotfiles-repo commit** (edited but not committed there — that repo's commit discipline is Henry's).
- **functionform-asmbl (#191)** — RULED **PARK, don't archive** (product-surface seed); borrow 3
  concepts tracked in **#193** (its `github_sourcing.py` = reference impl for externals-sync #36/#122,
  noted on #36). Read-only clone; nothing modified.

**→ OWNER'S COURT — still open (triage #192 "Decision gaps"):** **D3 #190** docs — name a specific
target or authorize a general audit (first pass: docs mostly correctly co-located). **O1** extender-db
children review/close (#155–159 done via `8bcb4e0`). **O2** meta-harness pointer for #165. **O3**
forward-skill-wave names/homes (#137/#138/#139, estate-review-gated). Waves 2–5 planned in #192.

Backlog lives on the dev-tooling desk (`_meta/plans/dotfiles-agents/` + `extenders-estate/`), tracked via
`sequence.py`/`reconcile.py` there; the pinned triage issue **#192** is the in-repo ranked view.
- ~~**Close-out:** run #111's install-smoke proof, then close #111/#134 + mirrors #121/#135.~~ **DONE (this session).**
- **Forward skill wave (unblocked):** #138 release-loop (code-desk) · #137 decision-loop (exec-desk) ·
  #139 claude-code-expertise (standalone). Names/homes held pending the estate cohesion review (below).
- **Sequenced backlog:** #32 (retire hsb3-custom-plugins) · #36/#122 (clone-at-build externals) · #37.
- **New (filed 2026-07-20):** #149 — standard gap: no `_meta/` slot for secret-free runbooks/reference. Untriaged.
- ~~**Harness follow-ups (Henry's ask, 2026-07-21)**~~ **BOTH DELIVERED 2026-07-21** — PRs
  #177 + #178, details §2c (owner decisions taken in-session: keep-everything retention,
  PB file-field blobs + tracked `storage/`, launchd scheduler, weekly full grid).
  Still open: #172 · #173. Auth for any live run:
  `export ANTHROPIC_API_KEY="$(secret get ANTHROPIC_API_KEY)"`.
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
  invalidated #148). Branch off `dev`, PR into `dev`. Since ADR 0008 (2026-07-22): `main` is a
  **filtered parented assembly** (never a dev snapshot — verify with tree hashes per the
  `.claude/skills/publish-to-main` runbook); `publish.yml`'s `reset=orphan` input rewrites main
  history and must not be used again without an owner ruling.
- **dev's branch-protection required checks are pinned by CI JOB NAME** — renaming a job in
  `ci.yml` strands every PR on a check that never reports (cost one blocked merge 2026-07-22).
  Update the protection setting first if a job must be renamed.
- **`flow.yaml` is load-bearing**: `make flow` (in `make ci`) fails any PR that adds a top-level
  path without a declared home, or an automated cycle. New generated artifacts need generator +
  guard + a flow node; regenerate the FLOW.md DAG with `scripts/check_flow.py --write-doc`.
- Planning/PM for this repo is run from the exec desk (dev-tooling-desk), not in-repo.
- Comms/decks: the exec-desk `comms` skill uses deck-builder MCP (boardroom theme); `SendUserFile` is absent
  in this env — deliver PDFs via `open`. In-repo deck fallback (proven twice): copy the prior briefing's
  `build_deck.py` (python-pptx via `uv run --with python-pptx`, carbon-white theme), export PDF via
  `soffice --headless --convert-to pdf`, QA-render pages with `pdftoppm` and view them. Audio:
  `speak_gemini --profile briefing --save x.mp3`, but cloud TTS needs fresh `gcloud auth
  application-default login` (interactive, Henry-only) and the kokoro fallback IGNORES
  `--save`/`--no-play` — it just plays aloud.
- Worker agents can drop `.claude/agent-memory/` into whatever directory they worked in — before
  committing, sweep for stray nested `.claude/` dirs; distill anything valuable first, then delete.
  **Scope the sweep to the worker-created subdirs ONLY:** the repo-root `.claude/agent-memory/` is
  TRACKED, legitimate memory — a whole-dir `git rm` swept it once (2026-07-21) and cost a restore
  commit (`c2133fe`).
- **Henry signs off on major IA changes before they are finalized/built** (standing directive 2026-07-20;
  memory `approve-major-ia-changes`). Present IA changes as an approval gate, not a done deal.
- Machine-local leftover: `evals/pb_data/data.db.local-backup-2026-07-21` (gitignored) — a
  pre-branch-switch backup of a data.db that diverged from the tracked copy. Reconcile or
  delete next time a session works in `evals/`.

## 6 · Map

- **Pinned triage issue #192** — `meta: triaged open-issue backlog (living list)`: the in-repo
  ranked backlog view + the dotfiles-agents-proper waves plan + the owner decision queue. Refresh
  it (edit the body, never commit) at session boundaries alongside `/handoff`. Three tracks:
  dotfiles-agents-proper (waves) · extender-db epic #154 (self-manages via `evals/_structure/`) ·
  agent-harness #172/#173.
- CLAUDE.md — task interface + rules · docs/decisions/ — ADR mirrors.
- **Exec desk** (planning + the desk-platform design): `~/Documents/EXECUTIVE_DESK/Projects/dev-tooling-desk/`
- **desk-standard** (the exec governor / deskkit source, a core co-product; opencode planned-deferred here):
  `~/Developer/desk-standard/`
- Extender census: `dev-tooling-desk/_knowledge/extenders.yaml`
