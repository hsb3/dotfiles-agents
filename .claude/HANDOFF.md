# HANDOFF — dotfiles-agents

_Cold-start bridge. Last updated: 2026-08-11 (session 18). Refresh at session boundaries (/handoff). Secret-free._

_**This file lives at `.claude/HANDOFF.md`** — third entry in the handoff hooks'
`CANDIDATE_PATHS`, higher-precedence paths absent, so the hooks resolve it with no override
(META-06 as amended by decision-8). Do not relocate._

## 0 · Orientation

**Everything about what this repo is, the task interface, and the source-of-truth rules lives in
CLAUDE.md, which is hot-loaded already — do not restate it here.** This file carries only live
state, decisions with their whys, and the gotchas that bite.

## 1 · Current standing

- **`dev` `cb1b441`** · **`main` `e50753e` = `publish: dev@cb1b441`** (payload-verified:
  kaneo 0.9.1 on main carries the importer fix) · **7 plugins** · **59 primitives** ·
  `make ci` green (exit 0, 571 tests) · no worktrees. Re-read `gh issue list` live — the
  queue fills from other repos with zero activity here.
- **THE TRACKER IS THE KANEO BOARD** (decision-011, owner ruling 2026-08-11): project
  **DFA / dotfiles-agents** `l2k5zzte5qo9amu79tr8e6iy`, workspace hsb3
  `6DfGLeeKlTRArM24iKqeZCQ0v2BZWBq0`. Backlog.md is fully retired (#317): no `backlog/`,
  no label gate, no CLI workflow block in AGENTS.md. Standing law rehomed to `docs/`
  (flow node `repo-law`); ADRs at `docs/decisions/`.
- **Session credentials are wired**: five `KANEO_*` values in gitignored
  `.claude/settings.local.json`; identity = agent account `dotfiles-agents@agents.local`
  (the instance's FIRST per-repo agent; creds also on the Railway roster as
  `DOTFILES_AGENTS_*`). MCP token expires ~2026-09-10; on 401 re-mint per the kaneo skill.
  A session started before 2026-08-11 evening has no board tools — headers expand at
  process start only.
- Open GH issues 13 as of the last look; #308/#309 closed (shipped in 0.9.0/#310), #301
  closed duplicate of #282, #299/#300/#306 triaged onto cards (now board tasks
  TASK-067/068).

## 2 · Recent deliveries — one line per era; blow-by-blow in PRs, issues, git

- 2026-07-20/08-06: rebuild epics; ADR 0016/0017 restructure; publish repaired;
  marketplace front door; foreman-kit → atelier.
- 2026-08-07 (s9–s13): backlog sweep; 22 marketplace entries → 6 (`solo-skills`);
  version-bump gate; `plugin-feedback`; worktree-isolation; plugin-README diagram gate.
- 2026-08-11 (s15–s16): `comment-hygiene`; `kaneo` adopted as 7th plugin, first `mcp`
  primitive, availability guards.
- 2026-08-11 (s17): kaneo 0.9.0 — mint script shipped in-skill, preflight
  shadow-registration catch, api.md corrections, `onboard_repo.py`; five repos migrated
  onto one board.
- 2026-08-11 (s18): **this repo migrated to the board and Backlog.md retired end-to-end.**
  #315 handoff parked; issue triage (2 cards, 3 closures); **#316 importer fix — the
  SECTION regex missed the bare `<!-- AC:BEGIN -->` dialect, so the first import dropped
  every AC/notes/plan/comments section; kaneo 0.9.1**; board wiped + re-imported
  losslessly (101 items, 79/79 ACs verified against source markers) + 3 milestone tasks;
  **#317 retirement** (law → `docs/`, decision-011 supersedes decision-1); published
  `dev@cb1b441` → main. Agent account minted; meta board register/decision/repair-task
  updated.

**Sub-projects, self-describing — read their own docs first.** `evals/` (PocketBase extender
DB): `evals/README.md`, `_structure/CHARTER.md`. **`pb_data/data.db` is TRACKED — stop the
server before committing**; creds in untracked `.claude/operations/`. `harness/` (uv):
`harness/docs/DESIGN.md`; live runs need `ANTHROPIC_API_KEY`; **no dry-run — a smoke test
appends to tracked `results.jsonl`** (board task, was TASK-27).

## 3 · Next up

**Source of truth is the board — read lane counts live, never from here.** Imported titles
keep `TASK-NNN:` prefixes; milestones are the three `Milestone m-N:` tasks; member cards
carry `Milestone: m-N` under Source Metadata.

- **Users actually waiting:** TASK-052 (plugin-feedback can't file feature requests — #282
  still open) and TASK-053 (two shipped READMEs teach the ignored flat `worktreeBaseRef`).
- **Sequencing judgment kept from the cards:** TASK-042 (trim surfaces.md) highest-leverage;
  TASK-049 waits on TASK-034's profile decision; TASK-13 waits for ledger rows.
  Needs a live billed run: TASK-21.3/21.5. Needs the PocketBase server: TASK-21.1/21.2/21.4.
- **Meta board (workspace `meta` VZWoU4ImwHL99wPAhLqVF6JHRG3wfm71, project MIG
  `qb6wjtyagke9bmg9n9mcm159`) holds the migration program**: runbook, conventions, API
  gotchas, status register, and the open **high-priority repair task — the five boards
  migrated before the #316 fix (PBTT/APIA/MSS/DAPI/AZR) are missing every AC/notes/plan/
  comments section; their source repos still hold the truth.** Also open there: per-repo
  agent keys for those five, mhi-raptorxai workspace, ~15 remaining repos.
- **kaneo-ops residue (second repo, owner's call):** `~/Developer/kaneo` ops repo still
  lists `kaneo` in its own marketplace.json and carries `plugins/kaneo/` — two copies
  exist; needs its entry dropped and README pointed here. Never mutate it unprompted.
- **`plugin-feedback` SubagentStart tier still unconfirmed** — if the event is unhonored
  the tier is silently inert and every test passes. Close with the headless probe recipe
  (§5) rather than waiting for an organic dispatch.

## 4 · Owner's court

- **`.env.example`** (untracked, repo root): looks copy-pasted — duplicate KANEO header,
  unrelated TELEGRAM placeholders. Confirm intent before tracking; flagged 2026-08-11,
  unanswered.
- **Should §5 move out of this file?** Still open (asked 2026-08-07, re-raised 2026-08-11).
  With `docs/` now homed as `repo-law`, a `docs/gotchas.md` with a pointer here is the
  natural landing — but that is an IA change and needs the owner's word. Until then this
  file runs over the skill's ~200-line ceiling on purpose.
- ra-platform planning-desk adoption uncommitted in `~/Developer/ra-platform`; desk-platform
  design parked at `~/Documents/EXECUTIVE_DESK/Projects/ARCHIVE/dev-tooling-desk-old/`.
- `~/Developer/kaneo` (ops repo) still carries the uncommitted test-bed changes from s16/s17
  (settings.json plugin install record; disabledMcpjsonServers in settings.local.json).

## 5 · Conventions & gotchas

**Publishing**

- **A plugin is the UNIT OF INSTALLATION.** Never accept "make skills individually
  installable" — correct the premise (progressive disclosure makes bundles cheap).
- **Retiring a marketplace entry breaks consumers' registrations** — migration is
  remove-and-re-add the marketplace, not merely uninstall.
- **`main` is a filtered, parented assembly** — never whole-tree diff against dev;
  published `plugins/` are dereferenced files where dev's are symlinks. Audit a publish by
  the `publish: dev@<sha>` commit on main, NEVER by the Actions run — **a re-run reuses
  the original run id and `created_at`, and its `head_sha` lies** (observed 2026-08-11).
- **A version bump IS the release step** — bump BOTH `plugins/<id>/.claude-plugin/plugin.json`
  and `.claude-plugin/marketplace.json`, by targeted string replace (the files disagree on
  unicode escaping; a json.dump rewrite silently re-encodes). A dual-homed edit bumps EVERY
  plugin shipping the primitive (`make members`).
- **`make ci` is NOT the whole gate** — `scripts/check_version_bump.py` is CI-only; run it
  by hand before assuming green.

**CI and gates**

- **`ci.yml` fires on `pull_request` ONLY.** Direct pushes to `dev` get ZERO CI; the owner's
  waiver (docs/memory/handoff-only) means `remote: Bypassed rule violations` is expected —
  run `make ci` locally first, nothing else will. Code still goes through a PR.
- **CI job names are frozen** — branch protection pins checks by NAME; new gates ride
  existing jobs.
- **`make ci`'s `✗` lines are passing tests' own output. Judge by exit code only.** Fixture
  runs say "1 primitives"; the real repo says 59. This trap produced a false "3 pre-existing
  failures" handoff claim on 2026-08-11 — re-run before inheriting any red-tree claim.
- **A heuristic that passes its tests can still be mostly wrong — measure against a corpus**
  (replay over git history; use a stdlib parser as oracle where one exists). Proved twice:
  comment-hygiene-gate (79% precision found by replay) and the kaneo importer (tests used a
  marker dialect no real Backlog.md writes — **a gate can have zero real subjects and stay
  green**; deliberate forward-guards must say so in their docstring).
- **`comment-hygiene-gate` has real subjects here** (~41 findings in 25 files: evals/,
  externals.yaml, workflow YAML) — it firing on commits is the gate working; cleanup uncarded.
- **`git diff` appends a TAB to `+++ b/<path>` when the path contains spaces** —
  `docs/decisions/*.md` filenames have spaces; split on `\t` before using the name.
- **PROBE the harness instead of reasoning about it**: headless run in a throwaway repo,
  prompt on **stdin** — `printf '<prompt>' | claude -p --settings <f> --model haiku
  --permission-mode acceptEdits --allowedTools "Agent,Bash,Read"`. For undocumented
  schemas grep `strings ~/.local/share/claude/versions/<v>`. (#297's false conclusion came
  from inferring via a YAML lib; the real gap — no gate parses agent frontmatter — keeps
  #297 open.)
- **`Closes #N` does nothing here** (auto-close is default-branch only; PRs merge to dev).
  Close issues explicitly.
- **`flow.yaml` is load-bearing** — `make flow` fails unhomed top-level paths; regenerate
  the doc with `scripts/check_flow.py --write-doc`. The hand-maintained table below the
  generated block is separately stale (board task).
- **DERIVE a set, never consume a recorded one** — a card/report handing you an inventory
  is a hypothesis (TASK-043: recorded 27, derived 30).

**Kaneo board** (workflow law = the kaneo skill; instance specifics = meta board docs)

- REST `GET`s must NOT send a `Content-Type` header with no body — the instance 400s.
  `PUT /task/{id}` rejects `"userId": null` — omit the key.
- `GET /task/export/{projectId}` omits task ids — keep the onboarding `--state` file
  (`.claude/operations/kaneo-migration-state.json`, source-id → board-id) or use the board
  view `GET /task/tasks/{projectId}`.
- The label endpoint returns one row per ATTACHMENT; statuses are per-project column slugs
  (this board's Document lane slug is `document`; PBTT's is `documents`).
- `claude mcp list` does not apply project settings env — diagnose MCP from a session.
  `--allowedTools` on a probe hides tools from the model; a NONE answer is not absence.
- Plugin MCP servers: installing the plugin IS the trust decision (no approval dialog);
  a plugin's root `.mcp.json` auto-merges (a string `mcpServers` key means an MCPB path —
  don't use it); `/mcp disable` writes `plugin:<p>:<s>` into `~/.claude.json` per-project
  and survives everything; a direct `kaneo` registration outranks the plugin's and a
  headerless one silently OAuths as the human owner (preflight catches it).
- `claude plugin install --scope project` writes the TRACKED settings.json — use
  `--scope local` in repos you don't own.

**Agents and delegation**

- "Layer" (strategy/management/execution) ≠ "tier" (model). `[field]` provenance tag =
  owner-observed, outranks `[untested]`, never outranks `[lab]`/`[cost]`.
- An agent `memory:` frontmatter key makes the RUNTIME mkdir before the agent acts; no
  atelier agent sets it — a fresh `.claude/agent-memory/` means some other definition does.
- Prefer disjoint file ownership over worktrees (s9: ~15 concurrent workers, zero
  collisions). **A worktree cannot see uncommitted work** — never isolate a reviewer/scout
  aimed at an uncommitted diff; builders commit first or dispatch un-isolated.
- Worktree base ref = nested `worktree.baseRef` (flat `worktreeBaseRef` is silently
  ignored — two shipped READMEs still teach it, TASK-053/#292). Unset defaults to `fresh`
  off origin/main — wrong here.
- **A stalled manager looks exactly like a dead one** (#285/TASK-054): before taking over
  a manager's git steps, check `gh pr list` and `git log` for work it landed since you
  looked, or you race it. Related, distinct: **worker completion notifications route to
  the top session, not the spawning manager** (#299/#306, board TASK-067) — silent
  deadlock; top-session relay is the field workaround.
- Adversarially review a new plugin AND a builder's report — s18's reviewer confirmed all
  mechanical claims but caught an unsuperseded decision left readable as current truth.
- `logs/delegation.jsonl` history before 2026-08-07 is untrustworthy (9x inflation,
  `lead` naming) — truncate before analysis. No time axis at all until TASK-068 lands.
- `/reload-plugins` misreports skills as 0; it also never respawns MCP servers — config
  changes need a full process quit.

**Docs, diagrams, hygiene**

- Every plugin README carries a Mermaid diagram (`docs/readme-diagram-standard.md`,
  gated) — draw the trigger and flow, never the inventory. **mermaid-cli exits 0 on
  render failure** — assert `test -s out.svg` and check labels reached the SVG.
- **Run `git worktree list` at session start** — a stale worktree can hide finished work
  while `git status` stays clean.
- **No unguarded counts in prose/metadata** (owner rule) — a count needs a gate or a
  growth-proof phrasing.
- New plugin = `plugins/<id>/` + hand-authored marketplace.json entry. pptx-themes README
  keeps its Anthropic attribution section — never drop it.
- Never mutate a second repo's git history. Removing a marketplace via `/plugin` deletes
  its entries from tracked `enabledPlugins` (correct here; know it elsewhere).

## 6 · Map

- CLAUDE.md/AGENTS.md (law, hot-loaded) · `.github/CONTRIBUTING.md` (human loop) ·
  `docs/decisions/` (ADRs + rulings) · `docs/` (FLOW.md, vendoring-rule,
  readme-diagram-standard, extender-dev-sop).
- Boards: DFA (this repo) + MIG/meta (migration program) on
  `kaneo-production-5641.up.railway.app`.
- Exec desks: `~/Documents/EXECUTIVE_DESK/Projects/dotfiles-agents-desk/` ·
  `.../desk-standard-desk/` · `.../ARCHIVE/dev-tooling-desk-old/`.
