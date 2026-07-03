---
title: "Build plan — repoint core-tier skill symlinks + migrate the 16 commands before retiring hsb3-custom-plugins"
type: spec
status: draft
created: 2026-07-03
purpose: Source-grounded build plan for #32 — the verified TRUE residual (the issue body's symlink framing is stale), per-command dispositions, skills-CLI retirement, doc/memory hygiene, and the archive step.
notes: Drafted 2026-07-03 from fresh machine + gh verification. The T-15 counts in the issue body (6 broken + 8 breaking symlinks) no longer describe the machine; every claim below was re-verified against disk, the live GitHub repo, or cited source on 2026-07-03.
---

# Repoint core-tier skill symlinks + migrate the 16 commands before retiring hsb3-custom-plugins

_The symlink half of this issue is already done or overtaken by events: `~/.claude/skills/`
holds exactly two healthy symlinks (auth0-cli, find-skills -> `~/.agents/skills/`), the old
`hsb3-custom-plugins` marketplace is deregistered locally, and skill delivery now runs
through the `dotfiles-agents` plugin-marketplace cache (project-workflow at 0.2.1). The TRUE
residual is: (1) disposition the 16 slash commands that live only in the frozen GitHub repo
(fold or drop per ADR 0001), (2) rescue or drop two supporting assets the T-15 migration
missed (python-standards `templates/`, dev-focus `session-summary.py` — the migrated Stop
hook dangles on the latter today), (3) retire the broken `skills` CLI and update the three
dotfiles docs/memory surfaces that still describe the old two-tier model, then (4) archive
the GitHub repo and close out #32._

Status: draft
Date: 2026-07-03

## Tracking

- Issue: #32 (milestone P1 — Lifecycle live).
- Origin: T-15 skills-migration inventory, findings F-symlinks / F-commands, approved
  2026-07-02 (vault note `[[skills-migration-inventory]]`, cited from #32 and #31; the note
  itself is in the Obsidian vault, not on any repo desk — counts re-verified here instead).
- Relations: #31 (closed — Q-13 batch triage that carried the T-15 sourced-origin flips);
  #27 (project-workflow v2 — no file overlap, but any plugin-version bumps must not collide);
  ADR `docs/decisions/0001-skills-over-commands.md` (this issue is its named worklist);
  CANON decisions 1 / 3 / 15 (cowork desk `_structure/CANON.md:40,42,55` — retire-and-archive,
  commands dropped, source repo frozen).
- Contract impact: possible roster additions (drift-guarded; stable ids per
  `primitives-core.yaml`), plugin version bumps in `plugins.yaml`, regenerated `targets/`
  (never hand-edited). No checklist-row or API surface. Machine-side edits land in the
  `~/dotfiles` repo, not here.

## The problem (grounded in source)

**What exists (all re-verified 2026-07-03):**

- `~/.claude/skills/` contains exactly TWO symlinks, both healthy, both dated 2026-07-02:
  `auth0-cli -> ../../.agents/skills/auth0-cli` and `find-skills -> ../../.agents/skills/find-skills`
  (verified: `ls -la ~/.claude/skills/` + readlink resolution). The issue body's "6 already
  broken + 8 more break at retirement" describes a pre-2026-07-02 state; the pruning and
  repointing already happened. **Zero dangling symlinks exist today.**
- Skill delivery is the marketplace, not symlinks: the installed cache is
  `~/.claude/plugins/cache/dotfiles-agents/` (project-workflow at 0.1.0 / 0.2.0 / 0.2.1;
  python-standards also cached), and the registered marketplaces are azure-skills,
  claude-plugins-official, dotfiles-agents, temporal-marketplace — `hsb3-custom-plugins`
  is **already deregistered** (verified: `ls ~/.claude/plugins/{cache,marketplaces}/`).
  Deploy is dotfiles-bootstrap's job (`scripts/translate.py:476`; `_meta/HANDOFF.md:34`),
  and opencode reads `~/.agents/skills/` natively (`docs/CHARTER.md:40`).
- The `skills` CLI (`~/dotfiles/bin/.local/bin/skills`) is dead for every subcommand: its
  repo default is `REPO="${SKILLS_REPO:-$HOME/Developer/FUNCTIONFORM/hsb3-custom-plugins}"`
  (`skills:17`) and it hard-dies when that path is absent (`skills:24`). Verified:
  `skills doctor` -> `skills: source repo not found: /Users/henry/Developer/FUNCTIONFORM/hsb3-custom-plugins`.
  `/Users/henry/Developer/FUNCTIONFORM` does not exist; no `hsb3-custom-plugins` checkout
  exists anywhere under `~/Developer` (verified with `fd`).
- `github.com/hsb3/hsb3-custom-plugins` is live, NOT archived, last pushed 2026-07-02
  (verified: `gh repo view --json isArchived,pushedAt`). Its full tree (243 blobs, fetched
  via `gh api .../git/trees/HEAD?recursive=1`) confirms **exactly 16 command files**:
  dev-focus 3 (focus-check, scope-review, session-summary), github-projects-board-management 4
  (board-setup, board-status, board-sync, board-triage), obsidian-plugin-dev 1 (create),
  project-dashboard 2 (setup-dashboard, update-dashboard), python-standards 6 (python-fix,
  python-init, python-validate, ty-check, ty-check-file, ty-install).
- Every remote skill and agent is already in the roster (spot-verified: all 14 `agents/*.md`
  and all `plugins/*/skills/*` names in the remote tree match `primitives-core.yaml` ids;
  the 13 remote core-shelf `skills/*` all appear in `targets/claude-code/skills/`). The
  python-standards hooks all migrated too (`primitives-core.yaml:837,847,857`). The T-15
  claim "the 16 commands are the only retiring-repo content not in the roster" is **almost**
  true — see the two missed supporting assets below.
- ADR 0001 binds the disposition: "No command survives as-is. Each existing command's intent
  folds into its paired skill ... or the command retires with a rationale"
  (`docs/decisions/0001-skills-over-commands.md:19-21`), and names this issue as the
  fold/retire worklist (`0001-skills-over-commands.md:25-26`). Desk convention repeats it
  (`_meta/plans/_config.md:54`) and requires hooks to be stdlib-only (`_config.md:55`).

**What's missing / broken:**

- **The 16 commands exist only in the remote repo** — no local checkout, nothing in
  `primitives-core/`, no `commands/` dir anywhere under `targets/` (verified `fd -t d
  commands targets/` = empty). They must be dispositioned before archive or their content is
  buried in an archived repo with no rationale on record.
- **Missed asset 1 — python-standards `templates/`** (4 files: `.gitignore`,
  `.python-version`, `README_template.md`, `pyproject.toml` in the remote tree). Referenced
  by `python-fix` and `python-init` via `${CLAUDE_PLUGIN_ROOT}/templates/`; not present in
  `primitives-core/hooks/python-standards/` nor anywhere in `targets/`. Dropping the
  commands silently drops the templates.
- **Missed asset 2 — dev-focus `scripts/session-summary.py`.** The MIGRATED Stop hook
  (`primitives-core/hooks/dev-focus/hooks-handlers/dev-focus.Stop.stop-summary.sh:10-11`)
  runs `uv run "$SCRIPT_DIR/scripts/session-summary.py"` — but no `scripts/` dir was
  migrated (verified in `primitives-core/hooks/dev-focus/` and
  `targets/claude-code/plugins/dev-focus/`). The hook is a silent no-op today (`|| true`
  swallows the failure). Latent bug shipped in the current plugin.
- **The `skills` CLI has no disposition** — its two-shelf model (core symlinks + the old
  marketplace) is gone; `claude plugin` + the dotfiles-agents marketplace + `npx skills`
  (find-skills installs into `~/.agents/skills/`) replaced every subcommand.
- **Three stale doc/memory surfaces** still teach the old model: the global memory note
  `~/dotfiles/claude-code/.claude/memory/reference-skills-system.md` (two-shelf model,
  FUNCTIONFORM clone path, a "full inventory" pointer to
  `~/dotfiles/_docs/reference/skills-inventory.md` which **does not exist** — verified);
  `~/dotfiles/CLAUDE.md:172` (the `skills` CLI row naming hsb3-custom-plugins as source of
  truth); and the `skills` row in
  `~/dotfiles/claude-code/.claude/instructions/tools.md`. A stray
  `~/dotfiles/claude-code/.claude/settings copy.bak` also still references the old
  marketplace.
- **Governance loose ends on the two live symlinks:** `auth0-cli` in `~/.agents/skills/` is
  a vendor skill (SKILL.md author `Auth0 <support@auth0.com>`) tracked NOWHERE — not in the
  roster, not in `externals.yaml` (verified grep), despite `_config.md:56` "externals are
  tracked, not vendored". The deployed `find-skills` copy is NEWER than the roster's pinned
  source (`primitives-core.yaml:201-211`, vendor vercel-labs, ref `2adcfe5a...`): the
  deployed SKILL.md documents an `--owner` flag the roster copy lacks (verified diff).

## Deliverables

**A — Disposition record for the 16 commands (analysis is done; record it).**
Thirteen of the 16 are thin invocation wrappers over roster primitives that already carry
the full procedure — drop each with a one-line rationale naming its covering primitive:

| Command | Disposition | Covering roster primitive (primitives-core.yaml line) |
| ------- | ----------- | ------------------------------------------------------ |
| board-setup | drop | github-project-board skill (223); scripts bundled per #41 |
| board-status | drop | board-reporting skill (42) |
| board-sync | drop | board-triage / board-reporting skills + bundled export scripts |
| board-triage | drop | board-triage skill (52) + board-analyst agent (637) |
| create (obsidian) | drop | plugin-scaffolder (777), chat-ui-builder (647), mcp-integrator (747) agents |
| setup-dashboard | drop | setup-project-dashboard skill (583) |
| update-dashboard | drop | update-project-dashboard skill (627) |
| focus-check | drop or fold | developer-focus skill (161) — fold the output template if absent from the skill |
| scope-review | drop or fold | developer-focus skill (161) — fold the Scope Hammer MUST/DEFER/CUT rubric if absent |
| ty-check | drop | trivial one-liner; ty usage is baseline knowledge plus python-standards hooks |
| ty-check-file | drop | same |
| ty-install | drop | same |
| session-summary | drop | pairs with deliverable C (the dangling hook) |
| python-fix | decision 1 | see deliverable B |
| python-init | decision 1 | see deliverable B |
| python-validate | decision 1 | see deliverable B |

For focus-check / scope-review: read `primitives-core/skills/developer-focus/SKILL.md` +
`references/checklists.md`; if the Scope Hammer rubric and the focus-check output format are
already substantively there, drop; otherwise fold those two blocks in (ADR 0001's "the skill
gains the invocation guidance").
Acceptance: a 16-row disposition table (this one, corrected by the builder where the
developer-focus read changes a verdict) is staged for the #32 close-out comment; every fold
lands as a diff in `primitives-core/`; every drop names its covering primitive.

**B — python-standards command trio + templates (per owner decision 1).**
Recommended path: fold `python-init` / `python-fix` / `python-validate` intent into ONE new
skill (working name `python-project-standards`, plugins: `[python-standards]`) that carries
the four `templates/` files as skill assets (fetch from the remote repo at the frozen HEAD;
record provenance in the skill). The ty-* trio stays dropped regardless.
Acceptance: new roster entry passes `make ci` (roster + targets drift guards green); the
skill's SKILL.md covers scaffold/fix/validate; `templates/` content byte-matches the remote
tree at the archived ref; `plugins.yaml` python-standards version bumped minor (membership
changed — the rule adopted in #40 decision 4). If the owner instead rules drop-all:
acceptance is the close-out note naming the four template files as intentionally dropped.

**C — Fix the dev-focus Stop hook (per owner decision 2).**
Recommended path: strip the `session-summary.py` invocation from
`dev-focus.Stop.stop-summary.sh` (the script violates the stdlib-only hook convention,
`_config.md:55` — it needs uv + API keys) and note the session-summary capability as
dropped; alternatively gate it behind a path-exists check with a visible skip message.
Acceptance: no hook handler in `primitives-core/` references a file that does not exist in
its shipped bundle (greppable check: every `$SCRIPT_DIR`/`${CLAUDE_PLUGIN_ROOT}` path in
`primitives-core/hooks/**` resolves inside the plugin's built folder under `targets/`);
`make ci` green; `plugins.yaml` dev-focus version bumped.

**D — Retire the `skills` CLI (per owner decision 3).**
Recommended path: delete `~/dotfiles/bin/.local/bin/skills` (dotfiles repo). Its replacement
surface already exists: `claude plugin list/enable/disable/marketplace update` for
toggleables, `npx skills` for vendor installs into `~/.agents/skills/`, dotfiles-bootstrap
for deploy. The issue's `skills doctor` acceptance line is restated as: `ls -l
~/.claude/skills/` shows zero dangling symlinks (already true; re-verify at close-out) and
no shipped tool references the retired repo path.
Acceptance: `command -v skills` empty (or the rewritten tool exits 0 with no
hsb3-custom-plugins reference); `rg --hidden 'FUNCTIONFORM|hsb3-custom-plugins' ~/dotfiles
--glob '!.git'` returns only historical/memory-note hits that deliverable E rewrites.

**E — Doc + memory hygiene (dotfiles repo, rides with D).**
Rewrite the three stale surfaces to the current model (marketplace cache from
`dotfiles-agents` + `~/.agents/skills/` vendor installs + `~/.claude/skills/` as thin
symlink shims):
1. `~/dotfiles/claude-code/.claude/memory/reference-skills-system.md` — full rewrite; also
   remove the pointer to the nonexistent `_docs/reference/skills-inventory.md`.
2. `~/dotfiles/CLAUDE.md:172` — replace or delete the `skills` CLI row to match D.
3. The `skills` row in `~/dotfiles/claude-code/.claude/instructions/tools.md` (same edit).
4. Delete the stray `~/dotfiles/claude-code/.claude/settings copy.bak` (owner confirm — it
   is a .bak with old-marketplace references).
Acceptance: `rg --hidden -l 'hsb3-custom-plugins' ~/dotfiles --glob '!.git'` returns zero
files (or only a deliberate historical note that states the repo is archived).

**F — Archive the GitHub repo + close out #32.**
After A-E land: `gh repo archive hsb3/hsb3-custom-plugins` (outward-facing — owner approval
per `_config.md:52`), then post the close-out comment on #32 carrying: the disposition
table (A), the stale-framing note (symlink work shipped 2026-07-02, before this plan), the
restated acceptance evidence (symlink ls output, `make ci` run, rg sweeps), and the archive
confirmation.
Acceptance: `gh repo view hsb3/hsb3-custom-plugins --json isArchived` returns `true`; #32
closed with the comment; `reconcile.py` clean for this plan's row.

**G — (optional, decision 4) Track the two live vendor installs.**
Add `auth0-cli` to `externals.yaml` (`kind: skill`, upstream + ref, per the existing
`kind: skill` entries at `externals.yaml:58-103`) and refresh the roster's `find-skills`
pinned ref to the deployed upstream version (the `--owner` flag delta). Keeps
"externals are tracked, not vendored" true for everything actually on the machine.
Acceptance: `externals.yaml` yamllint-clean; find-skills roster `ref:` matches the deployed
SKILL.md content after `make build`.

## Gate & contract hygiene

| Gate | Fires? | Why |
| ---- | ------ | --- |
| CI aggregate (make ci) | yes | always; B/C edit primitives-core/ |
| Targets drift guard (make build-check) | yes | any primitives-core/ edit (A folds, B, C) regenerates targets/; never hand-edit targets/ |
| Roster drift guard (make check) | conditional | fires only if decision 1 adds the python-project-standards skill; drop-all path leaves the roster untouched |
| Naming taxonomy (manifests/naming.md) | conditional | only the new skill name under decision 1 |
| yamllint / actionlint | conditional | only if G edits externals.yaml; no workflow files touched anywhere in A-G |

Contract notes: plugin membership changes (B adds a skill to python-standards; C edits a
dev-focus hook) each bump that plugin's minor version in `plugins.yaml` per the #40
decision-4 rule — coordinate with #27 so versions are bumped once, not twice. D/E/F touch
the `~/dotfiles` repo and GitHub, outside every gate here; their acceptance is the rg
sweeps + `gh repo view` evidence in the close-out. The archive step (F) is one-way on
GitHub (reversible only via unarchive) — it is the sanctioned destructive-ish op and runs
last, after everything worth rescuing is committed here.

## Parallelism + landing order

| Unit | Owner | Depends on | Notes |
| ---- | ----- | ---------- | ----- |
| A | one builder | decisions 1-2 ruled | reads developer-focus skill; stages the disposition table; folds (if any) are primitives-core edits |
| B | same builder as A | decision 1 | same plugin family surface; fetch templates from remote HEAD before archive |
| C | one builder | decision 2 | disjoint files from A/B (dev-focus hooks only); parallel with A/B |
| D | one builder | decision 3 | dotfiles repo; parallel with A-C (different repo) |
| E | same builder as D | D ruled | doc rewrites must state the model D leaves behind |
| F | foreman | A-E landed, owner approval | archive + close-out comment; strictly last |
| G | follow-up builder | decision 4 | independent; can ride the A+B+C PR or trail |

Landing order: one PR in dotfiles-agents (A+B+C, plus G if approved) gated on `make ci`;
one commit in `~/dotfiles` (D+E); then F. Nothing here waits on #27, but if #27's rename PR
is in flight, land whichever is ready first and let the second rebase the `plugins.yaml`
version lines.

## Open questions / owner decisions

1. **python trio: fold into one new skill (with templates) or drop all six python-standards
   commands?** Recommended default: **fold python-init/fix/validate into one
   `python-project-standards` skill carrying the 4 templates; drop the ty-* trio.** The
   templates are real content that dies with the archive otherwise; the hooks only enforce,
   they don't scaffold. Alternative: drop-all with the templates named in the close-out.
2. **dev-focus session-summary: strip the dangling script call or migrate the script?**
   Recommended default: **strip it and drop the capability with a note.** Migrating
   `session-summary.py` violates the stdlib-only hook convention (`_config.md:55`) and pulls
   uv + API-key runtime deps into a hook bundle.
3. **`skills` CLI: retire or rewrite?** Recommended default: **retire (delete the script +
   its doc rows).** Every subcommand's job is covered by `claude plugin`, `npx skills`, or
   dotfiles-bootstrap; a doctor-only rewrite can be a fresh, small tool later if symlink
   drift actually recurs.
4. **Track auth0-cli in externals.yaml + refresh the find-skills ref now (G), or defer?**
   Recommended default: **do it in this wave** — it is two small tracked-not-vendored
   entries and closes the last untracked extender on the machine; defer only if the wave
   needs to stay minimal.
5. **Issue body: edit to the true residual, or leave and correct via close-out comment?**
   Recommended default: **leave the body; correct in the close-out comment** (provenance of
   the T-15 framing stays legible; outward edits need owner approval anyway,
   `_config.md:52`).
6. **`settings copy.bak` deletion (E.4)?** Recommended default: **delete** — it is an
   untracked-style backup with stale marketplace references; confirm nothing in it is
   unrecovered before removal.
