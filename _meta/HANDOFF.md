# HANDOFF — dotfiles-agents

_Cold-start bridge. Last updated: 2026-08-06. Refresh at session boundaries (/handoff). Secret-free._

## 0 · Orientation

dotfiles-agents is a marketplace of coding-agent extenders serving TWO runtimes from one
source tree (ADR 0017): Claude Code installs the hand-authored symlink assemblies under
`plugins/<id>/` (root `.claude-plugin/marketplace.json`) natively; opencode is generated at
install time (`scripts/install_opencode.sh`). **Nothing generated is tracked.** `dev` =
source, `main` = CI-published (publish-only). **Publishing WORKS** (fixed 2026-08-06, PR #237):
the release gate is the filtered parented assembly — decision-4 was amended to ratify it (its
original "plain fast-forward" wording violated its own evals/harness exclusion). Publish =
`gh workflow run publish.yml --ref dev -f confirm=publish` per the publish-to-main skill. Task
interface + source-of-truth rules: see CLAUDE.md (hot-loaded).

## 1 · Current standing

`make ci` green — 95 repo tests + 139 harness tests (41 primitives: agent=4, hook=4, skill=33).
GH issue queue: **zero open** (both bugs fixed + closed 2026-08-06). Standing:

- **ADR 0017 pointer refactor DONE** (m-0 tasks 1–4, 7, 8; PRs #227–#231). 15 symlink
  assemblies + root marketplace.json (`make symlinks`); `dist/` + generators retired; roster =
  provenance manifest; opencode is install-time. Mechanics live in CLAUDE.md (hot-loaded).
- **m-0 owner's-court rulings CLEARED 2026-08-04** (decisions 4/5/6, via an owner-signoff form
  — trail in `_meta/signoff/2026-08-03-backlog-ordering/`):
  - **task-5 publish** = DONE 2026-08-06: decision-4 amended (assembly-gate ratified, owner
    sign-off), publish.yml fixed (#237), proven by two publishes.
  - **task-6 extraction** = extract evals/+harness/ eventually but **deferred** — dev is the
    workbench; they never publish to main (decision-5). Parked (Low).
  - **task-9 lineup** = comms-first approved **in principle**, gated on a design pass I still
    owe (ADR bundle-composition extension + code-desk dispositions).
  - **task-10 externals** = **pinned-vendored-copy**, not clone-at-install (decision-6);
    supersedes #36/ADR 0003; drop the 4 plugin externals, only pptx stays vendored; new
    `origin: vendored` class + narrow ADR 0015 amendment. Memo:
    `_meta/plans/externals-clone-vs-vendor/memo.md`. Build **unblocked** (task-26 done).
- **Board repaired to decision-7** (2026-08-06, PR #242, owner sign-off in
  `_meta/signoff/2026-08-06-backlog-standards/`): minimum task-definition standard ruled; 8
  stub cards rewritten from their closed GH issues; stale statuses flipped (5, 22, 23, 24, 26
  all Done); m-0 gained a checkable definition of done (2/5 ticked).

`main` is current: `publish: dev@a7d87ac` (2026-08-06), foreman-kit **0.7.1** live. The
publish surface is only `plugins/` + marketplace.json + README — backlog/harness merges since
don't need a re-publish.

Live marketplace lineup (ADR 0016, 15 plugins): **code-desk (0.3.0)** ·
**foreman-kit (0.7.1** — review-cycle trio #235; waves triage-ordering fix #240**)** · diagrams · obsidian-toolkit · 11 standalones (claude-code-config ·
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
- 2026-08-03/04 (session 2): ADR 0017 refactor executed end-to-end (PRs #227–#231) — symlink
  assemblies, dist/generator retirement, opencode install-time lane, governance sweep.
- 2026-08-04 (session 3): m-0 rulings via owner-signoff form → decisions 4/5/6; backlog
  regrouped (#234); task-24 maxTurns fix (#233); externals memo + ruling (#236); vendoring
  rule drafted (#238); foreman-kit trio v0.7.0 (#235).
- **2026-08-06 (session 4, this one): publish repaired + bugs cleared + board standard.**
  #237 publish fix + #238 vendoring rule merged; two publishes (main current, foreman-kit
  0.7.1). Waves triage bug fixed (#240, closed #215). Harness isolation fixed lead-driven
  (#241, closed #172; suite 102→139 tests; residuals → task-27). decision-7 task standard +
  full board repair (#242, owner sign-off). decision-4 amended (assembly-gate ratified).

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
- **Isolation fixed 2026-08-06** (#241, task-22): claude runner now truly isolated (throwaway
  HOME/config, `--setting-sources ""`, loud failure over silent host-config fallback);
  preconditions recorded in ledger + log header; `--keep-workspaces`; flat `agents/<name>.md`
  resolves in-package. Residuals in task-27: scratch-ledger/--dry-run mode (evidence runs
  append to tracked results.jsonl — restore from HEAD if you smoke-test), vision-grader
  assertion recording.

## 3 · Next up

**Source of truth is the backlog** (`backlog board` / `backlog task list --plain`) — ranked
work, drafts (owner-parked #137/#138/#152), decisions, and the m-0 refactor milestone all
live there, not duplicated here.

- m-0 remaining (its DoD now lives in the milestone file): **task-10 externals build** (High,
  unblocked — ACs enumerate the full scope) → task-11 sits on it; **task-9 design pass**
  (session-owed): ADR bundle-composition extension + code-desk dispositions for owner ratify
  BEFORE build; board-conformance box ticks itself as cards stay clean.
- Buildable, no ruling needed: task-15 (handoff-override, High), task-25 (waves backlog-aware),
  task-13 (250k-token spike), task-14 (coord-branch protocol), task-27 (harness residuals).
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
- The backlog-CLI hand-edit-only rule is now IN CLAUDE.md + decision-7 (the CLI rewrote
  sibling task files from a stale index, 2026-08-04) — read-only CLI use (`list`/`board`) fine.
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
- **ADR 0015 (self-authored-only) is mechanically enforced** (`scripts/check_provenance.py`);
  third-party content goes through `externals.yaml` reference-only or the vendoring exception
  gated by `docs/vendoring-rule.md` (decision-6; enforcement arm = task-10's build). Check any
  "package an upstream skill" ask against the rule doc before scoping.
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
  backlog-aware successor is task-25). Extender-db family: task-21.x (self-manages
  via `evals/_structure/`); harness: task-22.
- CLAUDE.md — task interface + rules · `.github/CONTRIBUTING.md` (new) — human-facing
  contribution loop · `docs/decisions/` — ADR mirrors (now includes 0015).
- **Exec desks:** this repo's desk is `~/Documents/EXECUTIVE_DESK/Projects/dotfiles-agents-desk/`;
  desk-standard work is `.../desk-standard-desk/`; the former dev-tooling-desk (desk-platform
  design) is archived at `.../ARCHIVE/dev-tooling-desk-old/`.
