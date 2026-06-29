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
| `hooks/<name>/` | **hook** | handler `<plugin>.<Event>.<slug>.sh` + `hook.toml` | Claude-Code-only; handlers are **stdlib-only** (no pip/npm deps). |

## Rules

- **One source copy per primitive.** A plugin that ships a skill *references* it in the roster; it
  does not keep its own copy. The translation service materializes plugin bundles at build time.
- **Every primitive is registered** in [`../primitives-core.yaml`](../primitives-core.yaml). A
  drift test (Phase 3) fails if anything on disk is unregistered, or any roster entry is missing on disk.
- **Naming is lint-enforced** against [`../manifests/naming.md`](../manifests/naming.md).
