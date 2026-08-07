# HANDOFF — dotfiles-agents

_Cold-start bridge. Last updated: 2026-08-07 (session 9). Refresh at session boundaries (/handoff). Secret-free._

_**This file lives at `.claude/HANDOFF.md`** — the third entry in the handoff hooks'
`CANDIDATE_PATHS`, with the two higher-precedence paths absent, so the hooks resolve it with no
override. META-06 was amended 2026-08-06 to accept that trio (decision-8), so this location is
conformant and the `handoff` skill's "never relocate" rule is satisfied by leaving it here._

## 0 · Orientation

**Everything about what this repo is, the task interface, and the source-of-truth rules lives in
CLAUDE.md, which is hot-loaded into your context already — do not restate it here.** This file
carries only what CLAUDE.md cannot: live state, decisions and their whys, and the gotchas that bite.

## 1 · Current standing

- **`dev` `3eb1177`** · **`main` `a3b81c4` = `publish: dev@d08a346`** · 22 plugins ·
  `make ci` green · **375 tests** · zero open GH issues · clean tree · no worktrees.
- **BREAKING, published 2026-08-07 — the delegation vocabulary was renamed.** Skill
  `atelier:foreman` → **`atelier:delegation`**; agent `lead` → **`manager`**. Anything using the
  old ids fails silently: saved aliases, another repo's briefs, a stored command. The doctrine now
  names three **layers** — strategy (role `strategist`, the session itself, never spawnable),
  management (`manager`), execution (`scout`/`builder`/`reviewer`) — and **three layers is the
  default for non-trivial work**, inverting guidance that had called the middle layer avoidable cost.
- **Operator checklist, still yours to run** (install **atelier 0.10.0**): per project that had
  `foreman-kit`, `claude plugin uninstall foreman-kit@dotfiles-agents` then
  `claude plugin install atelier@dotfiles-agents` **in that project** (an `enabledPlugins` flag
  alone proves nothing — memory: `plugin-enablement-needs-per-project-install`); flip that
  project's `enabledPlugins` key; delete the stale
  `~/.claude/plugins/cache/dotfiles-agents/foreman-kit/`; rename any
  `.claude/foreman-kit.local.md` → `.claude/atelier.local.md` (it now also carries `handoff:` —
  schema in the delegation skill's `references/activation.md`); consider installing
  **`plugin-feedback`**, which only fires where installed. Remaining `foreman` mentions in
  `backlog/`, decisions, and memory are deliberate history — **do not rewrite them**.

Standing mechanisms not to re-derive: **ADR 0017** (symlink assemblies, `dist/` retired, roster =
provenance manifest, opencode generated at install time); **`origin: vendored`** (third-party
in-tree only under `backlog/docs/vendoring-rule.md`, machine-checked); **dual-homing** (one
`primitives-core/` source symlinked into two assemblies loads the skill once).

## 2 · Recent deliveries — one line per era; blow-by-blow lives in PRs, issues, git

- 2026-07-20/22: rebuild epics closed; extender-db Waves 0–3; harness + campaign runner;
  ADR 0008 publish lanes; estate restructure to the ADR 0016 lineup.
- 2026-08-03/04: Backlog.md migration; **ADR 0017 refactor end-to-end**; m-0 rulings → decisions
  4/5/6; vendoring rule drafted.
- 2026-08-06: publish repaired; harness isolation; decision-8; iterm2 skill; **marketplace front
  door rebuilt** (consumer-first README, catalog drift guard); **foreman-kit renamed to atelier**
  with the lab-01 doctrine rewrite and three new hooks.
- 2026-08-07 (s9): **backlog sweep + delegation layers.** 15 cards closed, 6 filed, issue queue
  emptied, published twice. Landed: the delegation ledger now records subagents not the parent
  (#250); a **version-bump gate**; `scout` rewritten; `reviewer`'s stray writes root-caused;
  a `handoff:` override; the **`plugin-feedback`** plugin; and the **three-layer rewrite**
  (TASK-045). Filed: TASK-041/042/043/044/046/047.

**Sub-projects, both self-describing — read their own docs first.** `evals/` (PocketBase extender
DB): `evals/README.md`, `_structure/CHARTER.md`, `PROCEDURES.md`. Waves 0–3 done; M3–M6 are
TASK-21.x. **`pb_data/data.db` is TRACKED — stop the server before committing or switching
branches**; creds in untracked `.claude/operations/extender-db.env`. `harness/` (uv project):
`harness/docs/DESIGN.md`; live runs need `export ANTHROPIC_API_KEY="$(secret get ANTHROPIC_API_KEY)"`.
**No dry-run exists, so a smoke test appends to the tracked `results.jsonl`** — restore from HEAD
after (TASK-27).

## 3 · Next up

**Source of truth is the backlog** (`backlog board` / `backlog task list --plain`).

**Start here — analysis done, build unstarted: TASK-043**, one plugin holding every
standalone-capable skill. Owner ruled the **replacing** reading: the per-skill plugins retire.
**Do not redo the inventory** — it is on the card: **27 eligible, 3 not**. Three facts decide the
build's shape, all recorded there:
1. **Eligibility cannot be read from metadata.** None of the ineligible skills was caught by the
   roster's `requires:` field — two hardcode a sibling's path inside a bundled Python script. A
   membership gate must read bodies and scripts.
2. `marketplace.json`'s `metadata.description` enumerates all seventeen standalone plugins **by
   name** and the catalog guard verifies them. Red until rewritten.
3. **`check_symlinks`' standalone branch loses every subject** and can never fire again. It
   shipped the same day (TASK-28). Retire it or keep it with a stated reason.
Accepted cost: retiring an entry dangles every install record, and there is no alias mechanism.

**Nothing else is blocked on the owner** — every question asked on 2026-08-07 was ruled.
Recorded on their cards and ready to implement without re-asking: TASK-034 (decide now, build
later; adopt `strategist` as the primary profile name), TASK-033 (split — TASK-044 holds the open
hooks-to-opencode question), TASK-12 (its own skill), TASK-29 (standalone home, but sequenced
behind TASK-043).

**Buildable now:** TASK-042 (trim `surfaces.md` — the de-duplication behind three shipped defects),
TASK-041, TASK-047, TASK-033's mechanical half, TASK-25 (now has criteria drafted for review),
TASK-18, TASK-19, TASK-27, TASK-046. **TASK-13 is unblocked but wait** — it reads the delegation
ledger, whose pre-2026-08-07 history is unusable, so let post-fix rows accumulate first.

**Needs a live billed run:** TASK-21.3, TASK-21.5. **Needs the PocketBase server:** TASK-21.1,
TASK-21.2, TASK-21.4 (only these three are independently startable).

**TASK-035 residue:** the cold-read audit is done and every failing card is named, but its first
two criteria stay unchecked because several cards still need rewriting. The recurring authoring
defect to watch: **criteria phrased "Either X… or Y…"**, which defers the decision into the
criterion and makes it unverifiable until someone rules.

**Never observed live:** nobody has confirmed `SubagentStart` fires with `plugin-feedback`
installed. If the event were unhonored the worker tier is silently inert and every test still
passes, since they assert only on stdout. One live dispatch closes it.

**Cross-repo, the owner's call:** ra-platform's planning-desk adoption is uncommitted in
`~/Developer/ra-platform`; the four desk folders in dotfiles-agents-desk likewise.

## 4 · CROSS-REPO — desk-platform design (on the desk, NOT here)

Parked on the owner's IA approval; unchanged since 2026-08-04. Full state:
`~/Documents/EXECUTIVE_DESK/Projects/ARCHIVE/dev-tooling-desk-old/_meta/plans/desk-platform/`.

## 5 · Conventions & gotchas

**Publishing**

- **`main` is a filtered, parented assembly, never a snapshot of `dev`.** Never whole-tree diff
  them: published `plugins/` are dereferenced regular files where dev's are symlinks.
- **A version bump IS the release step.** Consumers cache by version. Bump in BOTH
  `plugins/<id>/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`; keep
  `ensure_ascii=True` when editing them programmatically.
- **A dual-homed edit needs a bump on EVERY plugin shipping it.** Editing one cross-reference in
  `planning-desk` changed `code-desk`'s bytes while only `atelier` was bumped. `make members` maps
  primitive → plugins.
- **`make ci` is NOT the whole gate.** `scripts/check_version_bump.py` runs CI-only (it needs
  network for `origin/main`). Run it by hand before assuming green `make ci` means green PR.
  Offline it skips clean rather than blocking.
- **If Actions is down**, reproduce `publish.yml` by hand in *scratch worktrees* so the real tree
  never touches `main` — the workflow file is the spec; follow its lift map. Proven twice on
  2026-08-06, dormant since. Delete the leftover local `publish-tree` branch afterward.

**CI and gates**

- **`ci.yml` fires on `pull_request` ONLY.** A commit pushed straight to `dev` gets zero CI.
- **CI job names are frozen** — branch protection pins required checks by NAME, so a new gate must
  ride an existing job.
- **`make ci`'s `✗ opencode laydown — refusing…` line is a passing test's own output.** Judge by
  exit code, never by ✗ glyphs.
- **`Closes #N` does nothing here.** GitHub auto-closes only on the *default* branch and PRs merge
  into `dev`. Close issues explicitly, or a shipped fix leaves its issue open.
- **The checklist↔audit contract is a CLOSED type vocabulary, and `make ci` never runs the
  compliance audit.** A new check TYPE is an audit-script change; prove checklist edits with a real
  `audit.py` run. Residue: IGNORE-01 still probes `_meta/operations/`.
- **`flow.yaml` is load-bearing** — `make flow` fails any PR adding an unhomed top-level path.
  Regenerate the doc with `scripts/check_flow.py --write-doc`.

**Agents and delegation**

- **"Layer" ≠ "tier".** Layer = org structure (strategy/management/execution). Tier = the model
  (haiku/sonnet/opus), the whole subject of `references/tier-cutoff.md`. Collapsing them re-creates
  the ambiguity the rename removed.
- **The `[field]` provenance tag** = observed in practice by the owner, not yet reproduced under
  measurement. Outranks `[untested]`, never outranks `[lab]`/`[cost]`. Carries the three-layer
  default until TASK-046 settles it. **Do not defend one as a measurement, or discard one as a
  guess** — both gut the tag's purpose.
- **An agent's `memory:` frontmatter key makes the RUNTIME create a directory** before the agent
  acts (`memory: project` → `<cwd>/.claude/agent-memory/<agentType>/`). The enum has no `off`
  value, so omitting the key is the only disable — no prose in an agent body can stop the `mkdir`.
  No atelier agent sets it as of 2026-08-07, so a fresh one means some other definition carries it.
- **`scout` is no longer Bash-less.** It still cannot write files (`Edit`/`Write` absent — that half
  is structural), but shell authority is prompt-enforced: a brief must name the exact read-only
  commands it grants. Its `maxTurns` cap is gone, so scout briefs may budget honestly.
- **A skill can name an agent that does not exist and nothing catches it** (TASK-047:
  `board-triage` documents a `board-analyst` "(this plugin)" that is in no roster). Check agent
  names against the roster by hand until a gate exists.
- **Prefer disjoint file ownership over worktrees.** Session 9 ran ~15 concurrent workers on one
  tree with zero collisions, purely by giving each an owned file list and forbidding `make`/git.
  `isolation: worktree` calls here have repeatedly checked out a *published* commit instead of
  `dev` — any worktree brief needs the self-check (`primitives-core/` missing → `git reset --hard
  origin/dev`).
- **Adversarially review a new plugin before merging.** On `plugin-feedback` it found that
  third-party reports would file into this repo silently, and mutation-tested two tests that could
  not fail — one passed while the stray file it checked for sat on disk.
- **`logs/delegation.jsonl` is trustworthy from 2026-08-07 on, its history is not.** Pre-fix rows
  recorded the parent session at ~9x inflation and are unsalvageable. Truncate or archive before any
  tier analysis. Gitignored, so this costs no gate.
- **The ledger's `agent_type` vocabulary changed on 2026-08-07** — rows written before the rename
  say `lead`, rows after say `manager`. Any analysis spanning that boundary must map them or it
  will read one agent as two. Compounds with the pre-fix history problem above.
- **`/reload-plugins` misreports skills as `0`** — observed 2026-08-07 reporting
  "8 plugins · 0 skills · 11 agents · 7 hooks" while the skills were in fact loaded and usable.
  This is #250's D4, previously unverified. Trust the skill list, not the count.

**Repo hygiene**

- **A stale worktree can hide finished work indefinitely.** One sat for a day holding ~100
  uncommitted lines of documentation while the shipped README described 4 of 7 hooks; `git status`
  in the main tree stayed clean and the branch read as merged. **Run `git worktree list` at session
  start** and check each one's status before assuming a branch is disposable.
- Worker agents may drop `.claude/agent-memory/` into their working dir — sweep the specific stray
  path, **never** whole-dir `git rm` the root `.claude/` (it holds this file and the tracked memory).
- **Stranded agent-memory is TASK-048**, a one-time migration rather than a standing hazard: the
  `memory:` frontmatter key that created those directories is gone from every agent, so the pile is
  finite. Two of the three files carry real verification lessons and are candidates for promotion
  into `.claude/memory/`; the card says to judge each on the store's bar rather than promoting both
  by default.
- **Never mutate a second repo's git history** — read/draft in a consumer repo, leave it uncommitted.
- **No unguarded counts in prose or metadata** (owner rule) — a count needs a gate that reads it, or
  phrase it so growth cannot falsify it.
- **A new plugin** = a `plugins/<id>/` dir + a hand-authored root marketplace.json entry.
  pptx-themes' skill README carries the Anthropic attribution for its vendored `base/` — never split
  or drop that section.
- **Project settings disable product plugins for dev sessions** — editing their source never needs
  them enabled; flip the entry in `.claude/settings.json` temporarily to *run* one.
- **The owner signs off on major IA changes before they are built.** Present them as an approval
  gate, not a done deal.
- Backlog specifics beyond CLAUDE.md: `--depends-on` needs the dotted subtask form (`task-21.1`);
  `make flow` requires a claimed top-level path to be *tracked*; avoid two sessions writing the
  backlog at once.

## 6 · Map

- **`backlog/` is THE task system** (decision-1) — GH issues are bug intake only.
- Docs: CLAUDE.md (rules) · `.github/CONTRIBUTING.md` (human loop) · `backlog/decisions/` (ADR
  mirrors + rulings) · `backlog/docs/vendoring-rule.md`.
- **Exec desks:** `~/Documents/EXECUTIVE_DESK/Projects/dotfiles-agents-desk/` (this repo);
  `.../desk-standard-desk/`; `.../ARCHIVE/dev-tooling-desk-old/` (desk-platform design).
