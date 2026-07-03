# Compliance checklist — repo meta-structure

The **machine-consumable surface** of the standard. The repo-compliance-audit skill reads
these rows and executes them; zero checklist items for this standard are defined anywhere
else. Adding or changing a check means editing this file, not the audit.

**Contract:**

- Columns are `ID | Area | Check | Pass condition`. The **stable IDs are the machine
  contract** — they never change, even if the skill is renamed. Rows may be added; IDs are
  never reused.
- The Check column is `<check-type>: <argument>`, with `<check-type>` drawn from a closed
  vocabulary: `path-exists`, `gitignore-tracks`, `gitignore-ignores`, `frontmatter-has`,
  `no-inline-hooks`, `flag-if-present`. New check *types* are an audit-script change; new
  check *rows* belong here.
- `gitignore-tracks` / `gitignore-ignores` arguments are probe paths evaluated with
  `git check-ignore` (tracks = exit 1 / not ignored; ignores = exit 0 / ignored). Probe
  paths need not exist on disk.
- `flag-if-present` rows are inverted: the path being **absent** is the pass. Rows marked
  *(migration debt)* are reported with migration-debt wording, distinct from a structural gap.
- Per-repo variance declared in `_meta/mise-en-place.yml` (e.g. `required_folders`,
  `default_branch`) is applied by the audit on top of these rows; the rows themselves are
  invariant.

## `_meta/` layout

| ID | Area | Check | Pass condition |
|---|---|---|---|
| META-01 | `_meta/` | `path-exists: _meta/_archive/` | Directory exists |
| META-02 | `_meta/` | `path-exists: _meta/briefings/` | Directory exists |
| META-03 | `_meta/` | `path-exists: _meta/plans/` | Directory exists |
| META-04 | `_meta/` | `path-exists: _meta/operations/` | Directory exists |
| META-05 | `_meta/` | `path-exists: _meta/research/` | Directory exists |
| META-06 | `_meta/` | `path-exists: _meta/HANDOFF.md` | File exists |
| META-07 | `_meta/` | `path-exists: _meta/README.md` | File exists (states the `_meta/` taxonomy) |

## `.claude/` layout

| ID | Area | Check | Pass condition |
|---|---|---|---|
| CLAUDE-01 | `.claude/` | `path-exists: .claude/agents/` | Directory exists |
| CLAUDE-02 | `.claude/` | `path-exists: .claude/hooks/` | Directory exists |
| CLAUDE-03 | `.claude/` | `path-exists: .claude/memory/` | Directory exists (index/content rules are `MEM-xx`, owned by the memory-taxonomy standard) |
| CLAUDE-04 | `.claude/` | `path-exists: .claude/rules/` | Directory exists |
| CLAUDE-05 | `.claude/` | `path-exists: .claude/skills/` | Directory exists |
| CLAUDE-06 | `.claude/` | `path-exists: .claude/settings.json` | File exists (tracked project policy; must carry anything a headless run depends on) |
| CLAUDE-07 | `.claude/` | `flag-if-present: .claude/commands/` | Absent — commands are migration debt per the skills-over-commands decision (ADR: `dotfiles-agents/docs/decisions/0001-skills-over-commands.md`) *(migration debt)* |

## `.github/` template set

| ID | Area | Check | Pass condition |
|---|---|---|---|
| GH-01 | `.github/` | `path-exists: .github/ISSUE_TEMPLATE/config.yml` | File exists |
| GH-02 | `.github/` | `path-exists: .github/ISSUE_TEMPLATE/bug.yml` | File exists |
| GH-03 | `.github/` | `path-exists: .github/ISSUE_TEMPLATE/feature.yml` | File exists |
| GH-04 | `.github/` | `path-exists: .github/ISSUE_TEMPLATE/epic.yml` | File exists |
| GH-05 | `.github/` | `path-exists: .github/PULL_REQUEST_TEMPLATE.md` | File exists |
| GH-06 | `.github/` | `path-exists: .github/dependabot.yml` | File exists |
| GH-07 | `.github/` | `path-exists: .github/workflows/ci.yml` | File exists |
| GH-08 | `.github/` | `path-exists: .github/workflows/claude-review.yml` | File exists |
| GH-09 | `.github/` | `path-exists: .github/workflows/claude.yml` | File exists |

(`release.yml` and `CHANGELOG.md` apply only to repos that publish releases — conditional,
so they are layout guidance, not checklist rows.)

## Root files

| ID | Area | Check | Pass condition |
|---|---|---|---|
| ROOT-01 | Root | `path-exists: README.md` | File exists |
| ROOT-02 | Root | `path-exists: CLAUDE.md` | File exists |
| ROOT-03 | Root | `path-exists: AGENTS.md` | File exists |
| ROOT-04 | Root | `path-exists: Makefile` | File exists (v1 task-runner default; this single row swaps if the task-runner decision lands differently) |
| ROOT-05 | Root | `path-exists: lefthook.yml` | File exists |
| ROOT-06 | Root | `path-exists: .gitignore` | File exists |
| ROOT-07 | Root | `path-exists: .mcp.json` | File exists |
| ROOT-08 | Root | `path-exists: docs/` | Directory exists |
| ROOT-09 | Root | `path-exists: scripts/` | Directory exists |
| ROOT-10 | Root | `path-exists: tests/` | Directory exists |

## docs/ minimum planning docs

The floor inside `docs/`: an orientation page, the canonical precedence page, and an ADR
directory with its convention + template. Deeper taxonomy (design workspaces, operations,
api, images, sops) is per-repo shape — layout guidance in [`layout.md`](layout.md), not rows.
`docs/CHARTER.md` is authored content (the repo's canonical page with an explicit precedence
rule) — the scaffold never creates it; the other four rows are template-backed.

| ID | Area | Check | Pass condition |
|---|---|---|---|
| DOCS-01 | `docs/` | `path-exists: docs/README.md` | Orientation page: what docs/ holds, the docs-vs-`_meta/` boundary |
| DOCS-02 | `docs/` | `path-exists: docs/CHARTER.md` | Canonical page with an explicit precedence rule (authored, never scaffolded) |
| DOCS-03 | `docs/` | `path-exists: docs/decisions/` | ADR directory exists |
| DOCS-04 | `docs/` | `path-exists: docs/decisions/README.md` | ADR convention (append-only, supersede-vs-correct) + index |
| DOCS-05 | `docs/` | `path-exists: docs/decisions/0000-template.md` | ADR template exists |

## `.gitignore` semantics

Evaluated with `git check-ignore` against probe paths — this tests the repo's *actual*
ignore behavior, not a byte-match against the template.

| ID | Area | Check | Pass condition |
|---|---|---|---|
| IGNORE-01 | gitignore | `gitignore-ignores: _meta/operations/probe` | Ignored (non-negated `_meta/` content stays local) |
| IGNORE-02 | gitignore | `gitignore-tracks: _meta/plans/probe.md` | Not ignored (`!_meta/plans/` negation effective — requires the `_meta/*` form) |
| IGNORE-03 | gitignore | `gitignore-tracks: _meta/plans/inbox/probe.md` | Not ignored (nested intake tracked through `!_meta/plans/`, no extra negation) |
| IGNORE-04 | gitignore | `gitignore-tracks: _meta/README.md` | Not ignored |
| IGNORE-05 | gitignore | `gitignore-tracks: _meta/HANDOFF.md` | Not ignored |
| IGNORE-06 | gitignore | `gitignore-tracks: _meta/mise-en-place.yml` | Not ignored (manifest survives clones and worktrees) |
| IGNORE-07 | gitignore | `gitignore-ignores: .env` | Ignored |
| IGNORE-08 | gitignore | `gitignore-tracks: .env.example` | Not ignored (`!.env*.example`) |
| IGNORE-09 | gitignore | `gitignore-ignores: .claude/settings.local.json` | Ignored (machine-local) |
| IGNORE-10 | gitignore | `gitignore-ignores: .claude/worktrees/probe/file` | Ignored (harness worktrees never tracked) |
| IGNORE-11 | gitignore | `gitignore-tracks: .claude/settings.json` | Not ignored (tracked project policy) |
| IGNORE-12 | gitignore | `gitignore-tracks: .claude/memory/MEMORY.md` | Not ignored (tracked memory travels with the repo) |
| IGNORE-13 | gitignore | `gitignore-tracks: _meta/_archive/.gitkeep` | Not ignored (the scaffolded dir survives a fresh clone; other `_meta/_archive/` content stays ignored) |
| IGNORE-14 | gitignore | `gitignore-tracks: _meta/briefings/.gitkeep` | Not ignored (the scaffolded dir survives a fresh clone; other `_meta/briefings/` content stays ignored) |
| IGNORE-15 | gitignore | `gitignore-tracks: _meta/operations/.gitkeep` | Not ignored (the scaffolded dir survives a fresh clone; `IGNORE-01` still holds — `_meta/operations/` content is never tracked) |
| IGNORE-16 | gitignore | `gitignore-tracks: _meta/research/.gitkeep` | Not ignored (the scaffolded dir survives a fresh clone; other `_meta/research/` content stays ignored) |
| IGNORE-17 | gitignore | `gitignore-ignores: _meta/plans/_utils/__pycache__/probe.pyc` | Ignored (desk-toolkit bytecode never tracked — the `_meta/plans/` negation would otherwise re-include it) |
| IGNORE-18 | gitignore | `gitignore-ignores: _meta/plans/.DS_Store` | Ignored (Finder litter — the `_meta/plans/` negation re-includes it past the global `.DS_Store` rule) |

## AVOID list

| ID | Area | Check | Pass condition |
|---|---|---|---|
| AVOID-01 | Root | `flag-if-present: TODO.md` | Absent at root — content belongs in `_meta/` |
| AVOID-02 | Root | `flag-if-present: NOTE.md` | Absent at root — content belongs in `_meta/` |
| AVOID-03 | Root | `flag-if-present: NOTES.md` | Absent at root — content belongs in `_meta/` |

## `_meta/plans/` planning docs

Scope: every `*.md` under `_meta/plans/` (recursive, including `inbox/`), **excluding**
`README.md` (the desk index), files whose name starts with `_` (desk config such as
`_config.md`), anything under `_utils/`, and `issue-body.md` files. Staged `issue-body.md`
files are exempt from the frontmatter schema: a staged issue body is the raw publishable
GitHub body, kept byte-identical to the live issue (owner ruling 2026-07-02). Field
semantics and the `type` vocabulary — including the two intake extensions — are defined in
[`planning-docs.md`](planning-docs.md). Gaps are reported at field granularity (file +
missing field).

| ID | Area | Check | Pass condition |
|---|---|---|---|
| PLANS-01 | `_meta/plans/` | `frontmatter-has: title` | Every in-scope doc's frontmatter has `title` |
| PLANS-02 | `_meta/plans/` | `frontmatter-has: type` | Every in-scope doc's frontmatter has `type` (vocabulary per `planning-docs.md`) |
| PLANS-03 | `_meta/plans/` | `frontmatter-has: status` | Every in-scope doc's frontmatter has `status` |
| PLANS-04 | `_meta/plans/` | `frontmatter-has: created` | Every in-scope doc's frontmatter has `created` |
| PLANS-05 | `_meta/plans/` | `frontmatter-has: purpose` | Every in-scope doc's frontmatter has `purpose` |
| PLANS-06 | `_meta/plans/` | `frontmatter-has: notes` | Every in-scope doc's frontmatter has `notes` |

## Deferred families (owned elsewhere — no orphaned gaps)

- **`MEM-xx` (memory structure)** — tracked `.claude/memory/` with a `MEMORY.md` index and
  the taxonomy rules: owned by the **memory-taxonomy standard** (its own packaged skill and
  checklist). Layout presence here is only `CLAUDE-03` / `IGNORE-12`.
- **`HOOK-xx` (hook packaging)** — hooks as script + config directories, never inline in
  `.claude/settings.json`: the interim `HOOK-01` check (`no-inline-hooks`) is sourced by the
  audit directly from the hooks-as-script-plus-config decision (ADR:
  `dotfiles-agents/docs/decisions/0002-hooks-as-script-plus-config.md`); the full family
  arrives with the deferred hook-composition standard.
- **Naming-grammar conformance** — arrives with the naming-taxonomy standard.
