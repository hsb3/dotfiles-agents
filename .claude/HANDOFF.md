# HANDOFF — dotfiles-agents

_Cold-start bridge. Last updated: 2026-08-07 (session 13). Refresh at session boundaries (/handoff). Secret-free._

_**This file lives at `.claude/HANDOFF.md`** — the third entry in the handoff hooks'
`CANDIDATE_PATHS`, with the two higher-precedence paths absent, so the hooks resolve it with no
override. META-06 was amended 2026-08-06 to accept that trio (decision-8), so this location is
conformant and the `handoff` skill's "never relocate" rule is satisfied by leaving it here._

## 0 · Orientation

**Everything about what this repo is, the task interface, and the source-of-truth rules lives in
CLAUDE.md, which is hot-loaded into your context already — do not restate it here.** This file
carries only what CLAUDE.md cannot: live state, decisions and their whys, and the gotchas that bite.

## 1 · Current standing

- **`dev` `a752839`** · **`main` `a3b904e` = `publish: dev@8ea83ba`** · **6 plugins** ·
  `make ci` green · no worktrees. Read the issue count live (see below), never from here.
- **`dev` IS WELL AHEAD OF THE LAST PUBLISH and the gap now includes a whole new skill.**
  Session 13's diagram work (TASK-051, #288) plus session 14's `atelier:activation` (TASK-058,
  #295) are both unpublished; atelier is at `0.12.0` on `dev` and consumers still see `0.11.1`.
  `publish-to-main` is the obvious next action and is now overdue by two eras of work.
- **The open issues arrive from OTHER PROJECTS via `plugin-feedback`, not from work here.**
  **Triaged 2026-08-09 — every one now has a card** (TASK-052 … TASK-057, plus #289 folded into
  TASK-033). Two turned out to be live shipped defects, both code-confirmed: **#282** (the
  feature-request path cannot file — default label `type:feature`, this repo has `type:feat`) and
  **#292** (the worktree base-ref key is documented flat and Claude Code ignores it). **#291 is
  misfiled** — a `use-railway` bug, a skill this marketplace does not ship; it is evidence for
  TASK-052's scope check, and forwarding it upstream is the owner's call.
- **Two BREAKING renames published 2026-08-07; old ids fail SILENTLY.** (1) The marketplace went
  22 entries → 6: all seventeen one-skill plugins retired into one aggregate, **`solo-skills`**,
  the five bundles untouched. **Per-skill installation no longer exists** and no aggregate can
  restore it (§5); `mise-en-place-scaffold` is the exception, living only inside `code-desk`.
  (2) The delegation vocabulary: skill `atelier:foreman` → **`atelier:delegation`**, agent
  `lead` → **`manager`**. Doctrine names three **layers** — strategy (the session itself, never
  spawnable), management (`manager`), execution (`scout`/`builder`/`reviewer`) — and **three
  layers is the default for non-trivial work**, inverting guidance that had called the middle
  layer avoidable cost.
- **Operator checklist — this project is migrated, OTHER projects are not.** Per project: remove
  and re-add the marketplace (not just uninstall — §5), uninstall `foreman-kit` and any retired
  one-skill ids, install `atelier` + `solo-skills` **in that project** (an `enabledPlugins` flag
  alone proves nothing — memory: `plugin-enablement-needs-per-project-install`), delete the stale
  `~/.claude/plugins/cache/dotfiles-agents/foreman-kit/`, and rename any
  `.claude/foreman-kit.local.md` → `.claude/atelier.local.md` (schema, including `handoff:` and
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
- 2026-08-07 (s9–s12): **backlog sweep, the marketplace restructure, and worktree isolation.**
  15 cards closed and the issue queue emptied; **version-bump gate**; **`plugin-feedback`**;
  **three-layer rewrite** (TASK-045); **22 marketplace entries → 6** with `solo-skills` behind a
  derived membership gate (TASK-043, #276/#277); **`worktree-isolation`** (TASK-050, #286);
  published twice, ending at `dev@8ea83ba`. Every durable gotcha from these is in §5.
- 2026-08-07 (s13): **plugin-README diagrams** (TASK-051, #288) — a standard
  (`backlog/docs/readme-diagram-standard.md`), a gate (`scripts/check_plugin_diagrams.py`, in
  `make check`), and one Mermaid diagram backfilled into all six plugin READMEs. Six version
  bumps, **unpublished**. Measured a tool gotcha on the way (§5).

**Sub-projects, both self-describing — read their own docs first.** `evals/` (PocketBase extender
DB): `evals/README.md`, `_structure/CHARTER.md`, `PROCEDURES.md`. Waves 0–3 done; M3–M6 are
TASK-21.x. **`pb_data/data.db` is TRACKED — stop the server before committing or switching
branches**; creds in untracked `.claude/operations/extender-db.env`. `harness/` (uv project):
`harness/docs/DESIGN.md`; live runs need `export ANTHROPIC_API_KEY="$(secret get ANTHROPIC_API_KEY)"`.
**No dry-run exists, so a smoke test appends to the tracked `results.jsonl`** — restore from HEAD
after (TASK-27).

## 3 · Next up

**Source of truth is the backlog** (`backlog board` / `backlog task list --plain`).

**Publish is the one thing queued** — `dev` carries the diagram work and six version bumps that no
consumer has (`publish-to-main`). Issue triage is done (§1); the two live shipped defects it
surfaced, **TASK-052** and **TASK-053**, are the cards with users waiting on them, and TASK-053's
remaining work is two published READMEs, so it wants to ride a publish anyway.

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
TASK-21.2, TASK-21.4. **TASK-035 residue:** two criteria stay unchecked pending card rewrites.

**`plugin-feedback` is PROVEN IN THE FIELD at the session tier** — the 7 open issues are
unprompted reports from two other projects, so the `SessionStart` hook, the reporter, and the
repo resolution all work end to end. **The `SubagentStart` worker tier is still unconfirmed**;
if that event were unhonored the tier is silently inert and every test still passes (they assert
only on stdout). Close it with the headless probe recipe in §5 rather than waiting for an
organic dispatch.

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
  `plugins/<id>/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`. **Do it with a
  targeted string replace, not a load-and-redump** — the two files disagree on unicode
  (`marketplace.json` stores escapes, atelier's `plugin.json` stores raw), so a
  `json.dump(ensure_ascii=True)` rewrite silently re-encodes a description line nobody asked to
  touch. Read the diff either way.
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
- **A STALLED MANAGER LOOKS EXACTLY LIKE A DEAD ONE, and guessing wrong is expensive both ways.**
  Session 14: a manager went 65 minutes with a 145-byte output file while its builder had already
  reported. Read as dead; it was not — it was running adversarial review, and it then committed,
  pushed, and opened the PR on its own while the session was mid-takeover. **Nothing distinguishes
  the two states** — output-file mtime, size, and `TaskList` all read the same for a slow agent and
  a corpse. Before taking over a manager's git steps, check `gh pr list` and `git log` for work it
  landed since you last looked, or you race it. This is issue #285 / **TASK-054**, felt from the
  strategy layer rather than reported from below. The hour was not waste: that review caught two
  ship-blockers the builders' self-reports had called clean, one of which would have shipped a
  `create` that silently disabled handoff surfacing — the exact failure class the skill exists to
  expose.
- **A worktree cannot see uncommitted work — structural, not a bug.** It is a clean checkout of a
  ref, so modified and untracked files in the parent do not exist inside it (probed: "No such file
  or directory" for a file sitting right there). Hence `worktree-isolation` never isolates
  `scout`/`reviewer`/`Explore`/`Plan`/`fork` even when listed — isolating a reviewer aims it at a
  tree missing the diff it was sent to read. Same trap for a builder: commit first, or leave that
  dispatch un-isolated.
- **The "worktree crews land on a published commit" fix was written under the WRONG KEY and did
  nothing until 2026-08-09.** Cause is as recorded — base ref defaults to `fresh`, branching from
  `origin/<default-branch>`, here publish-only `main`. But the key is **nested `worktree.baseRef`**;
  the flat `worktreeBaseRef` that settings.json carried from `8ea83ba` is only the `/config` menu's
  widget id and was silently ignored (binary 2.1.220: handler reads `r?.worktree?.baseRef ?? "fresh"`,
  writes `{worktree:{baseRef}}`). Fixed in settings.json 2026-08-09; **the two published READMEs
  still teach the flat key — that is TASK-053, and it is issue #292.** Judge any past worktree-crew
  behavior before 2026-08-09 as having used `fresh`. Also governs `--worktree` and `EnterWorktree`.
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
- **The GH issue queue fills with ZERO activity in this repo.** `plugin-feedback` is installed in
  other projects, so their sessions file here asynchronously — 7 arrived on 2026-08-07 while
  nobody was working in this tree, and session 12's handoff asserted "zero open GH issues" ~20
  minutes after four of them landed. **Re-read `gh issue list` at session start; never carry an
  issue count forward from the handoff.** This is the "no unguarded counts" rule biting the
  handoff itself.

**Docs and diagrams**

- **Every `plugins/<id>/README.md` must carry a Mermaid diagram** under `## How it fits together`
  — standard in `backlog/docs/readme-diagram-standard.md`, enforced by `make check`. The rule
  that matters is editorial, not mechanical: *draw the trigger and the flow, never the inventory*.
- **`mermaid-cli` EXITS 0 WHEN THE RENDER FAILS** and writes no file — measured 2026-08-07 on a
  `(` in a label and on `load --> end`. The same diagrams render blank on GitHub with no error,
  so neither `$?` nor reading the source will tell you. Assert `test -s out.svg`, and for shipped
  diagrams confirm every label reached the SVG. Full entry: memory
  `mermaid-cli-exits-zero-on-failure`.

**Repo hygiene**

- **A stale worktree can hide finished work indefinitely** — one sat a day holding ~100 uncommitted
  lines while the main tree's `git status` stayed clean and the branch read as merged. **Run
  `git worktree list` at session start** before assuming a branch is disposable.
- Worker agents may drop `.claude/agent-memory/` into their working dir — sweep the specific stray
  path, **never** whole-dir `git rm` the root `.claude/` (it holds this file and the tracked
  memory). The pile is finite (TASK-048): the `memory:` key that created it is gone from every
  agent. **Still present and untracked as of s13:** `.claude/agent-memory/foreman-kit-reviewer/`
  (3 files) — pre-rename residue, harmless, and TASK-048's to remove.
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
- Backlog specifics beyond CLAUDE.md: `--depends-on` needs the dotted subtask form (`task-21.1`);
  `make flow` requires a claimed top-level path to be *tracked*; avoid two sessions writing the
  backlog at once.

## 6 · Map

- Docs: CLAUDE.md (rules, hot-loaded) · `.github/CONTRIBUTING.md` (human loop) ·
  `backlog/decisions/` (ADR mirrors + rulings) · `backlog/docs/` (`vendoring-rule.md`,
  `readme-diagram-standard.md`, `FLOW.md`).
- **Exec desks:** `~/Documents/EXECUTIVE_DESK/Projects/dotfiles-agents-desk/` (this repo);
  `.../desk-standard-desk/`; `.../ARCHIVE/dev-tooling-desk-old/` (desk-platform design).
