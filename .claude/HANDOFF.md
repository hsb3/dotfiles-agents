# HANDOFF — dotfiles-agents

_Cold-start bridge. Last updated: 2026-08-06 (session 7). Refresh at session boundaries (/handoff). Secret-free._

_**This file lives at `.claude/HANDOFF.md`** — the third entry in the handoff hooks'
`CANDIDATE_PATHS`, and the two higher-precedence paths are absent, so the hooks resolve it with
no override. META-06 was amended 2026-08-06 to accept that precedence trio (owner sign-off,
decision-8), so this location is standard-conformant; the `handoff` skill's "never relocate"
rule stands overridden by the owner. Task-15's residual scope is the per-project override._

## 0 · Orientation

**What this repo is, the task interface, and every source-of-truth rule live in CLAUDE.md,
already hot-loaded into your context — don't re-read them here.** This file carries only what
CLAUDE.md can't: live state, decisions and their whys, and the gotchas that bite.

The one orientation fact CLAUDE.md doesn't spell out: **publishing works, but the GitHub
Actions path is currently unusable.** See §1 and the fallback in §5.

## 1 · Current standing

- **`dev` tip `3fd5370`**, `make ci` green, 197 tests (145 repo + 41 catalog guard + harness).
- **`main` tip `22af059` = `publish: dev@3fd5370`**, 20-plugin lineup, published 2026-08-06 by
  the **local-worktree fallback** (§5), not the workflow. Parent chain intact (append-only).
- **GitHub Actions is in a declared MAJOR OUTAGE** (githubstatus.com, Actions + Pages), since
  ~16:00 on 2026-08-06. No workflow run is created for new PRs at all. Runs from earlier in the
  outage show the signature: a job `cancelled` with `steps=0` after sitting 15–18 minutes,
  surfacing as a top-level "failure" that is **not** a test failure — check each job's
  `conclusion` via `gh api .../actions/runs/<id>/jobs`, never the run summary.
- **PRs #251 and #253 were merged with `--admin`** on the owner's explicit instruction, gated on
  local `make ci` only. Local `make ci` is a strict superset of CI (CI runs `make floor` and
  `make check symlinks flow`). **If Actions returns, re-run the checks on `dev` before trusting
  the green.**
- GH issue queue: **one open — #250** (see §3). **m-0 is 4/5**; its last box (every open card
  cold-readable with verifiable acceptance criteria, assessed by someone who didn't write it)
  is still unassessed.
- **`feat/atelier` awaits the operator** (worktree `.claude/worktrees/atelier`, branched off
  dev@b35bade). It renames foreman-kit → **atelier** (git mv, both manifests, catalog row,
  live prose; version 0.8.0), lands the lab-01 doctrine rewrite (#252), three new hooks
  (delegation-watermark, config-custody, worker-context — the per-project custody model,
  off by default via `.claude/atelier.local.md`), and 26 hook behavior tests. `make ci`
  green on the branch. **Operator checklist after merge + publish**, in order:
  1. Per project that had foreman-kit installed (re-read `~/.claude/plugins/`
     `installed_plugins.json` — at branch time: dotfiles-agents, EVALS/lab-01-package-inventory,
     pb-task-tracker, plus a user-scope record): `claude plugin uninstall
     foreman-kit@dotfiles-agents`, then `claude plugin install atelier@dotfiles-agents` in that
     project — an enabledPlugins flag alone proves nothing (memory:
     plugin-enablement-needs-per-project-install).
  2. Flip each project's own `enabledPlugins` key to `atelier@dotfiles-agents` (this repo's is
     already done on the branch).
  3. Delete `~/.claude/plugins/cache/dotfiles-agents/foreman-kit/` once no record references it.
  4. Rename any `.claude/foreman-kit.local.md` → `.claude/atelier.local.md` (effort override
     moved there; the file now also carries `enforce:`/`protected:` — see the foreman skill's
     `references/activation.md`).
  5. The ~50 remaining `foreman-kit` mentions (backlog, decisions, memory, evals data shapes,
     this file's history) are deliberate history — do not rewrite them.

Standing mechanisms a cold session should not re-derive: **ADR 0017 pointer refactor is DONE**
(symlink assemblies, `dist/` retired, roster = provenance manifest, opencode install-time);
**`origin: vendored`** (third-party in-tree only under `backlog/docs/vendoring-rule.md`,
machine-checked); **dual-homing** (one `primitives-core/` source symlinked into both a bundle
and a standalone — installing both loads the skill once).

## 2 · Recent deliveries (one line per era — blow-by-blow lives in PRs, issues, git)

- 2026-07-20/22: rebuild epics closed; extender-db Waves 0–3; harness + campaign runner;
  ADR 0008 publish lanes; estate restructure to the ADR 0016 lineup.
- 2026-08-03/04: Backlog.md migration; **ADR 0017 refactor end-to-end** (#227–#231); m-0 rulings
  → decisions 4/5/6; vendoring rule drafted; foreman-kit trio v0.7.0.
- 2026-08-06 (s4/s5): publish repaired (#237); harness isolation (#241); decision-8 (`_meta`
  removed, backlog absorbs docs/); comms freed of `requires: [local-mcp]`; 19-plugin publish.
- 2026-08-06 (s6): **iterm2 skill** (#248, task-030) + first local-fallback publish.
- 2026-08-06 (s7): **marketplace front door rebuilt** (#251) — consumer-first README, 20-row
  catalog, goal-shaped chooser, `scripts/check_catalog.py` drift guard (6 checks, 41 tests,
  rides `make check`). Repaired en route: a mid-word-truncated description, two disagreeing
  manifests, a wrong dual-homing count, an 11-byte-stub link, internal codenames in the picker.
  Repo About box set. Published to `main`. Backlog closeout in #253.

## 2b · Extender-db mini-project (merged to dev 2026-07-21)

PocketBase DB of all agent extenders + the models used to compose/evaluate them.
**Self-describing — read `evals/_structure/CHARTER.md`, `evals/README.md`,
`evals/PROCEDURES.md` first** (the PocketBase gotcha list lives there). Waves 0–3 DONE;
remaining M3–M6 + excalidraw are task-21.x (M6 gated on M4+M5).

- **The one that bites:** `pb_data/data.db` is TRACKED. Stop the server before committing (WAL
  checkpoint) or switching branches. `pb_migrations/` is gitignored on purpose — `schema.py` is
  the ONE schema source. Server: `evals/serve.sh`; creds in untracked
  `.claude/operations/extender-db.env`.

## 2c · Agent-harness (delivered 2026-07-21)

Reusable extender-eval harness at root `harness/` (self-contained uv project). **Self-describing
— read `harness/docs/DESIGN.md`, `harness/README.md` first.** Owner intent: battle-test here,
later extract.

- **Auth for live runs:** `export ANTHROPIC_API_KEY="$(secret get ANTHROPIC_API_KEY)"`
  (per-run apiKeyHelper + fresh CLAUDE_CONFIG_DIR — Option Z; `--bare` strips the Skill tool).
- **Campaign runner** + weekly LaunchAgent (Mon 09:00). **Never auto-ingests** — ingest
  deliberately after each run and commit data.db + storage with cause.
- **No dry-run exists**, so a smoke test **appends to the tracked `results.jsonl`** — restore
  from HEAD afterwards. Residuals in task-27.

## 3 · Next up

**Source of truth is the backlog** (`backlog board` / `backlog task list --plain`) — ranked
work, drafts, and decisions live there, not duplicated here.

- **Issue #250 — foreman-kit telemetry — is the owner's stated next-session pickup.** Three
  reproduced defects: `agent_type` empty in 122/134 ledger rows; `model` records the *parent
  session's* model (60/60 rows in one session said Opus while sonnet builders ran); `ctx_tokens`
  tracks the parent's growing context; and row count ran ~10× the delegation count. Net: the kit
  cannot measure its own delegation behavior. The issue also carries six hypotheses for why a
  foreman-led session still retains delegable labor — **fix the telemetry first, because none of
  the hypotheses are measurable until it records the delegation.** Also filed there: four
  concurrent foreman-kit installs across three scopes with 0.7.1 and 0.7.2 both enabled at
  `local` — a live candidate root cause for the skills-not-reaching-sessions investigation.
- **New from s7:** **TASK-032** (High — no gate ties published bytes to a version bump; edit one
  dual-homed skill body and every plugin shipping it changes while CI stays green),
  **TASK-033** (Low, sequenced behind Claude Code per owner direction — the opencode installer's
  cleanup trap deletes its own exclusions record; users get 25 of 34 skills and no hooks,
  silently), **TASK-034** (agent definitions are Claude-Code-native; needs a harness-agnostic
  profile — **first deliverable is the decision, not code**).
- **m-0's last box** — a cold-read assessment of every open card, judged by someone who didn't
  write it.
- **task-15** (handoff-location override) half resolved: META-06 amended, residual scope is
  **draft-005**. Two owner-requested scoping drafts landed 2026-08-06: **draft-004** (extender
  information architecture) and **draft-005** (per-project settings overrides). Promoting
  draft-004 into its decision is the natural next scoping move.
- Buildable, no ruling needed: task-25, task-13, task-14, task-27, task-28, task-29.
- Cross-repo residue for the owner: ra-platform's planning-desk adoption is still
  **uncommitted** in `~/Developer/ra-platform`; the four desk folders in dotfiles-agents-desk
  likewise. Committing in a consumer repo is the human's call.

## 4 · CROSS-REPO — desk-platform design effort (lives on the desk, NOT here)

A separate design effort on the exec desk. **Parked on the owner's IA approval** (R3 element
model + both adversarial reviews done; 5 IA changes + 4 open questions await a ruling). Full
state: `~/Documents/EXECUTIVE_DESK/Projects/ARCHIVE/dev-tooling-desk-old/_meta/plans/desk-platform/`.
Unchanged since 2026-08-04.

## 5 · Conventions & gotchas

- **Publish fallback — now the proven path, used twice (2026-08-06, sessions 6 and 7).** When
  Actions is down, reproduce `publish.yml` by hand in scratch worktrees so the real tree never
  touches `main`:
  1. `git worktree add <scratch>/dev-publish origin/dev --detach` → `make ci` (the gate).
  2. **Version pre-flight** — diff each plugin's dereferenced bytes against `origin/main` **in
     both directions** (a one-way pass once missed a newly-added file), pruning `__pycache__`
     and `*.pyc` first, and confirm every changed plugin has a bumped version.
  3. Assemble per the lift map in `publish.yml`: `cp -RL plugins`, `.claude-plugin/marketplace.json`,
     `README.md`, `.gitignore` into a tempdir.
  4. `git worktree add <scratch>/main-publish origin/main --detach` → `git checkout -B publish-tree
     origin/main` → `git rm -rfq . && git clean -fdq` → copy the assembled tree in → `git add -A`
     → commit `publish: dev@<short-sha>` (body = plugin name/version list) →
     `git push origin HEAD:refs/heads/main`.
  5. Verify: `git ls-tree --name-only origin/main` is distributable-only, tip reads
     `publish: dev@<sha>`. Then `git worktree remove --force` both, and delete the leftover
     local `publish-tree` branch the fallback creates (`git branch -D publish-tree`) — it
     reappears every run and otherwise reads as a branch carrying unmerged work.
  The shipped `.gitignore` is what keeps `__pycache__` out of the published tree — don't drop it.
- **`main` is a filtered parented assembly, never a snapshot of `dev`** — never diff the two
  whole-tree; the published `plugins/` are dereferenced regular files where dev's are symlinks.
- **`ci.yml` fires on `pull_request` ONLY.** A commit pushed straight to `dev` gets zero CI.
- **CI job names are frozen** — dev's branch protection pins required checks by job NAME, so
  renaming one strands every PR on a check that never reports. A new gate rides an existing target.
- **A version bump IS the release step, and version fields lie.** Consumers cache by version.
  Diff the bytes, in both directions. Bump in BOTH `plugins/<id>/.claude-plugin/plugin.json` and
  `.claude-plugin/marketplace.json`. `check_catalog.py` now enforces *parity* between the two,
  but **nothing yet ties changed bytes to a bump** — that's TASK-032. Keep `ensure_ascii=True`
  when editing those files programmatically.
- **`make ci`'s `✗ opencode laydown — refusing…` line is a passing test's own output.** Judge by
  exit code, never by ✗ glyphs.
- **Don't trust `logs/delegation.jsonl`** until #250 is fixed — it records the parent session.
- **Branch hygiene now lives in CLAUDE.md** (merge-or-abandon within the session, check
  `git rev-list --count origin/dev..<branch>` before deleting, and the `chore/handoff`
  `--ff-only` loop). Two things that bit on 2026-08-06 and are the reason it is written down:
  deleting the unmerged `chore/handoff-backlog-refresh` reverted task-030 to To Do while the
  iterm2 skill stayed shipped and published, and `gh pr merge --delete-branch` fails outright
  on a dirty working tree because it switches branches.
- **Backlog writes go through the `backlog` CLI / MCP tools** (owner ruling). Avoid two sessions
  writing the backlog at once.
- **Backlog.md specifics:** subtasks get dotted IDs (`task-21.1`) and `--depends-on` needs the
  dotted form; `make flow` requires a claimed top-level path to be *tracked*.
- **No unguarded counts in prose or repo metadata** (owner rule 2026-08-06) — a count needs a
  gate that reads it, or phrase it so growth can't falsify it. Guarded numbers are fine (the
  README catalog's `Contents` column is checked against disk). Rationale in project memory
  `no-unguarded-counts-in-prose`.
- **A new plugin** = a `plugins/<id>/` dir + a hand-authored root marketplace.json entry;
  versions are hand-maintained. pptx-themes' skill README carries the Anthropic attribution for
  its vendored `base/` — never split or drop that section.
- **The checklist↔audit contract is a CLOSED type vocabulary, and `make ci` never runs the
  compliance audit.** A checklist row using a new check type hard-breaks the shipped audit for
  every repo while local gates stay green. A new TYPE is an audit-script change; prove checklist
  edits with a real `audit.py` run. Known residue: IGNORE-01 still probes `_meta/operations/`.
- **`isolation: worktree` Agent calls here have repeatedly checked out from a *published* commit
  instead of `dev`** — every worktree-crew brief needs the self-check (`primitives-core/` missing
  → `git reset --hard origin/dev`). Prefer disjoint file ownership over worktrees.
- Worker agents drop `.claude/agent-memory/` into whatever dir they worked in — sweep the
  specific stray path, never whole-dir `git rm` the root `.claude/` (it holds HANDOFF.md and the
  tracked memory store).
- **Never mutate a second repo's git history** — read/draft in a consumer repo, leave changes
  uncommitted there.
- **`flow.yaml` is load-bearing**: `make flow` fails any PR adding a top-level path without a
  declared home. Regenerate the DAG doc with `scripts/check_flow.py --write-doc`.
- **ADR 0015 (self-authored-only) is mechanically enforced**; third-party content goes through
  `externals.yaml` reference-only or the vendoring exception gated by
  `backlog/docs/vendoring-rule.md`.
- **Project settings disable product plugins for dev sessions** (code-desk, dataviz, diagrams,
  pptx-themes, github-project-board, mcp-server-dev) — editing their source never needs them
  enabled; flip the entry in `.claude/settings.json` temporarily to *run* one.
- **The owner signs off on major IA changes before they are built.** Present them as an approval
  gate, not a done deal.
- Stale local file to reconcile or delete when next in `evals/`:
  `evals/pb_data/data.db.local-backup-2026-07-21` (gitignored).

## 6 · Map

- **`backlog/` is THE task system** (decision-1) — GH issues are bug intake only. The
  waves/pinned-triage loop no longer applies here; its backlog-aware successor is task-25.
- Docs: CLAUDE.md (rules) · `.github/CONTRIBUTING.md` (human contribution loop) ·
  `backlog/decisions/` (ADR mirrors + backlog rulings) · `backlog/docs/vendoring-rule.md`.
- **Exec desks:** `~/Documents/EXECUTIVE_DESK/Projects/dotfiles-agents-desk/` (this repo);
  `.../desk-standard-desk/`; `.../ARCHIVE/dev-tooling-desk-old/` (desk-platform design).
