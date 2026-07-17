# dotfiles-agents

A Claude Code marketplace of proven coding-agent extenders, assembled from a single canonical
source (`primitives-core/`) into installable plugin bundles.

Clean-room rebuild to the 0007 lineup: two self-authored bundles — **project-workflow** (the
session-discipline loop) and **repo-standards** — plus one-skill standalone distribution.
Claude-Code-only; the marketplace resolves by name as `<plugin>@dotfiles-agents`.

> **Status:** rebuild in progress. This is the D1 fresh-history base — the build harness and
> the regenerate + drift-guard pattern, seeded with one primitive wired end to end
> (`project-workflow` / `handoff`). The bundle ports (D2–D4), the entry-gate CI floor (D6),
> and the READMEs (D8) land on top of it.

## Layout

| Path | What |
|---|---|
| `primitives-core/` | the single source copy of every primitive (`skills/`, `agents/`, `hooks/`) |
| `primitives-core.yaml` | the roster — the authoritative manifest of every primitive |
| `plugins.yaml` | plugin-bundle metadata (name / version / description) |
| `plugins/` | **generated** — assembled Claude Code plugin bundles (never hand-edited) |
| `.claude-plugin/marketplace.json` | **generated** — the marketplace root |
| `hooks/` | the ratified hook-dir layout (`hooks/<name>/hook.py`) |
| `scripts/` | roster guard + generators, each with a `--check` drift mode |
| `tests/` | stdlib-only unit tests (zero install) |
| `docs/decisions/` | in-repo ADR mirrors |

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
