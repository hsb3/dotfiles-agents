# targets/ — GENERATED distribution bundles

> ⚠️ **GENERATED — never hand-edit.** Everything under `targets/` is produced by the translation
> service ([`../scripts/`](../scripts/), Phase 3) from [`../primitives-core/`](../primitives-core/).
> Edit the **source** primitive, not the rendered copy. A CI drift guard regenerates these and fails
> on any hand-edit.

Status: skeleton (Phase 1) — populated once the translation service lands (Phase 3)

## The three targets

| Dir | Target | Contents | Deploy |
|---|---|---|---|
| `claude-code/` | Claude Code | `.claude-plugin/marketplace.json` + `plugins/<plugin>/…` | **Must be static in-repo** — `claude plugin marketplace add <repo>` reads it from here. |
| `opencode/` | opencode | `skills/` · `agents/` (transformed) · `opencode.json` (mcp fragment) | Three different deploy destinations, not one. |
| `claude-agents/` | Claude managed agents | CMA API payloads / build-sheet per agent | Lower priority; adapter built after the CC+opencode MVP. |

Hooks ship to `claude-code/` only (`unsupported` elsewhere — see the translation config).
