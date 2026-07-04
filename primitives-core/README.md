# primitives-core

The **single canonical source copy** of every primitive. Edit primitives **here** — never in
`targets/` (those are generated). This directory is the input to the translation service
([`../scripts/`](../scripts/), built in Phase 3); `targets/` is its output.

See [`../docs/CHARTER.md`](../docs/CHARTER.md) for the model and
[`../manifests/naming.md`](../manifests/naming.md) for the naming taxonomy every primitive must follow.

## The four primitive types

| Dir | Primitive | Canonical form | Notes |
|---|---|---|---|
| `skills/<name>/` | **skill** | `SKILL.md` (+ `references/`, `scripts/`, `assets/`) | Native on every target. `SKILL.md` at the folder root. |
| `agents/<name>.md` | **agent** | one `.md` with neutral frontmatter | Transformed per target (CC native, opencode reframes frontmatter, CMA renders to API). |
| `mcp/<name>.json` | **mcp** | one neutral server spec per service | Always rendered to each target's own config schema. |
| `hooks/<name>/` | **hook** | handlers `hooks-handlers/<plugin>.<Event>.<slug>.sh` + config `hooks/hooks.json` | Claude-Code-only; handlers are **stdlib-only** (no pip/npm deps). |

## Roster entry schema

Every entry in [`../primitives-core.yaml`](../primitives-core.yaml) carries these fields
(enforced by `scripts/check_roster.py` + `scripts/validate_primitives.py`):

| Field | Values | Notes |
|---|---|---|
| `id` | unique kebab-case instance name | hooks use `<plugin>.<Event>.<slug>` |
| `type` | `skill` \| `agent` \| `mcp` \| `hook` | |
| `source` | repo-relative path | must exist on disk (drift guard) |
| `shelf` | `core` \| `toggle` | |
| `origin` | `authored` \| `sourced` | provenance: written here vs cloned from an upstream repo. Immutable per entry — an item's authorship doesn't change. |
| `disposition` | `qualified` \| `grandfathered-pending-use` \| `demoted` \| `untriaged` | required. `untriaged` is a migration placeholder ("pre-seeded, not yet dispositioned", Q-13); real values are written by the promotion/re-qualification workflow. |
| `vendor` | string or `null` | |
| `targets` | subset of `claude-code`, `opencode`, `claude-agents` | |
| `plugins` | list of plugin ids | |
| `summary` | non-empty string | |
| `requires` | optional list: capability words `hooks`, `local-mcp`, `hosted-mcp` plus dependency declarations `cli:<kebab>` and `env:<kebab>` | per-primitive runtime needs the type × target matrix can't express. `cli:<name>` = a binary/app that must be installed (e.g. `cli:graphviz`); `env:<name>` = machine state the content assumes (e.g. `env:dotfiles`). `validate_primitives.py` forces a declaration when content references a machine-local tool, `~/dotfiles`, or `/Applications/` (issue #79). Absent = no special requirements. Capability subsetting is deferred; deploy tooling consumes the `cli:`/`env:` declarations. |
| `upstream` + `ref` | non-null, required when `origin: sourced` | upstream repo + pinned ref for clone-at-build (G4, deferred — no sourced entries exist yet). |

Duplicate keys within one entry: the tailored line parser keeps the last one (documented, not
guarded).

## Rules

- **One source copy per primitive.** A plugin that ships a skill *references* it in the roster; it
  does not keep its own copy. The translation service materializes plugin bundles at build time.
- **Every primitive is registered** in [`../primitives-core.yaml`](../primitives-core.yaml). A
  drift test (Phase 3) fails if anything on disk is unregistered, or any roster entry is missing on disk.
- **Naming is lint-enforced** against [`../manifests/naming.md`](../manifests/naming.md).
