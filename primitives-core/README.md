# primitives-core

The **single canonical source copy** of every primitive. Edit primitives **here** — the
`plugins/<id>/` dirs are thin symlink assemblies over this tree
([decision-030](../docs/decisions/decisions-030-pointer-based-marketplace-symlink-plugin-assemblies-no-tracked-dist.md)): they add hand-authored
`plugin.json`/`hooks.json`/bundle READMEs and point at everything else with in-repo
symlinks, so an edit here IS the edit everywhere the primitive ships.

## The primitive types

| Dir | Primitive | Canonical form | Notes |
|---|---|---|---|
| `skills/<name>/` | **skill** | `SKILL.md` (+ optional `references/`, `scripts/`, `assets/`) | `SKILL.md` at the folder root. A skill's README travels with it (`skills/<name>/README.md`); a standalone plugin's root README is a symlink to it. |
| `agents/<name>.md` | **agent** | one `.md` with frontmatter | one workflow-aware agent per bundle is encouraged (P4). |
| `commands/<name>.md` | **command** | one `.md` with frontmatter | the slash surface an operator *or an agent* invokes (decision-010). A command stays thin: it loads a skill and drives it, never restating the procedure — one surface, one source of truth. |
| `hooks/<name>/` | **hook** | handler + config in the ratified hook-dir layout `hooks/<name>/hook.py` | Claude-Code-only; stdlib-only (no pip/npm deps). |
| `mcp/<name>.json` | **mcp** | one `.json` in the `.mcp.json` shape | symlinked to `plugins/<id>/.mcp.json`, which Claude Code auto-discovers, so installing the plugin registers the server. Instance values arrive by `${ENV_VAR}` only — see `mcp/README.md`. |

## Roster entry schema (provenance manifest, ADR 0017)

Every entry in [`../primitives-core.yaml`](../primitives-core.yaml) carries these fields
(enforced by [`../scripts/check_roster.py`](../scripts/check_roster.py)). Plugin membership
is **not** a roster field — membership is the symlink assemblies under `plugins/<id>/`,
guarded by [`../scripts/check_symlinks.py`](../scripts/check_symlinks.py):

| Field | Values | Notes |
|---|---|---|
| `id` | unique kebab-case name | |
| `type` | `skill` \| `agent` \| `command` \| `mcp` \| `hook` | |
| `source` | repo-relative path | must exist on disk (drift guard) |
| `origin` | `authored` \| `sourced` \| `vendored` | provenance; immutable per entry. `sourced` and `vendored` require non-null `upstream` + `ref`. |
| `disposition` | `qualified` \| `grandfathered-pending-use` \| `demoted` \| `untriaged` \| `orphaned` | owner-curated verdict. |
| `targets` | `[claude-code, opencode, codex]` subset | Claude Code and Codex install the assemblies; Codex roles are rendered at project setup. opencode is generated at install time (task-4). |
| `requires` | optional capability/dependency words | `{hooks,local-mcp,hosted-mcp}` + `cli:<kebab>` / `env:<kebab>`. |

`primitives-core` holds **self-authored** primitives only
([decision-028](../docs/decisions/decisions-028-primitives-core-is-self-authored-only-externals-by-reference.md)); third-party items are
recorded by reference in [`../externals.yaml`](../externals.yaml), never copied in.

## READMEs

Every primitive carries a README — the shop label; the body is the manual. A **skill's**
README lives in its dir (`skills/<id>/README.md`) and travels with it into every assembly
that symlinks the skill; a standalone plugin's root README is one more symlink to it. A
**hook's** README lives at `hooks/<id>/README.md` and ships the same way. **Agents** and
**commands** are single files, so each family shares one `agents/README.md` /
`commands/README.md` (exempted from roster discovery). A **bundle's** README describes the
composition, so it is hand-authored directly at `plugins/<id>/README.md` (top level, not
under `primitives-core/`). All of it ships to a user the same way a skill body does, so all
of it is in scope for the identity-neutrality lint (`scripts/check_identity.py`).

### Per-item README template

The README is the shop label a person reads before installing; the body is the manual the
model reads after. Write in directive voice, value first. What every per-item README carries,
in order:

1. `# <id>` plus one short paragraph — what it does and the outcome it buys.
2. `## When it triggers` (skills) / `## When it fires` (hooks) — the asks or events that
   invoke it, in user phrasing.
3. `## Install` — the `claude plugin install <plugin>@dotfiles-agents` command(s), one per
   plugin whose assembly carries it. `scripts/check_readmes.py` gates this: the set named
   must equal the set on disk.

**Skills** stay short — about 25 lines is the norm across the tree, and a skill README that
outgrows that is usually restating its body. Add a section only when the skill owes one:
`## Attribution` / `## Provenance` for vendored or sourced content (upstream, pinned ref,
license), `## Access` for a hosted service with an account gate, and
`## How it fits together` when the skill is also a standalone plugin's root README (the
plugin-README standard requires the diagram there).

**Hooks** run longer, and that is correct: a hook's body is code nobody installs a plugin to
read, so the README is its only human-facing document. The sections the tree has settled on:
`## Why` (the failure it exists to stop, when the lede cannot carry it), `## When it fires`,
`## Activation` (what arms it, when it is gated by a per-project file), `## Configuration`
(every env-overridable knob: variable, default, and the value the shipped wiring sets),
`## Install`, `## Design notes` (the decisions a reader would otherwise reverse — fail-open,
what it deliberately does not cover, override paths), and `## Ledger` (stream name and path,
when it writes one). Omit any section with nothing to say.

**Bundles** (`plugins/<id>/README.md`) follow `docs/readme-diagram-standard.md` instead: lede,
`## How it fits together`, the member table naming every shipped member (gated), `## Install`,
and an honest-scope section for the requirements and overlaps a reader hits after installing.

Nothing else: no feature inventories, no API reference, no version history. A fact that
matters only when *editing* the primitive belongs in the source, not the README. The template
describes the tree as it is and is revised when the tree outgrows it — measure before
tightening (`wc -l primitives-core/*/*/README.md`).

## The pointer invariant

Nothing generated is tracked (ADR 0017). The assemblies are hand-authored pointers;
`make symlinks` (in `make ci`) asserts every link resolves inside the repo and that the root
`.claude-plugin/marketplace.json` and the assemblies match 1:1.
