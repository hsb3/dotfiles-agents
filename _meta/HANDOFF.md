# HANDOFF — dotfiles-agents

_Cold-start bridge. Last updated: 2026-08-06 (session 5). Refresh at session boundaries (/handoff). Secret-free._

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

`make ci` green — 145 repo tests + 139 harness tests (41 primitives: agent=4, hook=4, skill=33).
GH issue queue: **zero open**. **m-0 is 4/5 done** — only "board conforms to decision-7" is
open, and it wants an assessor who did NOT write the cards.

**⚠ dev is 7 commits ahead of the published main and NONE of them has been through CI.**
`ci.yml` triggers on `pull_request` only, and session 5's work was committed straight to `dev`
instead of via a branch+PR (a deviation from CLAUDE.md's own SDLC rule). Verification so far is
local `make ci` only. The fix is in flight: the PR carrying this handoff runs `make ci` over a
tree containing all of it — **that green run is the pre-promotion gate.** Do not promote before
it reports. Standing:

- **ADR 0017 pointer refactor DONE** (m-0 tasks 1–4, 7, 8; PRs #227–#231) — symlink assemblies,
  `dist/`+generators retired, roster = provenance manifest, opencode install-time. Mechanics
  are in CLAUDE.md (hot-loaded); don't restate them here.
- **m-0 owner's-court rulings all cleared** (decisions 4/5/6 on 2026-08-04, decision-7 board
  standard 2026-08-06; sign-off trails under `_meta/signoff/`). Tasks 5, 9, 10 are Done — the
  live residue is **task-6**: extract `evals/` + `harness/` eventually, but **deferred** by
  decision-5 (dev is the workbench; neither ever publishes to main). Parked at Low.
- **Two mechanisms this repo now enforces that a cold session should not re-derive:**
  `origin: vendored` (third-party in-tree only under `docs/vendoring-rule.md`, contract
  machine-checked) and **dual-homing** (one `primitives-core/` source, symlinked into both a
  bundle and a standalone plugin — installing both loads the skill once).

**`main` is STALE by design-in-progress**: `publish: dev@a7d87ac` still ships the **15-plugin
0.3.0** lineup. dev carries **19 plugins / 0.4.0**. Promotion is pending the CI gate above —
it is the next real deliverable, not a background chore. The publish surface is only
`plugins/` + marketplace.json + README, so backlog/harness/test churn never needs a republish;
this time the surface genuinely changed (4 new plugin dirs + marketplace rewrite).

Live-on-main lineup (15): code-desk 0.3.0 · foreman-kit 0.7.1 · diagrams · obsidian-toolkit ·
11 standalones. **Unpublished additions on dev (4):** comms · mise-en-place-scaffold ·
readme-value-and-proof · repo-meta-structure — each a standalone assembly over a skill that
also stays in code-desk (dual-home; one source, two symlinks, loads once).

**Also live: the extender-db mini-project** (§2b) — separate effort from the rebuild epics; do
not fold it into dev without Henry's promotion decision (already taken 2026-07-21, see §2b).

## 2 · Recent deliveries (era pointers — blow-by-blow lives in PRs/issues/git)

- 2026-07-20/22: rebuild epics closed; extender-db Waves 0–3; harness + campaign runner;
  ADR 0008 publish lanes (#180–184); `/waves` run (#205/#206/#209/#210); estate restructure
  to the ADR 0016 lineup (#212–214).
- 2026-08-03/04 (sessions 1–3): decisions 1+2 ruled; Backlog.md migration (#225); **ADR 0017
  refactor end-to-end** (#227–#231); m-0 rulings → decisions 4/5/6 (#236); vendoring rule
  drafted (#238); foreman-kit trio v0.7.0 (#235); task-24 maxTurns fix (#233).
- 2026-08-06 (session 4): publish repaired (#237) + vendoring rule (#238) + waves triage fix
  (#240, closed #215) + harness isolation (#241, closed #172; residuals → task-27) +
  decision-7 board standard (#242, owner sign-off); decision-4 amended; two publishes.
- **2026-08-06 (session 5, this one): m-0 build-out — task-10 + task-9 shipped, comms freed.**
  Externals mechanism built; lineup recomposed to 19 plugins / marketplace 0.4.0; **comms lost
  its `requires: [local-mcp]`** — it now ships `scripts/render_deck.py`, a stdlib-only renderer
  (validate → self-contained HTML → headless-Chrome PDF) covering all 17 deck block types,
  proven against 22 real decks / 256 slides across three repos. Repo suite 95 → 145 tests.
  Filed task-28 (README-symlink gate gap). Six commits went **straight to dev** — see §1.

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
- Isolation fixed 2026-08-06 (#241, task-22) — runner is genuinely isolated now. **Residuals in
  task-27**, one of which bites: there is no dry-run, so a smoke test **appends to the tracked
  `results.jsonl`** — restore from HEAD afterwards.

## 3 · Next up

**Source of truth is the backlog** (`backlog board` / `backlog task list --plain`) — ranked
work, drafts (owner-parked #137/#138/#152), decisions, and the m-0 refactor milestone all
live there, not duplicated here.

- **PROMOTION is the live thread.** Order: (1) the handoff PR's CI goes green — that is the
  only CI coverage this work has; (2) review the 4 new plugin dirs as a *published surface*
  (they ship to consumers, unlike backlog/test churn); (3) `publish-to-main` skill runbook →
  `gh workflow run publish.yml --ref dev -f confirm=publish`; (4) verify main lands on 19
  plugins / 0.4.0 and spot-check one new standalone installs.
- m-0's last box — **board conforms to decision-7** — is deliberately NOT self-certified:
  session 5 edited tasks 9, 10, 28 and the milestone, so it needs an assessor who did not
  write them.
- Buildable, no ruling needed: task-15 (handoff-override, High), task-25 (waves backlog-aware),
  task-13 (250k-token spike), task-14 (coord-branch protocol), task-27 (harness residuals),
  task-28 (README-symlink gate), task-29 (promote `lab-setup` from the EVALS workbench).
- **Open investigation (owner-staged):** `_meta/plans/plugin-skills-not-loading/issue-body.md`
  — foreman-kit skills not reaching sessions. Cross-reference before filing: project memory
  `plugin-enablement-needs-per-project-install` found that install records are keyed on
  `projectPath`, and the staged repro runs from `~/Developer`, not a path with a foreman-kit
  install record. Same root cause is a live hypothesis, NOT confirmed — the report notes hooks
  *are* running there, which that theory doesn't obviously explain. Check before filing.
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
- **`ci.yml` fires on `pull_request` ONLY.** A commit pushed straight to `dev` gets zero CI —
  no run, no red, no signal. This bit session 5 (six commits, local `make ci` the only proof).
  Branch + PR is not a style preference here; it is the only path that runs the gates.
- **CI job names are frozen** — dev's branch-protection required checks are pinned by job NAME,
  so renaming one in `ci.yml` strands every PR on a check that never reports (change the
  protection setting first). This is why the drift-guards job still reads "drift guards
  (roster · marketplace · catalog)" while actually running `make check symlinks flow`.
- **A plugin needs an install record for THIS `projectPath`, not just `enabledPlugins: true`.**
  `claude plugin list` happily reports another project's record as "enabled". Fix:
  `claude plugin install <id>@<marketplace> --scope local` from inside the repo, **then restart
  the session** — `/reload-skills` does not pick up a newly installed plugin. Full detail in
  project memory `plugin-enablement-needs-per-project-install`.
- **A sign-off item that contradicts a prior ruling must SAY SO in the item.** Session 5's
  design pass recommended keeping comms bundled — silently reversing the owner's own
  comms-first direction and the task's AC — and it was approved as a preselected default. The
  approval was worthless because the form never surfaced the conflict. Trail + standing lesson:
  `_meta/plans/task-9-lineup/design-pass.md`.
- **Scope a rewrite from the real corpus, not the in-repo samples.** The comms renderer was
  first sized off this repo's 2 sample decks (6 block types) and would have refused real
  briefings using `steps`/`table`/`timeline`. A census over `_meta/briefings/` in three repos
  found 17 types in use. Same shape of error as the point above: a confident guess, unverified.
- **`main` is publish-only** — never hand-commit/merge there; a CI guard fails PRs into main.
  Branch off `dev`, PR into `dev`. `main` is a **filtered parented assembly** (never a dev
  snapshot — verify with tree hashes per the `publish-to-main` skill runbook).
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
- **Never mutate a second repo's git history** — read/draft in a consumer repo (ra-platform,
  functionform-headcase, …) but leave changes **uncommitted** there; committing is the human's,
  same as `main`. Session 5 followed this when testing the deck renderer against real briefings.
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
