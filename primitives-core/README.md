# primitives-core

The **single canonical source copy** of every primitive. Edit primitives **here** — the
`plugins/<id>/` dirs are thin symlink assemblies over this tree
([ADR 0017](../docs/decisions/0017-pointer-based-marketplace.md)): they add hand-authored
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
([ADR 0015](../docs/decisions/0015-self-authored-primitives-only.md)); third-party items are
recorded by reference in [`../externals.yaml`](../externals.yaml), never copied in.

## READMEs

A **standalone skill's** README lives in its skill dir (`skills/<id>/README.md`) and reaches
the plugin root as one more symlink. A **bundle's** README describes the composition, so it
is hand-authored directly at `plugins/<id>/README.md` (top level, not under
`primitives-core/`). Both ship to a user the same way a skill body does, so both are in
scope for the identity-neutrality lint (`scripts/check_identity.py`).

## The pointer invariant

Nothing generated is tracked (ADR 0017). The assemblies are hand-authored pointers;
`make symlinks` (in `make ci`) asserts every link resolves inside the repo and that the root
`.claude-plugin/marketplace.json` and the assemblies match 1:1.
