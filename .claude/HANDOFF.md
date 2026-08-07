# HANDOFF — dotfiles-agents

_Cold-start bridge. Last updated: 2026-08-07 (session 9). Refresh at session boundaries (/handoff). Secret-free._

_**This file lives at `.claude/HANDOFF.md`** — the third entry in the handoff hooks'
`CANDIDATE_PATHS`, and the two higher-precedence paths are absent, so the hooks resolve it with
no override. META-06 was amended 2026-08-06 to accept that precedence trio (owner sign-off,
decision-8), so this location is standard-conformant; the `handoff` skill's "never relocate"
rule stands overridden by the owner. Task-15's residual scope is the per-project override._

## 0 · Orientation

**What this repo is, the task interface, and every source-of-truth rule live in CLAUDE.md,
already hot-loaded into your context — don't re-read them here.** This file carries only what
CLAUDE.md can't: live state, decisions and their whys, and the gotchas that bite.

The one orientation fact CLAUDE.md doesn't spell out: **the GitHub Actions outage declared
2026-08-06 is resolved** — the publish workflow ran clean end-to-end (both the gate and the
push) on the next two dispatches. See §1.

## 1 · Current standing

- **`dev` tip `5f3a2b2`**, `make ci` green, **375 tests** (was 230 two sessions ago).
- **`main` tip `cb2333b` = `publish: dev@5f3a2b2`**, **22-plugin** lineup, published 2026-08-07
  by the `publish.yml` workflow. Parent chain intact (append-only).
- **The GH issue queue is EMPTY.** All four that were open (#250, #254, #255, #256) were fixed
  and closed 2026-08-07; #252 had been closed earlier. **Note the trap that hid this before:**
  `Closes #N` in a PR body does **nothing** here, because GitHub only auto-closes on the
  *default* branch and this repo merges into `dev` while `main` is publish-only. Close issues
  explicitly or they linger looking open after the fix ships.
- **Branch state is clean**: only `chore/handoff`, `dev`, `dev-legacy`, `main` remain, and there
  are no leftover worktrees. `feat/atelier` and its stale worktree are gone — see §5 for what
  that worktree was hiding.
- **m-0's last box is now assessed** (TASK-035): a cold read of all 31 open cards by four
  assessors who authored none of them. AC#1/#2 are deliberately left unchecked — the audit is
  done and every failing card is named with its defect, but those criteria require the failing
  cards to be *rewritten*, and several rewrites are still open. See §3.
- **Session 9 (2026-08-07) closed 13 cards and filed 4.** Closed: TASK-6, 15, 16, 17, 20, 28,
  032, 035(partial), 036, 037, 038, 039, 040, 11.01. Filed: TASK-041 (board reporting),
  TASK-042 (trim `surfaces.md`), TASK-043 (**blocked — needs a ruling**, see §3), TASK-044
  (opencode hook translation).
- **The atelier operator checklist from session 8 is still yours to run** and is unchanged by
  session 9, except that the versions moved: install **atelier 0.9.0**, not 0.8.0.
  1. Per project that had foreman-kit installed (re-read `~/.claude/plugins/`
     `installed_plugins.json` — at branch time: dotfiles-agents, EVALS/lab-01-package-inventory,
     pb-task-tracker, plus a user-scope record): `claude plugin uninstall
     foreman-kit@dotfiles-agents`, then `claude plugin install atelier@dotfiles-agents` in that
     project — an enabledPlugins flag alone proves nothing (memory:
     plugin-enablement-needs-per-project-install).
  2. Flip each project's own `enabledPlugins` key to `atelier@dotfiles-agents` (this repo's is
     already done).
  3. Delete `~/.claude/plugins/cache/dotfiles-agents/foreman-kit/` once no record references it.
  4. Rename any `.claude/foreman-kit.local.md` → `.claude/atelier.local.md`. That file now also
     carries `handoff:` (new in session 9) alongside `effort:`/`enforce:`/`protected:` — the
     full schema is in the foreman skill's `references/activation.md`.
  5. Consider installing the new **`plugin-feedback`** plugin alongside atelier — it is the
     mechanism for reporting plugin defects and only fires where it is installed.
  6. The remaining `foreman-kit` mentions (backlog, decisions, memory, evals data shapes, this
     file's history) are deliberate history — do not rewrite them.
- **GitHub Actions is healthy.** The 2026-08-06 outage is long resolved; every PR this session
  got a real CI run in 7–16s. The §5 local-worktree fallback stays documented for the next
  outage but has been dormant since session 8. `--admin` merges are historical.

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
- 2026-08-07 (s9): **full backlog sweep** — 13 cards closed, 4 filed, GH issue queue emptied,
  two PRs (#266, #267) plus closeouts (#268), published as `dev@5f3a2b2`. Highlights, each with
  a captured red run: the delegation ledger now records subagents not the parent (#250, verified
  by replaying the live 262-row ledger to 29 rows, exactly the sidecar count on disk); a
  **version-bump gate** now fails CI when published bytes change under an unchanged version
  (TASK-032); `scout` rewritten (turn cap removed, brief-granted read-only shell); `reviewer`'s
  stray-write bug root-caused to a **frontmatter key**, not behavior (#254); a `handoff:`
  per-project override (TASK-15); and the new **`plugin-feedback`** plugin (TASK-11.01).
  Adversarial review before merging that plugin caught a consumer-facing defect and two tests
  that could not fail — see §5.
- 2026-08-06 (s8): **Actions outage resolved**; confirmed via a live `publish.yml` dispatch,
  then again publishing #260. **`feat/atelier` (#260) merged and published** — foreman-kit
  renamed to atelier 0.8.0, lab-01 doctrine rewrite (#252), delegation-watermark +
  config-custody + worker-context hooks. Verified against the open foreman-kit issues (§3):
  #252 substantially closed by the PR (closed on GH with the finding-by-finding check); #250,
  #254, #255, #256 filed as backlog tasks TASK-036/037/038/039 (still open). Found and fixed a
  real bug while filing them: `check_flow.py` mis-parsed any tracked path with non-ASCII bytes
  (git's default path quoting corrupted the top-level-segment split) — `git ls-files -z` fix +
  5 regression tests, PR #263. TASK-040 filed (are `claude-code-config`/`claude-code-expertise`
  one plugin's worth of overlap?). Designed and scoped **TASK-11.01** (plugin-feedback hooks —
  see §3) at the owner's request, but did not build it — refreshing context first by design.

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

**Blocked on the owner, and nothing else is:**

- **TASK-043 — needs a ruling before any build.** The owner asked for "a plugin that
  distributes all skills that can stand on their own", alongside ruling that lab-setup ships
  standalone. Those read two ways and cost very differently. *Additive*: the existing one-skill
  plugins stay and this is an aggregate convenience install — cheap, reversible, but every
  standalone skill becomes dual-homed. *Replacing*: the aggregate becomes the shape and the
  per-skill plugins retire — a breaking marketplace change across most entries, dangling every
  install record, with no alias mechanism in this marketplace's shape. Both readings are written
  out on the card. **Do not start TASK-043 or the lab-setup move until this is settled.**
  Second open question on the same card: "can stand on their own" needs a mechanical definition.
  `check_symlinks` now encodes a standalone rule, but that describes an *assembly*, not a skill's
  self-sufficiency — a skill referencing a sibling by path is not standalone-capable however it
  is packaged.

**Rulings taken 2026-08-07 and recorded on their cards — implement without re-asking:**
TASK-032 (gate rides the existing drift-guards CI job — **done**), TASK-15 (`.claude/atelier.local.md`
key — **done**), TASK-037/038 (**done**), TASK-29 (standalone home — build blocked on TASK-043),
TASK-034 (take the decision now, build later), TASK-033 (split; TASK-044 carries the open
question), TASK-12 (its own skill, not folded into `claude-code-config`), TASK-6 (**extraction
plan withdrawn, card closed** — `evals/` and `harness/` stay; the owner will raise it if that
changes).

**Buildable now, no ruling needed:** TASK-042 (trim `surfaces.md` — the de-duplication behind
the three shipped defects s9 fixed), TASK-041 (board reporting), TASK-033's mechanical half (the
opencode installer's cleanup trap deletes its own exclusions record, so users silently get a
subset), TASK-25 (**now has seven acceptance criteria** drafted for owner review — it had none),
TASK-12, TASK-18, TASK-19, TASK-27, TASK-13 (**sequenced behind TASK-036**, now unblocked — but
the pre-fix ledger history is unusable, so let post-fix delegations accumulate first).

**Needs a live billed run:** TASK-21.3, TASK-21.5. **Needs the PocketBase server:** TASK-21.1,
TASK-21.2, TASK-21.4. Only 21.1/21.2/21.4 are independently startable; 21.3 gates on 21.2 and
21.5 gates on both.

**TASK-035 residue:** the cold-read audit is complete but its first two criteria stay unchecked
because several failing cards still need rewriting — TASK-12's undefined "defensible", TASK-21.4's
undefined "works", TASK-11's sentence-satisfiable "or explicit disposition", TASK-21.1's
unprovable "never overwritten". The recurring authoring defect worth watching: **criteria phrased
as "Either X… or Y…"**, which defers the decision *into* the criterion and makes it unverifiable
until someone rules. TASK-037 and TASK-038 both had it.

**One thing shipped but never observed live:** nobody has confirmed `SubagentStart` fires in a
real session with `plugin-feedback` installed. If the event were not honored the worker tier
would be silently inert and every test would still pass, since they assert only on the hook's
stdout. `worker-context` already ships on that event via atelier, which is corroboration, not
proof. One live dispatch closes it.

**Cross-repo residue for the owner:** ra-platform's planning-desk adoption is still
**uncommitted** in `~/Developer/ra-platform`; the four desk folders in dotfiles-agents-desk
likewise. Committing in a consumer repo is the human's call.

## 4 · CROSS-REPO — desk-platform design effort (lives on the desk, NOT here)

A separate design effort on the exec desk. **Parked on the owner's IA approval** (R3 element
model + both adversarial reviews done; 5 IA changes + 4 open questions await a ruling). Full
state: `~/Documents/EXECUTIVE_DESK/Projects/ARCHIVE/dev-tooling-desk-old/_meta/plans/desk-platform/`.
Unchanged since 2026-08-04.

## 5 · Conventions & gotchas

- **Publish fallback — proven twice (2026-08-06, sessions 6 and 7), dormant since the outage
  resolved in session 8.** Kept documented for the next outage, not the active path — session 8
  published twice through the real `publish.yml` workflow instead. When Actions is down again,
  reproduce `publish.yml` by hand in scratch worktrees so the real tree never touches `main`:
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
- **`Closes #N` in a PR body does nothing here.** GitHub auto-closes only on the *default*
  branch, and PRs merge into `dev` while `main` is publish-only. Close issues explicitly, or a
  shipped fix leaves its issue sitting open. This is why four issues looked open for a day
  after being fixed.
- **`make ci` is no longer the whole gate.** `scripts/check_version_bump.py` runs **only in CI**,
  as a step inside the existing drift-guards job, because it needs network to reach `origin/main`
  and `make ci` is offline by design. Run it by hand before assuming a green `make ci` means a
  green PR. Offline it skips clean rather than blocking.
- **An agent's `memory:` frontmatter key makes the runtime create a directory**, before the agent
  does anything. `memory: project` resolves to `<cwd>/.claude/agent-memory/<agentType>/`. The
  enum is `user | project | local` with no `off` value, so **omitting the key is the only way to
  disable it** — no prose in an agent body can prevent the `mkdir`. No atelier agent sets it as
  of 2026-08-07, so a fresh `agent-memory/` dir now means some other agent definition carries it.
- **`scout` is no longer Bash-less** (2026-08-07). It cannot write files — `Edit`/`Write` are
  still absent, so that half is structural — but shell authority is now prompt-enforced: a brief
  must name the exact read-only commands it grants. Granting one is a real decision. Its
  `maxTurns` cap is also gone, so scout briefs may now budget honestly.
- **Adversarially review a new plugin before merging it.** On `plugin-feedback` this paid for
  itself: it found that reports about third-party plugins would be filed into *this* repo
  silently, and mutation-tested two tests that could not fail — one of which passed while the
  stray file it checked for sat on disk. A builder's self-report is a hypothesis.
- **`ls` is aliased to `eza`** in this shell; `ls <dir>` fails on the `--icons` flag. Use
  `/bin/ls` in scripted checks.
- **`logs/delegation.jsonl` is trustworthy from 2026-08-07 onward, but its history is not.**
  The parent-session defect (#250) is fixed: rows now source `agent_type`/`model` from the
  subagent's own `subagents/agent-<id>.meta.json` sidecar and `ctx_tokens` from its transcript,
  and a prospective row with no matching sidecar is dropped. Pre-fix rows recorded the parent and
  ran ~9x inflated, so **truncate or archive the file before any tier analysis** — pre- and
  post-fix rows are not comparable, and the history is not salvageable (the subagent identity was
  never captured). The file is gitignored, so this costs no gate.
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
  → `git reset --hard origin/dev`). Prefer disjoint file ownership over worktrees; session 9 ran
  ~15 concurrent workers on one tree with no worktrees at all and no collisions, purely by
  assigning each an owned file list and forbidding `make`/git.
- **A stale worktree can hide finished work indefinitely.** `.claude/worktrees/atelier` sat for a
  day holding ~100 uncommitted lines documenting atelier's configuration surface, while the
  shipped README described 4 of its 7 hooks. Nothing surfaces this: `git status` in the main tree
  is clean, and the branch reads as merged. **Run `git worktree list` at session start**, and
  check each one's `git -C <path> status` before assuming a branch is disposable. The content was
  recovered and shipped in s9; both the worktree and `feat/atelier` are now gone.
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
