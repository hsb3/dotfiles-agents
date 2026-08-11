# HANDOFF — dotfiles-agents

_Cold-start bridge. Last updated: 2026-08-11 (session 17). Refresh at session boundaries (/handoff). Secret-free._

_**This file lives at `.claude/HANDOFF.md`** — the third entry in the handoff hooks'
`CANDIDATE_PATHS`, with the two higher-precedence paths absent, so the hooks resolve it with no
override. META-06 was amended 2026-08-06 to accept that trio (decision-8), so this location is
conformant and the `handoff` skill's "never relocate" rule is satisfied by leaving it here._

## 0 · Orientation

**Everything about what this repo is, the task interface, and the source-of-truth rules lives in
CLAUDE.md, which is hot-loaded into your context already — do not restate it here.** This file
carries only what CLAUDE.md cannot: live state, decisions and their whys, and the gotchas that bite.

## 1 · Current standing

- **`dev` `eeb87f5`** · **`main` `696bf82` = `publish: dev@eeb87f5`** · **7 plugins** ·
  **59 primitives** · `make ci` green (exit 0, 589 tests) · no worktrees. Read the issue queue
  live, never from here.
- **NOTHING IS UNPUBLISHED.** `kaneo` `0.4.0 → 0.9.0` published 2026-08-11 and verified by
  payload rather than version string: `mint-mcp-token.sh` present as a real file (mode 100755,
  symlink correctly dereferenced), `onboard_repo.py` carrying `DOC_LABEL`/`WORK_TYPES`, and the
  preflight hook carrying the shadow-registration check. #310/#311/#312/#313 all merged.
- **The open issues arrive from OTHER PROJECTS via `plugin-feedback`, not from work here.**
  The 2026-08-09 triage carded everything then open (TASK-052 … TASK-057, #289 → TASK-033).
  **Four have arrived since and have NO card: #299, #300, #301** (2026-08-10) **and #306**
  (2026-08-11, which landed mid-session while nobody was working the queue — the standing
  proof of the "re-read `gh issue list` at session start" rule below). On a first read,
  unverified: #301 restates #282/TASK-052; #299 and #306 both describe a manager never
  receiving worker completion reports and are probably one bug, in the same wait-forever
  family as #280/#285/TASK-054; #300 (instrument long runs — 30-minute tasks taking 2–4
  hours) looks genuinely new. Triage them properly rather than trusting that sentence.
  **#291 no longer exists** — deleted upstream, so ignore any older note about forwarding it.
- **Two BREAKING renames published 2026-08-07; old ids fail SILENTLY.** The marketplace went 22
  entries → 6 (seventeen one-skill plugins retired into **`solo-skills`**; `mise-en-place-scaffold`
  survives only inside `code-desk`), and the delegation vocabulary changed: skill
  `atelier:foreman` → **`atelier:delegation`**, agent `lead` → **`manager`**. Remaining `foreman`
  mentions in `backlog/`, decisions, and memory are deliberate history — **do not rewrite them**.
- **Operator checklist — this project is migrated, OTHER projects are not.** Per project: remove
  and re-add the marketplace (not just uninstall — §5), uninstall `foreman-kit` and retired
  one-skill ids, install `atelier` + `solo-skills` **in that project** (an `enabledPlugins` flag
  alone proves nothing — memory: `plugin-enablement-needs-per-project-install`; confirmed again
  2026-08-11, where `kaneo@kaneo-ops: true` sat in a repo whose marketplace was never
  registered), delete the stale `~/.claude/plugins/cache/dotfiles-agents/foreman-kit/`, and
  rename `.claude/foreman-kit.local.md` → `.claude/atelier.local.md` (schema in the delegation
  skill's `references/activation.md`).

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
- 2026-08-11 (s15): **`comment-hygiene`** — a skill (dual-homed, atelier + solo-skills) and an
  advisory `PreToolUse` gate that fires on `git commit` / `gh pr create` (#302, #303). Owner
  directive: history belongs on the task, not in code comments. **TASK-060** filed for the gate
  gap it exposed. Two measurement lessons in §5.
- 2026-08-11 (s16): **`kaneo` adopted as the 7th plugin and published** (#304, #305,
  TASK-061). Moved from the `hsb3/kaneo-ops` ops repo, which gave it none of these gates.
  Ships the roster's **first `mcp`-type primitive** — closing a defect where the plugin
  claimed to ship an MCP server config that actually sat at the ops repo root, so every
  consumer but that one silently got no board tools. Then #305 added the availability guards
  the owner asked for ("fail loudly"): a `SessionStart` preflight plus a call-time config
  deny. **Proven live** in `~/Developer/kaneo`, not just by tests — see §5. TASK-062/063/064
  filed.
- 2026-08-11 (s17): **`kaneo` 0.4.1 → 0.9.0 — first-run fixed, and five repos migrated onto one
  live board.** #308/#310 shipped `mint-mcp-token.sh` inside the skill (the plugin mandated five
  env vars and shipped nothing that produced them; SKILL.md pointed at a path resolving to
  nothing) and taught `kaneo-preflight` to catch a stray headerless `kaneo` registration in
  `~/.claude.json`, which outranks the plugin's server and makes Claude Code fall back to
  interactive OAuth **as the human owner** while every tool still works. #311 corrected
  `references/api.md` on three counts and shipped `scripts/onboard_repo.py`. #312 (**unmerged**)
  imposed one closed label vocabulary. TASK-065/066 closed. Live state, gotchas and the
  remaining fleet: §7.
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

**The queued thing is triage: #299/#300/#301/#306 have no cards** (§1). Beyond those, the cards
with users actually waiting are **TASK-052** (plugin-feedback cannot file a feature request at
all) and **TASK-053** (two shipped READMEs still teach the ignored flat `worktreeBaseRef` key).

**One loose end from s16, and it is in a second repo.** TASK-061 is Done with **AC #8
unchecked**: `kaneo-ops` still lists `kaneo` in its own `.claude-plugin/marketplace.json` and
still carries `plugins/kaneo/`, so two copies of the plugin now exist. Left untouched on
purpose (never mutate a second repo). It needs its marketplace entry dropped and its README
pointed here. Note that repo's tracked `.claude/settings.json` also carries an inert
`"kaneo@kaneo-ops": true` — that marketplace is not registered on this machine, so the plugin
was never actually installed there; it ran on a project `.mcp.json` alone.

**TASK-060 and TASK-064 are the cheap ones.** TASK-060: no gate reads a *bundle* README's skill
table, so `comment-hygiene` shipped into `solo-skills`, counted right in the root README, passed
every gate, and was still missing from the bundle's own table. TASK-064: three gaps the first
`mcp` primitive exposed — `gen_opencode` would silently drop an opencode-targeted `mcp` entry
(`translation.yaml` has a `render` row but `build()` has no branch for it), `check_catalog`'s
Contents vocabulary cannot express an MCP server, and `check_plugin_diagrams` miscounts nodes
on inline dotted-edge labels.

**`command` is now a primitive type** (decision-010) — the first non-{skill,agent,hook,mcp} kind.
A fifth type would touch `check_roster.py`, `gen_opencode.py`, `check_symlinks.py`, and
`flow.yaml` again; that is the standing cost, not a defect. **ADR 0001 `skills-over-commands` is
Superseded** — read it for the anti-duplication argument, never for the ban.

**Four things the command build surfaced and left open**, none blocking: `check_roster.py` has no
duplicate-id check while `gen_opencode` keys exclusions by id; the harness/eval lane cannot
evaluate a command and would misclassify one as an agent; `/atelier:activate` leaves an untracked
`logs/` dir in a fresh project (telemetry hooks, not the command); and **#297 stays open for the
gate blind spot, not the bug it reported** — see §5.

**TASK-29 is now unblocked, but its ruling needs reinterpreting.** The owner ruled it should get a
"standalone home"; standalone plugins no longer exist. The faithful reading is that `lab-setup`
joins `solo-skills` **if the membership gate says it qualifies** — run
`python3 scripts/check_solo_skills.py --report` against it rather than deciding by eye. If it does
not qualify, the ruling has no valid target and needs a fresh one.

**No card is blocked on the owner** — every question asked on 2026-08-07 was ruled, and the rulings
sit on the cards (TASK-034, TASK-033, TASK-12). Read the card, do not re-ask. **One decision is
still open and is now overdue: whether §5 should move out of this file.** It is ~230 of these
lines, and this file is ~395 against the handoff skill's ~200 ceiling. §5 is a gotcha inventory
rather than session narrative, so it grows every session and cannot be pruned without destroying
knowledge that cost real time to learn. Splitting it into a tracked `backlog/docs/` doc with a
pointer here is an IA change, so it needs the owner's word first — asked 2026-08-07, re-raised
2026-08-11. Until then this file stays over the ceiling on purpose, not by neglect.

**Buildable now** is most of To Do; the cards carry their own scope. Only the sequencing judgment
is worth keeping here: **TASK-042** (trim `surfaces.md`) is the highest-leverage, being the
de-duplication behind three shipped defects; **TASK-049** waits on TASK-034's profile decision;
**TASK-13** is unblocked but should wait for post-2026-08-07 ledger rows to accumulate.
**Needs a live billed run:** TASK-21.3, TASK-21.5. **Needs the PocketBase server:** TASK-21.1,
TASK-21.2, TASK-21.4. **TASK-035 residue:** two criteria stay unchecked pending card rewrites.

**`plugin-feedback` is PROVEN IN THE FIELD at the session tier** — the open issues are all
unprompted reports from other projects, so the `SessionStart` hook, the reporter, and the
repo resolution all work end to end. **The `SubagentStart` worker tier is still unconfirmed**;
if that event were unhonored the tier is silently inert and every test still passes (they assert
only on stdout). Close it with the headless probe recipe in §5 rather than waiting for an
organic dispatch.

**Cross-repo, the owner's call:** ra-platform's planning-desk adoption is uncommitted in
`~/Developer/ra-platform`; the four desk folders in dotfiles-agents-desk likewise. **New
2026-08-11 — `~/Developer/kaneo` is the live test bed for the `kaneo` plugin and carries
uncommitted changes:** its tracked `.claude/settings.json` gained `"kaneo@dotfiles-agents":
true` (written by `claude plugin install --scope project`), and its gitignored
`.claude/settings.local.json` gained `"disabledMcpjsonServers": ["kaneo"]` — deliberate, so the
repo's own project `.mcp.json` server cannot mask the plugin-shipped one and the test stays
conclusive. Reverting that key restores the project server. That repo also carries a stale
**local-scope** `kaneo` MCP server pointed at `http://localhost:5173/api/mcp` that fails every
session; clear it with `claude mcp remove kaneo -s local`.

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
- **`make ci`'s `✗` lines are passing tests' own output. Judge by exit code, never by glyphs.**
  Several gate tests run the real check scripts against synthetic tempdir fixtures and let their
  stdout through, so `✗ identity-neutrality`, `✗ roster<->disk drift`, and `✗ opencode laydown`
  all appear on a green run. Tell them apart by the counts: a fixture says "1 primitives" or
  "1 plugin(s), 2 symlink(s)" where the real repo says 53 and 6. **This trap bit again on
  2026-08-11** — an incoming handoff reported "3 pre-existing failures on HEAD" that did not
  exist, having also mis-attributed two of them to `tests/test_plugin_feedback.py`. Re-run
  before inheriting any claim that the tree is red.
- **A heuristic that passes its tests can still be mostly wrong — measure it against a corpus
  before shipping.** `comment-hygiene-gate` arrived with 7 passing tests and a clean self-review.
  Replayed over the last 40 commits it would have fired on 25 of them, with 73 of 75 findings in
  markdown — flagging the backlog cards and this file, the exact places history is supposed to
  live. A second pass, scored against Python's `tokenize` as ground truth, put real precision at
  79%. Both fixes came from the numbers, not from reading the code. **The method generalizes and
  is cheap:** replay the thing over `git log` history, and where the stdlib already has an
  authoritative parser for the format, use it as the oracle instead of eyeballing samples.
- **`comment-hygiene-gate` HAS REAL SUBJECTS HERE — expect it to fire on this repo's own
  commits.** A sweep of all 425 source files found **41 findings in 25 files**, essentially all
  true positives: board refs and dates in comments in `evals/ingest.py`, `externals.yaml`,
  `scaffold.py`, the workflow YAML, and the harness. Touching any of those will nudge. That is
  the gate working, not misfiring — but nobody has done the cleanup pass, and it is not carded.
- **Pushing straight to `dev` prints `remote: Bypassed rule violations` — that is expected, not
  an error.** `dev` is protected and expects 2 status checks; the owner's docs-only waiver means
  those commits land by bypass and therefore get **zero CI**. Run `make ci` locally before any
  such push, because nothing else will.
- **`git diff` appends a TAB to the `+++ b/<path>` header when the path contains spaces.** Every
  `backlog/tasks/*.md` filename here has spaces, so any tool parsing diff headers in this repo
  hits it — and a naive `line[6:]` silently carries the tab into the filename, which then breaks
  every downstream suffix or extension test. Split on `\t` first.
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

**Plugin MCP servers** (new surface as of `kaneo`, s16 — all of this was probed, not read)

- **A marketplace-installed plugin's MCP server is NOT gated by the per-project approval
  dialog. Installing the plugin IS the trust decision.** The gate's candidate list is project
  `.mcp.json` servers plus plugins where `aPt(p) = p.scope === "project" &&
  p.source.endsWith("@skills-dir")` — repo-supplied plugins only. Do not design around an
  approval step that will never fire.
- **A plugin's root `.mcp.json` is auto-discovered and merged.** A *string* `mcpServers` in
  `plugin.json` means a path to an **MCPB file**, not a config file — setting it to
  `"./.mcp.json"` is wrong and silently does nothing useful. Ship the `.mcp.json`, omit the key.
- **`/mcp disable` is per-project, invisible, and survives everything.** It writes
  `plugin:<plugin>:<server>` into `disabledMcpServers` under the cwd's entry in
  `~/.claude.json` — not a settings file. Real example on this machine:
  `plugin:desk-pm:desk-pm`. Approvals themselves have MOVED to `.claude/settings.local.json`;
  the reset path calls the `~/.claude.json` copies "legacy approvals".
- **A server can connect on fewer variables than the skill needs, and nothing errors.** kaneo's
  `.mcp.json` expands 2 of 5; the workflow needs all 5. The tools then exist and work against
  an unknown board. If a plugin ships a server, something must check the *contract's* config,
  not the server's — `kaneo-mcp-policy` is the worked example.
- **`claude mcp list` does NOT apply project settings `env`**, so it reports
  `Missing environment variables: X` for servers that work fine in a real session. Diagnose MCP
  config from a session, never from that subcommand. Cost an hour on 2026-08-11.
- **`--allowedTools` on a headless probe restricts the tool list the model can SEE**, so asking
  a probe to "list your tools" returns `NONE` even when the server loaded. A negative from such
  a probe is not evidence of absence — re-ask without the filter.
- **`claude plugin install --scope project` writes to the TRACKED `.claude/settings.json`.**
  In someone else's repo that dirties a tracked file; use `--scope local` when that matters.

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
- **The worktree base ref is the NESTED `worktree.baseRef` key**, not the flat `worktreeBaseRef`
  (that is only the `/config` widget id and is silently ignored). Unset, it defaults to `fresh`,
  branching from `origin/<default-branch>` — here, publish-only `main`. settings.json was fixed
  2026-08-09, so judge any earlier worktree-crew behavior as having used `fresh`; **the two
  published READMEs still teach the flat key (TASK-053 / #292)**. Also governs `--worktree` and
  `EnterWorktree`.
- **Forcing isolation: two levers.** A `PreToolUse` hook matching tool name `Agent` (not `Task`)
  rewrites the dispatch via `hookSpecificOutput.updatedInput` (PreToolUse-only); agent frontmatter
  also takes `isolation:`, resolving as `explicit param ?? frontmatter`. Frontmatter was rejected
  for atelier because it ships always-on to every consumer. Forcing it outside a git repo is a hard
  error, and the Agent `cwd` param is mutually exclusive with it.
- **Adversarially review a new plugin before merging.** On `plugin-feedback` it caught third-party
  reports filing into this repo silently, plus two tests that could not fail.
- **Do not infer harness behavior from a YAML library.** #297 concluded that an unquoted
  `end to end: ` in `agents/manager.md` made the harness drop every frontmatter field, because
  strict `yaml.safe_load` raises on it. It did not — the agent loaded with its full description
  and exact `tools`. Quote it anyway (strict-parsing consumers exist). **#297 stays open for the
  real gap: `make ci` never parses agent frontmatter, and repo-level `claude plugin validate`
  checks only the marketplace manifest without descending into plugin bodies**, so a malformed
  agent body is invisible to every gate. `--strict` on a dereferenced plugin dir catches it.
- **A doc that restates a script's vocabulary WILL drift, and it drifts downstream.**
  `activation/SKILL.md` said `check` has "three states"; the script emits four. The command then
  copied that wrong fact and invented a section. Fix by deletion — point at the script's own
  labels — not by synchronizing two copies.
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

## 7 · Kaneo migration — live state (2026-08-11, s17)

**The board is now the tracker for five repos.** Instance `kaneo-production-5641.up.railway.app`,
workspace `hsb3` = `6DfGLeeKlTRArM24iKqeZCQ0v2BZWBq0`. 553 tasks, all imported by
`scripts/onboard_repo.py`, all verified by re-export rather than by the import summary.

| slug | project | id | tasks |
| --- | --- | --- | --- |
| PBTT | pb-task-tracker (learn-pocketbase) | `mutooe0ijwd3yhyhd5behk74` | 241 |
| APIA | api-agents | `rhq4qgsmu2q7cztfpeui2cfp` | 164 |
| MSS | mcp-server-standard | `v6844qhsgp45ntrio55g8fle` | 73 |
| DAPI | desk-api-agents | `cv36ncnegdo5pmq36upkthb2` | 39 |
| AZR | azure-resources | `luci7yxlxv0rqcwv54dmeg2v` | 36 |

**The `meta` workspace (`VZWoU4ImwHL99wPAhLqVF6JHRG3wfm71`) is where the migration guides
itself.** Project `MIG` / `migration` = `qb6wjtyagke9bmg9n9mcm159`. Read it before doing more
migration work — it holds five documents (API gotchas, the onboarding runbook, board
conventions, the workspace/project decision, and a living status register) and seven open
tasks covering everything below. Workspaces have no REST CRUD; this one was created with
`POST /api/auth/organization/create`.

**Label model, closed on both axes** (#312): lowercase = kind of WORK
(`feature bug chore docs test spike`, Backlog.md's own `type:` axis, synonyms folded);
UPPERCASE = kind of DOCUMENT (`DOC DECISION SPEC GUIDE REFERENCE RESEARCH INCIDENT REGISTER`).
Per-repo area labels are dropped — the five repos' union was 80+, api-agents alone 52. Every
board has a **Document** lane holding decisions and docs.

### Gotchas that cost real time here

- **Statuses are NOT a global vocabulary.** A task's `status` is the slug of a column in its own
  project, so the valid set is whatever `GET /column/{projectId}` returns. A board with a
  `Documents` lane accepts `"status":"documents"` and no other board does.
- **A column's slug is fixed at creation; renaming changes only the display name.** PBTT's lane
  is named `Document` but keeps slug `documents`; boards created later use `document`. Resolve
  lanes by slug OR name — `onboard_repo.py` does.
- **`POST /task/import/{projectId}` silently discards `labels`** and still reports
  `"failed": 0`. `GET /task/export/{projectId}` *does* emit them, so an export → import
  round-trip looks lossless and is not. Labels need a second pass, verified by re-export.
- **`GET /label/workspace/{id}` returns one row per ATTACHMENT, not per label.** A name on 81
  tasks comes back 81 times. Compare distinct lowercased names or you will "discover" duplicates.
- **Cross-project task relations do not work** on this instance (owner-verified). Nothing in
  `/config` governs it. So a cross-cutting strategy project cannot link to the work it governs;
  workspace-scoped `GET /search` is the connective tissue instead.
- **Kaneo has no milestone/sprint/release primitive.** Hierarchy is workspace → project → task,
  plus columns, labels, relations. Releases are best modelled as a parent task with `subtask`
  relations — projects-as-releases renumbers task ids on every slip.
- **Backlog.md layouts differ per repo, silently.** learn-pocketbase keeps finished work in
  `tasks/` with status Done; mcp-server-standard used `completed/` and nests `archive/tasks/`.
  A fixed source list would have imported 31 of 73 items there and said nothing about the rest.
- **~100 of 192 task files in one repo carry folded-scalar titles** (`title: >-` + indented
  continuation). Treating that as the value retitles most of an import to `>-`.

### Not done

- **`--repo` takes a filesystem path only.** Repos with no checkout must be cloned first; the
  clone step is not automated.
- **~15 repos remain**, across `hsb3` and `mhi-raptorxai`, greenfield and brownfield mixed.
  `mhi-raptorxai` should be its own workspace (a real trust boundary); nothing there is started.
- **dotfiles-agents itself is deliberately NOT migrated.** It is the most coupled repo in the
  fleet — a `CRITICAL_INSTRUCTION` block in CLAUDE.md, `scripts/check_backlog_labels.py`,
  DoD-as-code reading `backlog/config.yml`, and 20 decision docs citing TASK ids. Migrating it
  changes repo law and gates, not just data. Do it last, or not at all.
- Run state (manifest, per-repo id-maps, the one-off `relabel.py` / `backfill_labels.py`) lived
  in the session scratchpad and is **gone**. `onboard_repo.py adopt` rebuilds a state file from
  board titles, which is why `apply` writes `TASK-083: ...` titles by default.

### Credentials

The migration ran under the **owner** key from this repo's gitignored `.env`
(`KANEO_CLIENT_URL`, `KANEO_API_KEY`), as a one-time owner-authorised exception. Normal
operation wants a per-repo **agent** key — an owner key misattributes every claim comment and
holds rights over every workspace. `.env` is covered by `.gitignore`'s `.env*`; `.env.example`
is trackable via the `!.env*.example` negation and holds placeholders only.
