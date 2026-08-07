# HANDOFF — dotfiles-agents

_Cold-start bridge. Last updated: 2026-08-07 (session 12). Refresh at session boundaries (/handoff). Secret-free._

_**This file lives at `.claude/HANDOFF.md`** — the third entry in the handoff hooks'
`CANDIDATE_PATHS`, with the two higher-precedence paths absent, so the hooks resolve it with no
override. META-06 was amended 2026-08-06 to accept that trio (decision-8), so this location is
conformant and the `handoff` skill's "never relocate" rule is satisfied by leaving it here._

## 0 · Orientation

**Everything about what this repo is, the task interface, and the source-of-truth rules lives in
CLAUDE.md, which is hot-loaded into your context already — do not restate it here.** This file
carries only what CLAUDE.md cannot: live state, decisions and their whys, and the gotchas that bite.

## 1 · Current standing

- **`dev` `8ea83ba`** · **`main` `a3b904e` = `publish: dev@8ea83ba`** · **6 plugins** ·
  `make ci` green · **413 tests** · zero open GH issues · no worktrees.
- **`dev` and `main` are IN SYNC — nothing unpublished.** `atelier` **0.11.0** (the
  `worktree-isolation` hook, #286, TASK-050) published 2026-08-07 (session 12) via
  `publish-to-main`; consumers pick it up on their next plugin update.
- **Two BREAKING renames published 2026-08-07; old ids fail SILENTLY.** (1) The marketplace went
  22 entries → 6: all seventeen one-skill plugins retired into one aggregate, **`solo-skills`**
  (30 skills), the five bundles untouched. **Per-skill installation no longer exists** and no
  aggregate can restore it (§5); `mise-en-place-scaffold` is the exception, living only inside
  `code-desk`. (2) The delegation vocabulary: skill `atelier:foreman` → **`atelier:delegation`**,
  agent `lead` → **`manager`**. Doctrine now names three **layers** — strategy (role `strategist`,
  the session itself, never spawnable), management (`manager`), execution
  (`scout`/`builder`/`reviewer`) — and **three layers is the default for non-trivial work**,
  inverting guidance that had called the middle layer avoidable cost.
- **Operator checklist — this project is migrated, OTHER projects are not.** Per project: remove
  and re-add the marketplace (not just uninstall — §5), uninstall `foreman-kit` and any retired
  one-skill ids, install `atelier` + `solo-skills` **in that project** (an `enabledPlugins` flag
  alone proves nothing — memory: `plugin-enablement-needs-per-project-install`), delete the stale
  `~/.claude/plugins/cache/dotfiles-agents/foreman-kit/`, and rename any
  `.claude/foreman-kit.local.md` → `.claude/atelier.local.md` (schema, now including `handoff:` and
  `isolate:`, in the delegation skill's `references/activation.md`). Remaining `foreman` mentions
  in `backlog/`, decisions, and memory are deliberate history — **do not rewrite them**.

Standing mechanisms not to re-derive: **ADR 0017** (symlink assemblies, `dist/` retired, roster =
provenance manifest, opencode generated at install time); **`origin: vendored`** (third-party
in-tree only under `backlog/docs/vendoring-rule.md`, machine-checked); **dual-homing** (one
`primitives-core/` source symlinked into two assemblies loads the skill once).

## 2 · Recent deliveries — one line per era; blow-by-blow lives in PRs, issues, git

- 2026-07-20/08-04: rebuild epics; extender-db Waves 0–3; harness + campaign runner; ADR 0008
  publish lanes; ADR 0016 estate restructure; Backlog.md migration; **ADR 0017 refactor
  end-to-end**; decisions 4/5/6; vendoring rule.
- 2026-08-06: publish repaired; harness isolation; decision-8; iterm2 skill; **marketplace front
  door rebuilt**; **foreman-kit renamed to atelier** with the lab-01 doctrine rewrite.
- 2026-08-07 (s9): **backlog sweep + delegation layers.** 15 cards closed, issue queue emptied,
  published twice; delegation-ledger fix (#250), **version-bump gate**, rewritten `scout`,
  `handoff:` override, **`plugin-feedback`**, **three-layer rewrite** (TASK-045).
- 2026-08-07 (s10): **the marketplace restructure** (TASK-043, #276/#277) — 22 entries → 6,
  `solo-skills` published behind a derived membership gate (`scripts/check_solo_skills.py`). Two
  live defects removed on the way, including a standalone that had **never worked**.
- 2026-08-07 (s11): **`worktree-isolation`** (TASK-050, #286) — atelier's 8th hook, a `PreToolUse`
  rewrite on the `Agent` tool giving writing workers their own worktree, opt-in via `isolate:`.
  Root-caused the "worktree crews land on a published commit" gotcha (§5).
- 2026-08-07 (s12): published `dev@8ea83ba` to `main` (`worktree-isolation` / atelier 0.11.0 now
  live for consumers). No other changes landed.

**Sub-projects, both self-describing — read their own docs first.** `evals/` (PocketBase extender
DB): `evals/README.md`, `_structure/CHARTER.md`, `PROCEDURES.md`. Waves 0–3 done; M3–M6 are
TASK-21.x. **`pb_data/data.db` is TRACKED — stop the server before committing or switching
branches**; creds in untracked `.claude/operations/extender-db.env`. `harness/` (uv project):
`harness/docs/DESIGN.md`; live runs need `export ANTHROPIC_API_KEY="$(secret get ANTHROPIC_API_KEY)"`.
**No dry-run exists, so a smoke test appends to the tracked `results.jsonl`** — restore from HEAD
after (TASK-27).

## 3 · Next up

**Source of truth is the backlog** (`backlog board` / `backlog task list --plain`).

`dev` and `main` are in sync (nothing unpublished) — no single obvious next; pick by appetite
from "buildable now" below.

**TASK-29 is now unblocked, but its ruling needs reinterpreting.** The owner ruled it should get a
"standalone home"; standalone plugins no longer exist. The faithful reading is that `lab-setup`
joins `solo-skills` **if the membership gate says it qualifies** — run
`python3 scripts/check_solo_skills.py --report` against it rather than deciding by eye. If it does
not qualify, the ruling has no valid target and needs a fresh one.

**Nothing is blocked on the owner** — every question asked on 2026-08-07 was ruled, and the rulings
sit on the cards (TASK-034, TASK-033, TASK-12). Read the card, do not re-ask.

**Buildable now** is most of To Do; the cards carry their own scope. Only the sequencing judgment
is worth keeping here: **TASK-042** (trim `surfaces.md`) is the highest-leverage, being the
de-duplication behind three shipped defects; **TASK-049** waits on TASK-034's profile decision;
**TASK-13** is unblocked but should wait for post-2026-08-07 ledger rows to accumulate.
**Needs a live billed run:** TASK-21.3, TASK-21.5. **Needs the PocketBase server:** TASK-21.1,
TASK-21.2, TASK-21.4.

**TASK-035 residue:** the cold-read audit is done and every failing card named, but two criteria
stay unchecked pending card rewrites. Authoring defect to watch: **criteria phrased "Either X… or
Y…"** defer the decision into the criterion and are unverifiable until someone rules.

**Never observed live:** nobody has confirmed `SubagentStart` fires with `plugin-feedback`
installed. If the event were unhonored the worker tier is silently inert and every test still
passes, since they assert only on stdout. **This is now cheap to close** — use the headless probe
recipe in §5 rather than waiting for an organic dispatch.

**Cross-repo, the owner's call:** ra-platform's planning-desk adoption is uncommitted in
`~/Developer/ra-platform`; the four desk folders in dotfiles-agents-desk likewise.

## 4 · CROSS-REPO — desk-platform design (on the desk, NOT here)

Parked on the owner's IA approval; unchanged since 2026-08-04. Full state:
`~/Documents/EXECUTIVE_DESK/Projects/ARCHIVE/dev-tooling-desk-old/_meta/plans/desk-platform/`.

## 5 · Conventions & gotchas

**Publishing**

- **A plugin is the UNIT OF INSTALLATION**, and so is a marketplace's granularity. No aggregate can
  offer per-skill installs. What makes that cheap is progressive disclosure — 30 skills cost 30
  one-line descriptions, not 30 bodies. **Do not accept a request to make a plugin's skills
  "individually installable"**; correct the premise instead.
- **Retiring an entry breaks a consumer's marketplace registration, not just the plugin.** Observed
  2026-08-07: a stale registration reported "8 errors during load" until the marketplace was
  removed and re-added. Migration is remove-and-re-add, not merely uninstall the dead ids.
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
- **If Actions is down**, reproduce `publish.yml` by hand in *scratch worktrees* (the workflow file
  is the spec) so the real tree never touches `main`; delete the leftover `publish-tree` branch after.

**CI and gates**

- **`ci.yml` fires on `pull_request` ONLY.** A commit pushed straight to `dev` gets zero CI. The
  owner waived the PR step for **docs/memory/handoff-only** commits on 2026-08-07 ("commit directly
  to dev"); that waiver does not extend to code, which still needs a PR so the gates actually run.
- **CI job names are frozen** — branch protection pins required checks by NAME, so a new gate must
  ride an existing job.
- **`make ci`'s `✗ opencode laydown — refusing…` line is a passing test's own output.** Judge by
  exit code, never by ✗ glyphs.
- **PROBE the harness instead of reasoning about it.** A hook or agent behavior in question is
  answered in one round-trip by a headless run in a throwaway git repo:
  `printf '<prompt>' | claude -p --settings <f> --model haiku --permission-mode acceptEdits
  --allowedTools "Agent,Bash,Read"`, where `<f>` registers the real hook.py (or a stdin logger).
  The prompt must arrive on **stdin** — a positional prompt errors out; `--settings` merges over
  the normal config, so existing auth is reused. For schemas and error strings the docs omit,
  grep `strings ~/.local/share/claude/versions/<v>`. Settled TASK-050's whole contract pre-code.
- **`Closes #N` does nothing here.** GitHub auto-closes only on the *default* branch and PRs merge
  into `dev`. Close issues explicitly, or a shipped fix leaves its issue open.
- **The checklist↔audit contract is a CLOSED type vocabulary, and `make ci` never runs the
  compliance audit.** A new check TYPE is an audit-script change; prove checklist edits with a real
  `audit.py` run. Residue: IGNORE-01 still probes `_meta/operations/`.
- **`flow.yaml` is load-bearing** — `make flow` fails any PR adding an unhomed top-level path.
  Regenerate the doc with `scripts/check_flow.py --write-doc`.
- **DERIVE a set, never consume a recorded one.** TASK-043's card handed over an inventory of 27
  eligible skills and said not to redo it; a gate that re-derived membership found 30, three having
  been dropped by a group generalization nobody checked per-item. A recorded inventory is a
  hypothesis. Applies to any card whose notes hand you a list.
- **A gate passing tells you nothing about whether it has subjects.** `check_symlinks`' standalone
  README rule now has zero real subjects and is exercised only by synthetic fixtures, so it stays
  green either way; it is kept deliberately as a forward guard (reason in its module docstring).

**Agents and delegation**

- **"Layer" ≠ "tier".** Layer = org structure (strategy/management/execution). Tier = the model
  (haiku/sonnet/opus), the whole subject of `references/tier-cutoff.md`. Collapsing them re-creates
  the ambiguity the rename removed.
- **The `[field]` provenance tag** = observed in practice by the owner, not yet reproduced under
  measurement. Outranks `[untested]`, never outranks `[lab]`/`[cost]`. Carries the three-layer
  default until TASK-046 settles it. **Do not defend one as a measurement, or discard one as a
  guess** — both gut the tag's purpose.
- **An agent's `memory:` frontmatter key makes the RUNTIME create a directory** before the agent
  acts (`memory: project` → `<cwd>/.claude/agent-memory/<agentType>/`). The enum has no `off`, so
  omitting the key is the only disable — no prose in an agent body stops the `mkdir`. No atelier
  agent sets it as of 2026-08-07, so a fresh dir means some other definition carries it.
- **`scout` is no longer Bash-less.** It still cannot write (`Edit`/`Write` absent — structural),
  but shell authority is prompt-enforced: a brief must name the exact read-only commands it grants.
  Its `maxTurns` cap is gone, so scout briefs may budget honestly.
- **A skill can name an agent that does not exist and nothing catches it** — TASK-047's
  `board-triage` documents a `board-analyst` that is in no roster, which is one of the two reasons
  it is excluded from `solo-skills`. Check agent names against the roster by hand until a gate
  exists; fixing this one changes what ships.
- **Prefer disjoint file ownership over worktrees.** Session 9 ran ~15 concurrent workers on one
  tree with zero collisions, purely by giving each an owned file list and forbidding `make`/git.
- **A worktree cannot see uncommitted work — structural, not a bug.** It is a clean checkout of a
  ref, so modified and untracked files in the parent do not exist inside it (probed: "No such file
  or directory" for a file sitting right there). Hence `worktree-isolation` never isolates
  `scout`/`reviewer`/`Explore`/`Plan`/`fork` even when listed — isolating a reviewer aims it at a
  tree missing the diff it was sent to read. Same trap for a builder: commit first, or leave that
  dispatch un-isolated.
- **The "worktree crews land on a published commit" mystery is SOLVED, and the fix is unapplied.**
  Cause: the `worktreeBaseRef` setting (`fresh` default | `head`); `fresh` branches from
  `origin/<default-branch>`, which here is publish-only `main`. **This repo has not set it**, so
  every worktree brief still needs the self-check (`primitives-core/` missing → `git fetch origin
  && git reset --hard origin/dev`) until `"worktreeBaseRef": "head"` lands in settings.json. Also
  governs `--worktree` and `EnterWorktree`.
- **Forcing isolation: two levers.** A `PreToolUse` hook matching tool name `Agent` (not `Task`)
  rewrites the dispatch via `hookSpecificOutput.updatedInput` (PreToolUse-only); agent frontmatter
  also takes `isolation:`, resolving as `explicit param ?? frontmatter`. Frontmatter was rejected
  for atelier because it ships always-on to every consumer. Forcing it outside a git repo is a hard
  error, and the Agent `cwd` param is mutually exclusive with it.
- **Adversarially review a new plugin before merging.** On `plugin-feedback` it caught third-party
  reports filing into this repo silently, plus two tests that could not fail.
- **`logs/delegation.jsonl` is trustworthy from 2026-08-07 on, its history is not** — earlier rows
  inflate the parent session ~9x and say `lead` where later ones say `manager`, so an analysis
  spanning that boundary reads one agent as two. Truncate before any tier analysis.
- **`/reload-plugins` misreports skills as `0`** (#250's D4, seen twice on 2026-08-07 with skills
  demonstrably loaded). Trust the skill list, not the count.

**Repo hygiene**

- **A stale worktree can hide finished work indefinitely** — one sat a day holding ~100 uncommitted
  lines while the main tree's `git status` stayed clean and the branch read as merged. **Run
  `git worktree list` at session start** before assuming a branch is disposable.
- Worker agents may drop `.claude/agent-memory/` into their working dir — sweep the specific stray
  path, **never** whole-dir `git rm` the root `.claude/` (it holds this file and the tracked
  memory). The pile is finite (TASK-048): the `memory:` key that created it is gone from every agent.
- **Never mutate a second repo's git history** — read/draft in a consumer repo, leave it uncommitted.
- **No unguarded counts in prose or metadata** (owner rule) — a count needs a gate that reads it, or
  phrase it so growth cannot falsify it.
- **A new plugin** = a `plugins/<id>/` dir + a hand-authored root marketplace.json entry.
  pptx-themes' skill README carries the Anthropic attribution for its vendored `base/` — never split
  or drop that section.
- **Project settings no longer name any `@dotfiles-agents` plugin** (2026-08-07) — enablement lives
  entirely in per-project install records, and `enabledPlugins` lists only the three `@workbench`
  dev plugins. Editing a product plugin's source never needs it enabled; leave this alone unless
  you want to *run* one.
- **Removing a marketplace via `/plugin` DELETES every one of its entries from the project's
  tracked `enabledPlugins`** (observed 2026-08-07, seven entries wiped in one go). The owner ruled
  the resulting state correct here, so **do not "restore" them** — just know it before doing it
  elsewhere.
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
