# primitives-core

The **single canonical source copy** of every primitive. Edit primitives **here** — the
`plugins/<id>/` dirs are thin symlink assemblies over this tree
([ADR 0017](../backlog/decisions/0017-pointer-based-marketplace.md)): they add hand-authored
`plugin.json`/`hooks.json`/bundle READMEs and point at everything else with in-repo
symlinks, so an edit here IS the edit everywhere the primitive ships.

## The primitive types

| Dir | Primitive | Canonical form | Notes |
|---|---|---|---|
| `skills/<name>/` | **skill** | `SKILL.md` (+ optional `references/`, `scripts/`, `assets/`) | `SKILL.md` at the folder root. A skill's README travels with it (`skills/<name>/README.md`); a standalone plugin's root README is a symlink to it. |
| `agents/<name>.md` | **agent** | one `.md` with frontmatter | one workflow-aware agent per bundle is encouraged (P4). |
| `hooks/<name>/` | **hook** | handler + config in the ratified hook-dir layout `hooks/<name>/hook.py` | Claude-Code-only; stdlib-only (no pip/npm deps). |

## Roster entry schema (provenance manifest, ADR 0017)

Every entry in [`../primitives-core.yaml`](../primitives-core.yaml) carries these fields
(enforced by [`../scripts/check_roster.py`](../scripts/check_roster.py)). Plugin membership
is **not** a roster field — membership is the symlink assemblies under `plugins/<id>/`,
guarded by [`../scripts/check_symlinks.py`](../scripts/check_symlinks.py):

| Field | Values | Notes |
|---|---|---|
| `id` | unique kebab-case name | |
| `type` | `skill` \| `agent` \| `mcp` \| `hook` | |
| `source` | repo-relative path | must exist on disk (drift guard) |
| `origin` | `authored` \| `sourced` | provenance; immutable per entry. `sourced` requires non-null `upstream` + `ref`. |
| `disposition` | `qualified` \| `grandfathered-pending-use` \| `demoted` \| `untriaged` | owner-curated verdict. |
| `targets` | `[claude-code, opencode]` subset | claude-code installs the assemblies natively; opencode is generated at install time (task-4). |
| `requires` | optional capability/dependency words | `{hooks,local-mcp,hosted-mcp}` + `cli:<kebab>` / `env:<kebab>`. |

`primitives-core` holds **self-authored** primitives only
([ADR 0015](../backlog/decisions/0015-self-authored-primitives-only.md)); third-party items are
recorded by reference in [`../externals.yaml`](../externals.yaml), never copied in.

## READMEs

Every primitive carries a README — the shop label; the body is the manual. A **skill's**
README lives in its dir (`skills/<id>/README.md`) and travels with it into every assembly
that symlinks the skill; a standalone plugin's root README is one more symlink to it. A
**hook's** README lives at `hooks/<id>/README.md` and ships the same way. **Agents** are
single files, so the family shares one `agents/README.md` (exempted from roster/agent
discovery). A **bundle's** README describes the composition, so it is hand-authored
directly at `plugins/<id>/README.md` (top level, not under `primitives-core/`). All of it
ships to a user the same way a skill body does, so all of it is in scope for the
identity-neutrality lint (`scripts/check_identity.py`).

### Per-item README template (tight scope)

15–25 lines, under 200 words, directive voice. Sections, in order:

1. `# <id>` plus one short paragraph — what it does and the outcome it buys, value first.
2. `## When it triggers` (skills) / `## When it fires` (hooks) — the asks or events that
   invoke it, in user phrasing.
3. `## Configuration` — hooks only, and only when env-overridable knobs exist: each
   variable, its default, and the value the shipped wiring sets.
4. `## Install` — the `claude plugin install <plugin>@dotfiles-agents` command(s) that
   deliver it, naming every bundle that carries it (a dual-homed skill lists both).

Nothing else: no feature inventories, no API reference, no version history, no restating
the body. A fact that matters only when *editing* the primitive belongs in the source, not
the README.

## The pointer invariant

Nothing generated is tracked (ADR 0017). The assemblies are hand-authored pointers;
`make symlinks` (in `make ci`) asserts every link resolves inside the repo and that the root
`.claude-plugin/marketplace.json` and the assemblies match 1:1.
