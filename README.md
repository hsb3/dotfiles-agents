# dotfiles-agents

A Claude Code marketplace of proven coding-agent extenders, assembled from a single canonical
source (`primitives-core/`) into installable plugin bundles.

The lineup is organized around desk sets: two desk bundles — **code-desk** (slim
next-release execution under a documented repo standard) and **exec-desk** (the
executive-desk overhead: planning, comms, board triage, deck themes) — plus three kits —
**foreman-kit** (tiered delegation agents and session-discipline hooks, enabled on every
desk), **diagrams** (structural diagrams: Mermaid, Python cloud-architecture diagrams,
draw.io, Excalidraw, Graphviz), and **obsidian-toolkit** (Obsidian plugin-dev guidance and
vault automation) — and five standalone one-skill plugins (**github-project-board**,
**private-fork**, **opencode-expertise**, **owner-signoff**, **pptx-themes**). Cross-desk
items ship standalone, never inside a desk bundle. Claude-Code-only; the marketplace resolves by name as `<plugin>@dotfiles-agents`
(consumers install from `main`, the published branch).

## Layout

| Path | What |
|---|---|
| `primitives-core/` | the single source copy of every primitive (`skills/`, `agents/`, `hooks/`) |
| `primitives-core.yaml` | the roster — the authoritative manifest of every primitive |
| `plugins.yaml` | plugin-bundle metadata (name / version / description) |
| `dist/claude-code/` | **generated** — the assembled Claude Code marketplace lane (`plugins/`, `marketplace.json`, `PLUGINS.md`; never hand-edited), lifted to the root of `main` at publish |
| `dist/opencode/` | **generated** — the opencode laydown lane (skills verbatim, remapped agents, installer, exclusions manifest), published as `opencode/` on `main` |
| `hooks/` | the ratified hook-dir layout (`hooks/<name>/hook.py`) |
| `scripts/` | roster guard + generators, each with a `--check` drift mode |
| `tests/` | stdlib-only unit tests (zero install) |
| `docs/decisions/` | in-repo ADR mirrors |
| `flow.yaml` + `docs/FLOW.md` | the repo-flow DAG — the home of every part, machine-checked by `make flow` |

## Build interface

`make ci` is the task interface (CI runs it on every PR). See `make help`.

| Target | Does |
|---|---|
| `make check` | roster ↔ disk drift guard (schema + provenance) |
| `make build` | regenerate `plugins/` + `marketplace.json` from source |
| `make build-check` | verify the committed marketplace matches source (drift guard) |
| `make test` | run the unit tests |
| `make ci` | `check` + `build-check` + `test` |

**Generated artifacts are never hand-edited.** Change a primitive under `primitives-core/`,
then `make build`; `make ci` fails if a committed generated file drifts from its source.

## Governance

`dev` is the source branch; every change lands via PR into `dev`. `main` is CI-published
(publish-only). See `docs/decisions/` for the dev/main rule and `_meta/HANDOFF.md` for the
current build state.
