# HANDOFF — dotfiles-agents

_Cold-start bridge. Last updated: 2026-08-03. Refresh at session boundaries (/handoff). Secret-free._

## 0 · Orientation

dotfiles-agents is a Claude Code marketplace of coding-agent extenders, assembled from
`primitives-core/` into plugin bundles by `scripts/gen_marketplace.py`. `dev` = source, `main` =
CI-published (publish-only, ADR 0014). Task interface + source-of-truth rules: see CLAUDE.md (hot-loaded).

## 1 · Current standing

`make ci` green (38 primitives: agent=4, hook=4, skill=30). Two big 2026-08-03 rulings now
govern everything:

1. **Task system = Backlog.md** (`backlog/` tree; backlog decision-1). GitHub issues are
   bug-report intake ONLY — 22 issues migrated + closed, triage issue #192 closed/unpinned,
   3 bug reports open (#172/#215/#222 ↔ work items task-22/23/24). PR #225 (merged
   2026-08-03) carries the `backlog/` tree + flow node; PR #226 the session closeout.
2. **Architecture: one repo, pointer-based distribution** (backlog decision-2). Verified
   against plugin docs + a live PoC: plugins become symlink assemblies over
   `primitives-core/`, root `.claude-plugin/marketplace.json`, NO tracked dist; opencode
   generates at install time. Planned as tasks 1–9 (milestone m-0); **task-1 (the ADR) is
   the critical path** — the dist/generator/publish machinery stays as-is until it lands.

`main` published 2026-07-22 at `dev@0cdca55` — lags `dev` (incl. the merged hook fix
PR #224); publish model itself is under revision (task-5), so publishing now is optional.

Live marketplace lineup (post ADR 0016 recomposition, 2026-07-22): **code-desk (0.3.0)** — the
sole desk bundle, now including planning-desk, comms, board-triage, pptx-themes (former
exec-desk, retired) — · foreman-kit (0.6.0) · diagrams · obsidian-toolkit · 11 standalones:
github-project-board · opencode-expertise · pptx-themes · private-fork · **project-memory**
(absorbed memory-taxonomy) · owner-signoff · claude-code-expertise · dataviz · deep-research ·
**claude-code-config** (renamed from update-config) · **tech-eval-research** (new). `main` lags
`dev` until next publish.

**Also live: the extender-db mini-project** (§2b) — separate effort from the rebuild epics; do
not fold it into dev without Henry's promotion decision (already taken 2026-07-21, see §2b).

## 2 · Recent deliveries (era pointers — blow-by-blow lives in PRs/issues/git)

- 2026-07-20/21: rebuild epics closed; extender-db Waves 0–3; harness + campaign runner.
- 2026-07-22: ADR 0008 publish lanes (PRs #180–184) · owner's-court rulings executed ·
  `/waves` run (PRs #205/#206/#209/#210; ra-platform adoption left staged uncommitted in
  that repo for owner review) · estate restructure (ADR 0016 lineup, 99-issue reboot,
  `_meta` compliance, `.claude/plugins/` workbench) — PRs #212–214.
- **2026-08-03 (this session):** hook logs/ CWD-scatter bug fixed (#223, PR #224, merged) ·
  triage #192 refreshed, then superseded same-day · architecture review (DAG audit, docs
  verification, live symlink PoC) → decisions 1+2 ruled · Backlog.md migration executed
  (PR #225) · project settings pruned to dev-relevant plugins.

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

- **Critical path: merge PR #225, then task-1 (the pointer-architecture ADR, owner-approval
  gate).** Tasks 2–9 hang off it. Owner offered a draft; not started.
- Buildable independent of the ADR: task-24 (builder maxTurns stall — High), task-23 (waves
  template), task-13 (250k-token spike, telemetry ledger now exists).
- Decisions embedded in tasks, owner's court: task-5 (publish model), task-6 (evals/harness
  extraction), task-10 (externals decisions 1–7), task-15 (handoff-override mechanism).
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
- **`main` is publish-only** — never hand-commit/merge there; a CI guard fails PRs into main.
  Branch off `dev`, PR into `dev`. `main` is a **filtered parented assembly** (never a dev
  snapshot — verify with tree hashes per the `publish-to-main` skill runbook).
- **dev's branch-protection required checks are pinned by CI JOB NAME** — renaming a job in
  `ci.yml` strands every PR on a check that never reports. Update the protection setting first.
- **PRs into `dev` do NOT auto-close their `Closes #N` issues** — auto-close only fires on the
  *default* branch (`main`). **Close bug issues by hand after every merge into dev.**
- **Backlog.md specifics:** subtasks get dotted IDs (`task-21.1`), so `--depends-on` a subtask
  must use the dotted form; `auto_commit: false` — backlog CLI writes are committed by the
  session like any file edit; `make flow` requires a claimed top-level path to be *tracked*
  (stage `backlog/` before the check passes).
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
- **Never check out `main` locally** — a PreToolUse hook denies it in agent sessions; a
  machine-local `post-checkout` hook warns on manual checkouts.
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
