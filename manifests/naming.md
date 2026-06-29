_The naming taxonomy every primitive and plugin must follow. Lint-enforced (Phase 3 drift guard)._

Status: active — created 2026-06-28

Source of truth for naming; derived from the technical plan §5. The roster
([`../primitives-core.yaml`](../primitives-core.yaml)) tracks ownership/vendor; **names never encode the vendor**
(except a `-henry` suffix for a personalized fork — see skills below).

## Patterns

| Primitive | Pattern | Examples | Rule |
|---|---|---|---|
| **skill** | `<domain>-<capability>` kebab | `cms-bigquery-etl`, `office-pptx`, `frontend-carbon-builder` | `domain` ∈ {cms, frontend, office, dev, agents, infra, docs, …}. Ownership/vendor tracked in the roster, **not** the name. Suffix `-henry` **only** for a personalized fork of a vendor skill (e.g. `pptx-henry`). |
| **agent** | `<domain>-<role>[-<verb>]` kebab | `fastapi-best-practices-reviewer`, `python-test-writer`, `langgraph-designer` | `role` ∈ {reviewer, builder, writer, architect, prototyper, designer, …}. |
| **hook** | handler: `<plugin>.<Event>.<slug>.sh` · `hook.toml` beside it | `python-standards.PostToolUse.ruff-format.sh`, `dev-focus.Stop.session-summary.sh` | Filename **encodes the firing event + owning plugin**. `<Event>` is the exact Claude PascalCase event (`SessionStart`, `PreToolUse`, `PostToolUse`, `Stop`, `UserPromptSubmit`, …). Handlers use **stdlib only** (bash builtins / python stdlib — no pip/npm deps). |
| **plugin** | `<domain>-<function>` kebab | `python-standards`, `github-projects-board-management` | — |
| **mcp** | `<service>` kebab | `notion`, `langchain` | one spec file per service. |

## Why these rules

- **Domain-first, vendor-out-of-name** keeps a primitive findable by what it does, and lets a vendored
  skill and our fork of it sit side by side (`pptx` vs `pptx-henry`) without renaming churn.
- **Event-in-filename for hooks** makes the firing semantics legible from `ls` alone, and groups a plugin's
  hooks together; the `hook.toml` carries the matcher + target tools.
- **stdlib-only handlers** is a promotion standard (technical-plan §6): no install step, runs anywhere the
  base interpreter exists.
