# HANDOFF — dotfiles-agents

_Cold-start bridge. Last updated: 2026-07-21. Refresh at session boundaries (/handoff). Secret-free._

## 0 · Orientation

dotfiles-agents is a Claude Code marketplace of coding-agent extenders, assembled from
`primitives-core/` into plugin bundles by `scripts/gen_marketplace.py`. `dev` = source, `main` =
CI-published (publish-only, ADR 0014). Task interface + source-of-truth rules: see CLAUDE.md (hot-loaded).

## 1 · Current standing

Both build epics are **DONE and CLOSED**; `make ci` is green. `dev` now also carries the
extender-db merge (#176), the harness (#169), the #174 telemetry lane (PR #177), and the
campaign runner (§2c); `main` is CI-published and lags until publish.
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
- **Gotchas:** PocketBase text fields default-cap at 5000 chars (set `max` explicitly);
  PATCHing a collection with field defs lacking ids drops+recreates columns — schema.py
  merges by name, never bypass it; a builder proving work on a throwaway PB instance can
  mask live-schema divergence (EDB-11) — re-run schema+ingest+gates on the live DB yourself;
  **delta coverage passes MUST use `load_coverage.py --extenders`** (unscoped delta loads
  forge carried-row provenance — EDB-26, full gotcha list in `evals/PROCEDURES.md`);
  **stop the PB server before BRANCH SWITCHES, not just commits** — a live server had its
  tracked data.db checked out from under it (2026-07-21) and SQLite recreated a hollow
  data.db that blocked switching back; pattern: `pgrep -fl pocketbase` → kill → move the
  orphan aside → checkout → restart `evals/serve.sh` (orphan preserved that day at
  `~/.Trash/extender-db-orphan-data.db-20260721`).
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
- **Battle-test outcome:** readme-value-and-proof shows a genuine +1.0 doctrine delta on BOTH
  harnesses; mermaid's reserved-node-id rule fires but isn't held under prompt pressure (both
  harnesses); scout case at ceiling for sonnet-4-5. Ledger: 72 rows (48 legacy pre-Skill-fix claude
  rows are confounded — campaign label `""` vs `skillfix` disambiguates).
- **CI:** marketplace lanes untouched; new path-filtered `harness-test` lane + stdlib coupling gate
  in `make ci`. Open follow-ups: #172 (hermeticity/env-pinning bundle), #173 (candidate-quality
  findings). ~~#174~~ **DONE 2026-07-21 (PR #177, issue CLOSED):** four PB collections
  (`runs`/`artifacts`/`run_events`/`tool_calls`) live in extender-db via the schema.py lane +
  `evals/load_harness_runs.py` ingester; 72-trial corpus ingested (decision record + verified
  counts on #174; runbook = PROCEDURES "ingesting a harness campaign"; blobs in tracked
  `evals/pb_data/storage/`). **Campaign runner also DONE 2026-07-21** (this branch):
  `make harness-campaign` (full grid, `weekly-YYYYMMDD` resume label, pinned
  claude-sonnet-4-5) + weekly launchd agent (Mon 09:00,
  `com.hsb3.dotfiles-agents.harness-campaign`; install/uninstall/status targets). The
  scheduled path NEVER auto-ingests into PB (tracked data.db discipline).

## 3 · Next up (dotfiles-agents proper)

Backlog lives on the dev-tooling desk (`_meta/plans/dotfiles-agents/` + `extenders-estate/`), tracked via
`sequence.py`/`reconcile.py` there — do not freeze a list here.
- ~~**Close-out:** run #111's install-smoke proof, then close #111/#134 + mirrors #121/#135.~~ **DONE (this session).**
- **Forward skill wave (unblocked):** #138 release-loop (code-desk) · #137 decision-loop (exec-desk) ·
  #139 claude-code-expertise (standalone). Names/homes held pending the estate cohesion review (below).
- **Sequenced backlog:** #32 (retire hsb3-custom-plugins) · #36/#122 (clone-at-build externals) · #37.
- **New (filed 2026-07-20):** #149 — standard gap: no `_meta/` slot for secret-free runbooks/reference. Untriaged.
- ~~**Harness follow-ups — QUEUED FOR NEXT SESSION (Henry's ask, 2026-07-21).**~~
  **BOTH DELIVERED 2026-07-21** (owner decisions taken in-session: keep-everything retention,
  PB file-field blobs + tracked `storage/`, launchd scheduler, weekly full grid):
  1. **Campaign runner** — `scripts/harness_campaign.sh` (`run`/`install`/`uninstall`/`status`)
     + `make harness-campaign*` targets + weekly LaunchAgent (Mon 09:00). See §2c.
  2. **#174 PB collections** — delivered via PR #177, issue CLOSED with the decision record.
     See §2c. The formerly machine-local 72-log corpus is now durable in extender-db.
  Still open: #172 (hermeticity bundle) · #173 (candidate fixes: mermaid phrasing, harder
  scout traps). Auth for any live run: `export ANTHROPIC_API_KEY="$(secret get ANTHROPIC_API_KEY)"`.
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

## 6 · Map

- CLAUDE.md — task interface + rules · docs/decisions/ — ADR mirrors.
- **Exec desk** (planning + the desk-platform design): `~/Documents/EXECUTIVE_DESK/Projects/dev-tooling-desk/`
- **desk-standard** (the exec governor / deskkit source, a core co-product; opencode planned-deferred here):
  `~/Developer/desk-standard/`
- Extender census: `dev-tooling-desk/_knowledge/extenders.yaml`
