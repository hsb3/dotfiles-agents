# dotfiles-agents

Source of truth for proven coding-agent **extenders** (skills, agents, MCP servers, hooks), distributed to Claude Code, opencode, and Claude managed agents from a single set of primitives.

**Canonical page:** [`docs/CHARTER.md`](docs/CHARTER.md) — read first; it wins over anything here.

## Model (one screen)
- **Primitives** (one source copy each): agent · skill · mcp · hook. No commands.
- **Distribution targets** (generated, never hand-edited): plugins + raw primitives, under `targets/`.
- **Two shelves:** `core` (always-on, raw) · `toggle` (plugin/marketplace) — a roster attribute in `primitives-core.yaml`.

## Layout (target — built out in Phase 1–2)
- `primitives-core/{skills,agents,mcp,hooks}/` — the single source copies
- `primitives-core.yaml` (roster) · `primitives-core-translation-config.yaml` (adapters) · `primitives-core-translation-results.json` (lock)
- `targets/{claude-code,opencode,claude-agents}/` — generated bundles

## Conventions
- Naming taxonomy in `manifests/naming.md`. Hooks: `<plugin>.<Event>.<slug>.sh`, stdlib-only handlers.
- Generated artifacts are never hand-edited; a CI drift guard regenerates and fails on diff.
- Decision record: `~/Documents/Claude/Projects/dotfiles-agents-cowork/planning/CANON.md`.
