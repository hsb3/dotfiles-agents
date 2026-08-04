# HANDOFF — dotfiles-agents

_Cold-start bridge. Last updated: 2026-08-03. Refresh at session boundaries (/handoff). Secret-free._

## 0 · Orientation

dotfiles-agents is a marketplace of coding-agent extenders serving TWO runtimes from one
source tree (ADR 0017): Claude Code installs the hand-authored symlink assemblies under
`plugins/<id>/` (root `.claude-plugin/marketplace.json`) natively; opencode is generated at
install time (`scripts/install_opencode.sh`). **Nothing generated is tracked.** `dev` =
source, `main` = CI-published (publish-only; but see task-5 below — publish is currently
broken-by-design). Task interface + source-of-truth rules: see CLAUDE.md (hot-loaded).

## 1 · Current standing

`make ci` green — 95 tests (38 primitives: agent=4, hook=4, skill=30). **The ADR 0017
pointer refactor EXECUTED 2026-08-03/04** (owner authorized merge-and-continue): m-0 tasks
1–4 + 7–8 DONE via PRs #227–#231 (squash-merged; blow-by-blow lives there). Net state:

- **ADR 0017** formalizes decision-2; ADR 0008's dist-lane design `Superseded-by-0017`
  (flow guard survives, ruled with task-7). Mechanics are in CLAUDE.md (hot-loaded).
- 15 symlink assemblies + root marketplace.json, linted by `make symlinks`; verified by
  byte-identity vs the old dist AND live path-marketplace installs before retirement.
- READMEs travel with their skill (`standalone-readmes/` + `bundles/` gone); retired:
  `dist/` (530 files), gen_marketplace/gen_standalone/check_skill_catalog, plugins.yaml,
  skill-catalog.yaml. Roster = provenance manifest; check_roster.py slimmed in place (its
  parse_roster serves check_identity/check_provenance/gen_opencode/evals).
- opencode is install-time (`scripts/install_opencode.sh`); round-trip verified vs live
  opencode 1.18.11 (23/23 skills, 4/4 agents). Live fix: agent `color:` dropped in the
  transform — opencode hard-fails on CC named colors.

`main` still holds the pre-0017 dist-lifted assembly (published 2026-07-22 at
`dev@0cdca55`). **publish.yml now fails loudly at assembly if dispatched** (dist is gone) —
deliberate; task-5 decides what publishing means under the pointer architecture.

Live marketplace lineup unchanged (ADR 0016, 15 plugins): **code-desk (0.3.0)** ·
foreman-kit (0.6.0) · diagrams · obsidian-toolkit · 11 standalones (claude-code-config ·
claude-code-expertise · dataviz · deep-research · github-project-board · opencode-expertise ·
owner-signoff · pptx-themes · private-fork · project-memory · tech-eval-research).

**Also live: the extender-db mini-project** (§2b) — separate effort from the rebuild epics; do
not fold it into dev without Henry's promotion decision (already taken 2026-07-21, see §2b).

## 2 · Recent deliveries (era pointers — blow-by-blow lives in PRs/issues/git)

- 2026-07-20/21: rebuild epics closed; extender-db Waves 0–3; harness + campaign runner.
- 2026-07-22: ADR 0008 publish lanes (PRs #180–184) · owner's-court rulings executed ·
  `/waves` run (PRs #205/#206/#209/#210; ra-platform adoption left staged uncommitted in
  that repo for owner review) · estate restructure (ADR 0016 lineup, 99-issue reboot,
  `_meta` compliance, `.claude/plugins/` workbench) — PRs #212–214.
- 2026-08-03 (session 1): hook logs/ CWD-scatter fix (#223/PR #224) · architecture review →
  decisions 1+2 ruled · Backlog.md migration (PR #225) · settings prune + closeout (#226).
- **2026-08-03/04 (session 2, this one): the ADR 0017 refactor executed end-to-end** —
  ADR (PR #227) · symlink assemblies + README consolidation + symlink lint (PR #228) ·
  dist/generator retirement + roster slim (PR #229) · opencode install-time lane (PR #230) ·
  governance sweep: backlog/issue split encoded, issue templates → bug-only, flow-guard
  ruling, handoff refresh (PR #231). Tasks 1–4, 7, 8 done; task-25 filed (waves
  backlog-mode); evals/ingest.py repointed to the new surface.

## 2b · Extender-db mini-project (merged to dev 2026-07-21)

PocketBase DB of all agent extenders + the mental models used to compose/evaluate them. **Self-
describing — read `evals/_structure/CHARTER.md`, `PLAN.md`, `OPEN-ITEMS.md`, `evals/README.md`,
`evals/PROCEDURES.md` first**; below is only what they don't carry.

- **State:** Waves 0–3 DONE (9 children closed 2026-07-22 with outcome notes). Remaining
  M3–M6 + excalidraw follow-up now live as backlog task-21 + subtasks 21.1–21.5 (M6 gated
  on M4+M5); note task-6 may re-home the whole family if evals/ extracts.
- **Operational:** server `evals/serve.sh` (admin UI 127.0.0.1:8090/_/); creds in untracked
  `_meta/operations/extender-db.env`. `pb_data/data.db` is TRACKED — stop the server before
  committing (WAL checkpoint) or switching branches (a live server had its tracked data.db
  checked out from under it once; `pgrep -fl pocketbase` → kill → checkout → restart).
  `pb_migrations/` is gitignored on purpose: `schema.py` is the ONE schema source.
- Gotcha list (idless-PATCH column drops, 5000-char text cap, live-proof mandate, scoped deltas,
  json first-byte coercion, file fields need `create_multipart`) lives in `evals/PROCEDURES.md`.

## 2c · Agent-harness (delivered 2026-07-21, PR #169 → dev)

Reusable extender-eval harness at root `harness/` (self-contained uv project): drives Claude Code
or opencode headlessly, grades two-tier, appends to `harness/results.jsonl`. **Self-describing —
read `_meta/research/agent-harness/DESIGN.md`, `harness/README.md` first.** Owner intent:
battle-test here, later extract to its own repo.
- **Auth for live runs:** `export ANTHROPIC_API_KEY="$(secret get ANTHROPIC_API_KEY)"` (per-run
  apiKeyHelper + fresh CLAUDE_CONFIG_DIR — Option Z; `--bare` strips the Skill tool, don't use it).
- **Campaign runner** (PR #178): `make harness-campaign` + weekly LaunchAgent live on this machine
  (Mon 09:00). **Never auto-ingests** — after each run, ingest deliberately
  (`load_harness_runs.py --campaign weekly-YYYYMMDD`) and commit data.db+storage with cause.
- Open follow-up: bug #172 / task-22 (hermeticity/env-pinning).

## 3 · Next up

**Source of truth is the backlog** (`backlog board` / `backlog task list --plain`) — ranked
work, drafts (owner-parked #137/#138/#152), decisions, and the m-0 refactor milestone all
live there, not duplicated here.

- **m-0 remaining = owner's court:** task-5 (publish model — main as merge gate vs
  install-from-dev; publish.yml is deliberately broken till ruled), task-6 (evals/harness
  extraction), task-9 (lineup recomposition — major IA, needs owner sign-off per standing
  directive). The mechanical chain (1–4, 7, 8) is done.
- Buildable without rulings: task-24 (builder maxTurns stall — High), task-23 (waves triage
  template), task-25 (waves backlog-aware mode — new), task-13 (250k-token spike),
  task-15 (handoff-override), task-10 (externals — decisions 1–7 are owner's, mechanism is
  buildable after).
- Note: consumers pointed at `main` still get the pre-0017 dist assembly — functional, just
  frozen at 2026-07-22 until task-5 rules how the pointer surface publishes.
- Parked observation (task-4 notes): opencode discovers `pptx-themes/base/SKILL.md` (the
  vendored Anthropic base) as its own skill — curation call for the task-21 family.
- Cross-repo residue for owner: ra-platform's planning-desk adoption still **uncommitted**
  in `~/Developer/ra-platform` (staged 2026-07-22, needs review/commit + live smoke test);
  the four desk folders in dotfiles-agents-desk likewise uncommitted.
- DEV-TOOLING board #11 carried #36/#152/#154, now all closed on GH — board is stale;
  board's future is wrapped into task-16. Gotcha (if touched): the project auto-adds
  sub-issues unless that workflow is toggled off in the UI.

## 4 · CROSS-REPO — desk-platform design effort (lives on the desk, NOT here)

A separate product design effort on the exec desk (NOT dotfiles-agents): a toolkit integrating AI
agents against one data model across three planes (input · activity · output), PocketBase-backed.
**R3 (element model) drafted + both adversarial reviews done — awaiting Henry's IA approval.**
State lives at `~/Documents/EXECUTIVE_DESK/Projects/ARCHIVE/dev-tooling-desk-old/_meta/plans/
desk-platform/` (`plan.md` = round index; `spec-element-model.md` = the proposal + review
findings). No change this session — still waiting on Henry to approve/adjust/veto the 5 major IA
changes + 4 open questions named in `spec-element-model.md`. Nothing folds into the canonical
model until he signs off (standing directive, §5).

## 5 · Conventions & gotchas

- Source-of-truth rules are in CLAUDE.md (hot-loaded) — not duplicated here.
- **Post-0017 mechanics CLAUDE.md doesn't spell out:** a NEW plugin = a `plugins/<id>/` dir
  + a hand-authored entry in the root marketplace.json; plugin versions are hand-maintained
  now — bump when content changes materially. pptx-themes' skill README carries the
  Anthropic attribution for its vendored `base/` — never split or drop that section.
- **ci.yml job names are frozen** (branch-protection pin): the drift-guards job still reads
  "drift guards (roster · marketplace · catalog)" though it now runs
  `make check symlinks flow` — renaming it strands PRs; change the protection setting first.
- **`main` is publish-only** — never hand-commit/merge there; a CI guard fails PRs into main.
  Branch off `dev`, PR into `dev`. `main` is a **filtered parented assembly** (never a dev
  snapshot — verify with tree hashes per the `publish-to-main` skill runbook).
- **dev's branch-protection required checks are pinned by CI JOB NAME** — renaming a job in
  `ci.yml` strands every PR on a check that never reports. Update the protection setting first.
- **Backlog.md specifics CLAUDE.md doesn't carry:** subtasks get dotted IDs (`task-21.1`) —
  `--depends-on` a subtask must use the dotted form; `make flow` requires a claimed top-level
  path to be *tracked* (stage new dirs before the check passes).
- **Project settings disable product plugins for dev sessions** (code-desk, dataviz, diagrams,
  pptx-themes, github-project-board, mcp-server-dev) — editing their source never needs them
  enabled; flip the entry in `.claude/settings.json` temporarily if a session must *run* one.
- **`flow.yaml` is load-bearing**: `make flow` (in `make ci`) fails any PR that adds a top-level
  path without a declared home. Regenerate the FLOW.md DAG with `scripts/check_flow.py --write-doc`.
- **ADR 0015 (self-authored-only) is now on disk and mechanically enforced**
  (`scripts/check_provenance.py`) — no `origin: sourced` body may live under `primitives-core/`,
  full stop; third-party content must go through `externals.yaml` + the clone-at-build mechanism
  (#36, still unbuilt). This blocked #152 this session — check any future "package an upstream
  skill" ask against this before scoping a wave.
- **`isolation: worktree` Agent calls in this repo have repeatedly checked out from a *published*
  commit instead of `dev`** (5/5 crews this session) — see project memory
  `worktree-agents-check-out-published-commit`. Every worktree-crew brief must include the
  self-check (`primitives-core/` missing → `git reset --hard origin/dev`) until root-caused.
- **Cross-repo crew pattern (new, proven this session):** when a wave's work spans dotfiles-agents
  + a separate consumer repo (e.g. ra-platform), the crew may read/draft in the other repo but
  must leave its changes **uncommitted** there — mutating a second repo's git history is reserved
  to the human, same as `main`. Confirmed working via git worktree isolation; see PR #210.
- Worker agents can drop `.claude/agent-memory/` into whatever directory they worked in — sweep
  stray nested `.claude/` dirs before committing (never whole-dir `git rm` the root `.claude/`).
  Tracked store is `.claude/memory/` (repo root) since #194.
- **Henry signs off on major IA changes before they are finalized/built** (standing directive;
  memory `approve-major-ia-changes`). Present IA changes as an approval gate, not a done deal.
- Machine-local leftover: `evals/pb_data/data.db.local-backup-2026-07-21` (gitignored) —
  reconcile or delete next time a session works in `evals/`.

## 6 · Map

- **`backlog/` — THE task system** (decision-1): tasks, drafts, decisions, milestone m-0.
  `backlog board` for the live view; `backlog task list --plain` for agents. GH issues =
  bug intake only. The waves/pinned-triage loop no longer applies to this repo (its
  backlog-aware successor is part of task-8). Extender-db family: task-21.x (self-manages
  via `evals/_structure/`); harness: task-22.
- CLAUDE.md — task interface + rules · `.github/CONTRIBUTING.md` (new) — human-facing
  contribution loop · `docs/decisions/` — ADR mirrors (now includes 0015).
- **Exec desks:** this repo's desk is `~/Documents/EXECUTIVE_DESK/Projects/dotfiles-agents-desk/`;
  desk-standard work is `.../desk-standard-desk/`; the former dev-tooling-desk (desk-platform
  design) is archived at `.../ARCHIVE/dev-tooling-desk-old/`.
