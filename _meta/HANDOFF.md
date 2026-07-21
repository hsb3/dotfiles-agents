# HANDOFF — dotfiles-agents

_Cold-start bridge. Last updated: 2026-07-21. Refresh at session boundaries (/handoff). Secret-free._

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

## 2b · Agent-harness (delivered 2026-07-21, PR #169 → dev)

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
  findings), #174 (durable run-log corpus → PB collections; analysis half done, see data-shape doc).

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
