---
title: "Build plan — convert ra-platform .claude/commands to a formal skill (#37)"
type: spec
status: draft
created: 2026-07-03
purpose: Source-grounded build plan for #37 — inventory of ra-platform's actual commands, the shipped-vs-residual finding (planning-desk already subsumes them), the adoption/retirement deliverables, gates, landing order, and open owner decisions.
notes: Drafted 2026-07-03. Key finding — the "redesign as a roster skill" half of the issue already shipped as the planning-desk skill (Phase 2a); the true residual is parity verification, ra-platform adoption, commands retirement, and the migration record. ra-platform inventoried via the GitHub API (no local checkout found on this machine).
---

# Convert ra-platform .claude/commands to a formal skill (first skills-over-commands migration)

_The issue as filed asks for ra-platform's `.claude/commands` content to be "redesigned as a
roster skill" — grounded in source, that redesign has ALREADY SHIPPED: the two commands
(`/issue-body`, `/plan-issue`) were generalized into the rostered `planning-desk` skill
(`primitives-core.yaml:523`, migrated in Phase 2a commit `39e208a`), whose `references/issue-body.md`
and `references/plan.md` are the parameterized versions of the two command bodies and whose
`scripts/_utils/` toolkit is a superset of ra-platform's desk scripts. The RESIDUAL is therefore
adoption and retirement, not authoring: verify parity and fold any genuinely generic delta, give
ra-platform the `_meta/plans/_config.md` the skill's modes require (routing the ra-platform-specific
gate menu out of the command body and into project config), prove one real authoring cycle through
the skill in ra-platform, retire `.claude/commands/` there (clearing its CLAUDE-07 audit row), and
append a promotion-log-style migration record._

Status: draft
Date: 2026-07-03

## Tracking

- Issue: #37 (`type:feat`, milestone `P3 — Rollout and retire`, created 2026-07-02).
- Origin: **T-19** on the strategy-desk task list — "the first real skills-over-commands migration
  instance, including the work-surface-hygiene automation" (issue #37 body). T-19 itself is not
  findable in any on-disk desk doc (searched `~/Documents/Claude/Projects/dotfiles-agents-cowork/`
  and this repo); the issue body is its only local citation — flagged, not blocking. The binding
  decision is **skills-over-commands**: CANON decision 3 ("Commands dropped", ratified 2026-06-26)
  and its ADR `docs/decisions/0001-skills-over-commands.md` ("No command survives as-is. Each
  existing command's intent folds into its paired skill ... or the command retires with a rationale").
- Relations: **#27** (project-workflow v2 — its deliverable A renames `planning-desk` to `pw-plan`;
  this plan deliberately does NOT rename, see open question 2). The repo-meta-structure standard
  flags `.claude/commands/` as migration debt — checklist row **CLAUDE-07**
  (`primitives-core/skills/repo-meta-structure/references/checklist.md:47`,
  `flag-if-present: .claude/commands/`) — so deliverable D is also what clears ra-platform's
  audit row.
- Contract impact: as filed, the issue adds a roster skill (`primitives-core.yaml` entry + `targets/`
  regenerate). As grounded below, the skill already exists in the roster, so under the recommended
  path the contract impact is **conditional**: only if the parity audit (A) folds a delta into
  `primitives-core/skills/planning-desk/` do `targets/` regenerate (drift-guarded) and the
  `project-workflow` plugin version bump (currently `0.2.1`, `plugins.yaml:42`). No API/DB surface.
  The ra-platform-side changes are docs + file deletions in that repo.

## The problem (grounded in source)

### Inventory — what ra-platform's `.claude/commands/` actually holds

**No local checkout found.** `~/Developer/ra-platform` does not exist; `fd -H` sweeps of
`~/Developer` and the home tree find only the cowork desk folder
(`~/Documents/Claude/Projects/ra-platform-cowork/` — analyses/comms/decisions, no repo).
Inventory below is from the GitHub API against `hsb3/ra-platform` (default branch, read 2026-07-03).
Anything that exists only in a local ra-platform working tree on another machine is unverifiable
from here and flagged where it matters.

`.claude/` there holds exactly: `commands/` (2 files), `memory/`, `settings.json`. The commands:

| File | Size | Summary |
| ---- | ---- | ------- |
| `.claude/commands/issue-body.md` | 5,443 B, 73 lines | `/issue-body <n or description>` - drafts or fixes a conformant GitHub issue body (feature, bug, epic template tiebreaker), grounds the problem in path:line source, stages it at `_meta/plans/<slug>/issue-body.md`, checks the ra-platform gate menu (API-shape types drift #375, alembic migrations, risk-model `make check-model`, `make specs` and `make check`, terraform), verifies `conformance.py`, and stops for owner review before any push |
| `.claude/commands/plan-issue.md` | 4,710 B, 68 lines | `/plan-issue <n, slug, or description>` - writes the deep source-grounded build plan at `_meta/plans/<slug>/plan.md` to the house schema (residual summary, Tracking, problem-grounded-in-source, A/B/C deliverables with acceptance, gate table, parallelism table, numbered owner decisions - never timelines) |

Provenance: both created in ra-platform PR #707 (`53c3c33`, 2026-06-18, "feat(authoring):
/issue-body + /plan-issue commands + CLAUDE.md rule"); last touched by #890 (`5224662`, 2026-06-27).
ra-platform's `CLAUDE.md` binds them at its "Authoring issues & plans" section (lines ~121-141:
"Use **`/issue-body <n>`** ...", "Use **`/plan-issue <n>`**"). Note the commands are already stale
against their own repo: `issue-body.md` lines 10-12 describe `_meta/plans/` as gitignored/local-only,
while `CLAUDE.md:132` states "**`_meta/plans/` is git-tracked** (negated in `.gitignore`)" — and the
desk (`README.md`, `_utils/`, ~25 plan folders) is indeed visible on GitHub. Drift like this is the
skills-over-commands argument in miniature: one capability, two unsynchronized homes.

### EXISTS — the redesign already shipped as `planning-desk`

- **Roster entry:** `planning-desk`, `type: skill`, `source: primitives-core/skills/planning-desk`,
  `shelf: core`, `origin: authored`, `disposition: grandfathered-pending-use`,
  `plugins: [project-workflow]` (`primitives-core.yaml:523-531`). Landed in Phase 2a
  (commit `39e208a`, PR #12, 2026-06-28) from the retiring `hsb3-custom-plugins` — i.e. the
  generalization happened there, ten days after ra-platform's #707 created the originals.
- **Command bodies subsumed:** `primitives-core/skills/planning-desk/references/issue-body.md`
  ("Mode: issue") and `references/plan.md` ("Mode: plan") carry the same procedure, standards, and
  non-negotiables as the two commands, with every ra-platform-specific binding parameterized:
  "Read `_meta/plans/_config.md` first — it names this project's issue templates, required sections,
  gate menu, and canonical docs" (`references/issue-body.md:7-8`; same in `plan.md`). The skill has
  zero ra-platform strings (`rg -i ra-platform` over the skill dir: no hits).
- **Toolkit subsumed:** `planning-desk/scripts/_utils/` is a superset of ra-platform's tracked
  `_meta/plans/_utils/`: `conformance.py` (5,029 B), `coverage.py` (5,447 B), `reconcile.py`
  (8,951 B), `sync-bodies.py` (5,367 B) are byte-size-identical to ra-platform's; `deps-suggest.py`
  (6,088 to 6,296 B), `evidence-audit.py` (4,956 to 4,972 B), `sequence.py` (7,607 to 7,725 B) are
  slightly larger (generalized); plus a `_repo.py` helper ra-platform lacks. This toolkit is the
  most plausible referent of the issue's "work-surface-hygiene automation" (unverified — open
  question 6).
- **Distribution path live:** `plugins.yaml` `project-workflow` is at `version: "0.2.1"`
  (`plugins.yaml:41-42`, post-#40 refresh); the documented consume path is
  `claude plugin marketplace add hsb3/dotfiles-agents` + `claude plugin install
  project-workflow@dotfiles-agents` (`docs/plugins/project-workflow.md:33-36`); this machine's
  installed cache already has `0.2.1` including `planning-desk`
  (`~/.claude/plugins/cache/dotfiles-agents/project-workflow/0.2.1/skills/`).
- **Standard + record scaffolding in place:** CLAUDE-07 flags `.claude/commands/` as migration debt
  citing ADR 0001 (`checklist.md:47`); the append-only promotions log exists with record templates
  and a precedent for cross-repo dotfiles-agents event records (the 2026-07-03 Q-13 batch record for
  da#31 in `dotfiles-agents-workbench/docs/promotions-log.md`).
- **Setup mode exists for adoption:** `planning-desk/SKILL.md` "Setup" scaffolds a desk into a repo —
  copy the toolkit, wire the gitignore negation, and detect-then-write `_meta/plans/_config.md` from
  `assets/_config.template.md`. ra-platform already has the desk and toolkit; only the config file
  applies.

### MISSING — the true residual

- **ra-platform has no `_meta/plans/_config.md`** (absent from the GitHub `_meta/plans/` listing;
  the dir holds `README.md`, `_utils/`, ~25 plan folders, loose scripts). The skill's issue/plan
  modes read it first; without it they fall back to nothing — the ra-platform gate menu currently
  lives hardcoded in `issue-body.md` step 4 (lines 44-50) and would be lost on retirement.
- **No verified use of the skill in ra-platform.** The issue's AC "ra-platform verified working with
  the skill" has no evidence anywhere; `planning-desk`'s roster disposition is
  `grandfathered-pending-use`, which per `dotfiles-agents-workbench/docs/requalification.md`
  upgrades to `qualified` only via >=2 cited real uses — this migration should mint citation #1.
- **`.claude/commands/` still present in ra-platform** — the CLAUDE-07 audit row fires there; and
  `CLAUDE.md` still routes authoring through `/issue-body` / `/plan-issue`.
- **No migration record.** ADR 0001's consequences require fold-or-retire *with a rationale*; the
  issue's AC requires "a promotion-log-style note".
- **Parity not yet audited line-by-line.** The subsumption above is verified at the structure and
  procedure level; a per-clause diff (e.g. whether the command's "sync-bodies --push is
  all-or-nothing" warning at `issue-body.md:63-66` survives in `references/issue-body.md` or
  `references/toolkit.md`) has not been done and is deliverable A.

## Deliverables

**A — Parity audit + conditional delta fold (dotfiles-agents side).**
Line-by-line diff of both ra-platform command bodies against
`planning-desk/references/{issue-body,plan}.md` and `references/toolkit.md`. Classify every clause:
(1) subsumed — no action; (2) generic and missing — fold into the skill reference (this repo);
(3) ra-platform-specific (the step-4 gate menu, template names, canonical-doc list) — route to B's
`_config.md`, NEVER into the skill (agnostic capability, project context in config — the CANON 13
principle applied to projects). Expected outcome: zero-to-small class-2 delta.
`Acceptance:` the classification is recorded (PR description or an addendum in this plan folder);
`rg -i ra-platform primitives-core/skills/planning-desk/` returns zero hits; if any class-2 fold
lands: `make ci` green, `targets/` regenerated via `make build`, and the `project-workflow` version
bumped once (coordinated with #27 — verify, don't double-bump).

**B — ra-platform desk config (`_meta/plans/_config.md`).**
Author it from `planning-desk/assets/_config.template.md` per the skill's setup step 3, carrying
over the command's embedded project bindings: gate menu (API-shape → `schemas.py` +
`api-contract.md` + `pnpm generate:types` #375 drift guard; DB migration → alembic revision +
bootstrap `--args migrate`; risk-model → `make check-model` + mechanics doc + values JSON;
generated artifacts → `make specs` / `make check`; infra → reviewed `terraform plan`; always
`make check` + pnpm lanes), issue templates + required sections, canonical docs
(`docs/design-technical/*`, `docs/decisions/*`).
`Acceptance:` file tracked on ra-platform main; it names every gate family from the retired
command's step 4 (grep each of the five against the new file); `python3
_meta/plans/_utils/conformance.py` and `reconcile.py` run clean from the ra-platform main tree.

**C — Consumption via the standard distribution path + live proof.**
On the working machine: plugin at current version (cache already holds `0.2.1`; update via
`/plugin` if the delta fold in A bumps it), then run ONE real authoring cycle in ra-platform through
the skill — issue mode or plan mode on a live ra-platform issue, producing a staged
`issue-body.md` or `plan.md` that passes `conformance.py`.
`Acceptance:` `/project-workflow:planning-desk` resolves in a ra-platform session; the produced
artifact + its issue/PR ref exists as a citable use (this is the issue's "ra-platform verified
working with the skill" AC, and use-citation #1 toward `planning-desk`'s
`grandfathered-pending-use` upgrade).

**D — Retire `.claude/commands/` in ra-platform.**
Delete `issue-body.md` + `plan-issue.md`; rewrite `CLAUDE.md`'s "Authoring issues & plans" section
to invoke the skill's modes (and drop the two `/command` references); keep the tracked
`_meta/plans/_utils/` (open question 4).
`Acceptance:` `gh api repos/hsb3/ra-platform/contents/.claude/commands` returns 404; `rg` for
`/issue-body` and `/plan-issue` over the ra-platform tree returns zero hits; the
repo-compliance-audit CLAUDE-07 row reports pass (flag-if-present target absent) — clearing
ra-platform's audit-debt row.

**E — Promotion-log-style migration record.**
A dated, append-only record of the migration: cites #37, ra-platform #707 (origin of the commands),
Phase 2a `39e208a` (the fold), the D retirement PR, and C's use citation; states the fold-or-retire
disposition per ADR 0001 and notes `planning-desk`'s use-count progress. Home per open question 5
(default: `dotfiles-agents-workbench/docs/promotions-log.md` Records, following the da#31
precedent).
`Acceptance:` record appended in the same change set as D (or immediately following, cross-linked);
follows the log's append-only discipline and template style; every cited ref resolves.

## Gate & contract hygiene

Gates from `_meta/plans/_config.md`'s menu; ra-platform's own lanes noted separately.

| Gate | Fires? | Why |
| ---- | ------ | --- |
| CI aggregate (make ci) | conditional | fires on any dotfiles-agents PR from A's delta fold; if A finds zero class-2 delta, no dotfiles-agents PR exists at all |
| Roster drift guard (make check) | no | recommended path adds, removes, and renames no primitive; fires only under the open-question-1 alternative (author a new skill) |
| Targets drift guard (make build-check) | conditional | only if A edits planning-desk source; fix with make build, never hand-edit targets/ |
| Naming taxonomy | no | no new primitive name; the planning-desk to pw-plan rename is owned by #27, not this plan |
| yamllint / actionlint | no | no workflow or YAML-structure edits; a plugins.yaml version bump is value-only |

Not in this repo's menu but binding on B and D: ra-platform's own PR lanes run on those changes
(docs + deletions only — no API-shape, DB, risk-model, or infra surface is touched, so none of the
gate families B records in `_config.md` fire on the migration PRs themselves). Contract hygiene:
the checklist stable-ID contract is untouched (CLAUDE-07 is cited, not edited); the promotions log
is append-only (E adds, never rewrites).

## Parallelism + landing order

| Unit | Owner | Depends on | Notes |
| ---- | ----- | ---------- | ----- |
| A | one read-mostly auditor | none | delta classification first; conditional small fold PR in dotfiles-agents |
| B | one builder | A classification | ra-platform PR; consumes the class-3 clauses A routes to config |
| C | foreman | B landed, plugin current | live proof run from the ra-platform main tree; produces the use citation |
| D | one builder | C verified | ra-platform PR; do not retire the commands before the replacement is proven working |
| E | foreman | D | append the record, same change set as D or cross-linked immediately after |

A is the only unit that can start immediately. B and the plugin-update half of C can proceed in
parallel once A's classification exists (disjoint repos). D strictly serializes after C — retiring
the commands before a proven skill cycle would leave ra-platform without a working authoring path.
No timelines.

## Open questions / owner decisions

1. **Reuse `planning-desk`, or author a new skill as the issue's wording implies?**
   **Recommend: reuse.** The redesign the issue asks for already shipped (Phase 2a); a second
   skill covering the same two modes would fail the J4-distinctness principle and re-create the
   two-homes drift this migration exists to end. The issue's "redesigned as a roster skill" AC is
   satisfied by citing the existing entry + A's parity audit. Alternative: new skill — fires the
   roster guard + naming lane and needs a dedup rationale against planning-desk.
2. **Skill id vs the naming lane ("kebab id passing the names lane").** `planning-desk` does not
   cleanly match `manifests/naming.md`'s `<domain>-<capability>` grammar, but #27's deliverable A
   already renames it to `pw-plan` across the roster. **Recommend: leave the id untouched here;
   #27 owns the rename.** If #27 lands before D, ra-platform's rewritten CLAUDE.md should reference
   the `pw-plan` invocation instead — check at D time.
3. **How ra-platform consumes: marketplace plugin vs project `.claude/skills/`.**
   **Recommend: the marketplace plugin** (`project-workflow@dotfiles-agents`), the documented
   standard distribution path (`docs/plugins/project-workflow.md:33-36`) — machine-level install,
   already present at `0.2.1`. Copying the skill into ra-platform's `.claude/skills/` would re-fork
   the source and defeat the one-canonical-copy rule (CANON 2). Sub-decision: also pin
   `enabledPlugins` in ra-platform's tracked `.claude/settings.json` so fresh machines and cloud
   sessions get it? Recommend yes if the field is supported in the current Claude Code settings
   schema (verify at C time); otherwise document the install step in ra-platform's CLAUDE.md.
4. **ra-platform's tracked `_meta/plans/_utils/` — keep or remove?** **Recommend: keep, resynced.**
   The skill's own setup mode installs the toolkit INTO the repo (tracked scripts work in fresh
   clones, cloud sessions, and CI without the plugin); ra-platform's CLAUDE.md and desk workflow
   already depend on them. D should diff them against the skill's `scripts/_utils/` and adopt the
   three slightly-newer generalized scripts + `_repo.py` if compatible. Alternative: delete and rely
   on the plugin cache — rejected, breaks worktree/cloud sessions.
5. **Where does the migration record (E) live?** **Recommend:
   `dotfiles-agents-workbench/docs/promotions-log.md`** — it is the established append-only record
   home with templates, and already records dotfiles-agents roster events (the 2026-07-03 Q-13
   batch record for da#31). Framed as a dated callout record (like the wb#10/wb#25 entries), not a
   promotion record — nothing enters or exits the trusted set. Alternative: a new
   `docs/migrations-log.md` in dotfiles-agents — rejected as a second log for one record.
6. **What is the "work-surface-hygiene automation" (issue body, from T-19)?** Not findable in any
   on-disk source. **Recommend interpreting it as the desk governance toolkit already bundled in
   planning-desk** (`reconcile.py`, `coverage.py`, `evidence-audit.py` — the scripts that keep the
   work surface honest) plus the CLAUDE-07 audit row this migration clears — i.e. no additional
   automation to build. Owner to confirm; if T-19 meant something more (e.g. a hook or CI lane that
   flags `.claude/commands/` on push), that is a separate issue, not silent scope here.
