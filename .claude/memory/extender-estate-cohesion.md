---
name: extender-estate-cohesion
description: The extender estate spans 3 surfaces; cohesion + datamodel analysis lives on the dev-tooling desk; datamodel is NOT greenfield
metadata: 
  node_type: memory
  type: project
  originSessionId: d283ab33-f349-4aa3-9de1-0570ea1449cb
  modified: 2026-07-22T19:20:26.464Z
---

> **Correction (2026-07-22):** paths below predate the EXECUTIVE_DESK reorganization;
> dev-tooling-desk is archived at
> `~/Documents/EXECUTIVE_DESK/Projects/ARCHIVE/dev-tooling-desk-old`, the desk estate now
> lives under `~/Documents/EXECUTIVE_DESK/Projects/` (desk-standard-desk,
> dotfiles-agents-desk, desk-standard-practice, desk-standard-tutorial).

The coding-agent extender estate is ONE system across three surfaces, reviewed as such starting 2026-07-20:

- **dotfiles-agents** — Claude-Code-only marketplace. opencode support is **planned but deferred** (Henry, 2026-07-20), mirroring desk-standard #12. So `gate:cross-tool` is a live deferred promise, not dead intent; the root `plugins/` layout (replaced `targets/claude-code/plugins` at the CC-only rebuild) will need revisiting when opencode lands.
- **desk-standard** (`~/Developer/desk-standard`) — the **executive-desk governor**, becoming a core part of the toolset. Multi-target already (claude-plugin + opencode), ships `plugin/` + `desk-pm` + the deskkit/librarian Go binary (embedded PocketBase) + schema v1. Heading to 1.0.0 (desk decision 0021). **Deliberately NOT yet distributed from dotfiles-agents** — under rapid dev; Henry wants to avoid churn in both repos.
- ~~**dev-tooling-desk** (`~/Documents/EXECUTIVE_DESK/Projects/dev-tooling-desk`)~~ — now
  archived at `~/Documents/EXECUTIVE_DESK/Projects/ARCHIVE/dev-tooling-desk-old` — the
  exec-desk instance: planning surface, `_knowledge/extenders.yaml` census, live `pb_data/`,
  decisions 0001–0021.

**Datamodel — two data natures (broadened 2026-07-20):** the exec desk's PM/KM spans well beyond GitHub issues (it *sets* release requirements that graduate to the GH board for the code desk; day-to-day PM/KM like "schedule a meeting with Tony" lives only on the desk). (1) **Derived census** (extenders/bundles/repos) — regenerable from `extenders.yaml` schema v2 + `primitives-core.yaml` + `gh`; files stay truth, DB is a rebuildable cache. (2) **Authored PM/KM state** (non-code tasks, people, meetings, decisions, notes) — lives nowhere else, edited, workflow-bearing, needs a UI. The PM/KM half **settles the store on PocketBase** (already committed via deskkit 0009/0015 + the desk-pm work-graph + the 0021-F3 webapp in 1.0 scope). DuckDB is OUT; a derived SQLite is only a census inspector, never the PM/KM store. Unifying primitive = typed entity + typed relation (person/topic/decision/task/meeting/extender). **KB/PM frontend not yet built** — design open: PB Admin UI now; recommend Go+htmx embedded in the PB binary (ADR-0001 lean) for the PM app + Obsidian over the markdown desk for the KB half; React reserved if PM views get rich.

**Platform vision (Henry 2026-07-20):** the frontend is really one surface of a **toolkit that integrates AI agents against ONE unified data model + workflows** via many surfaces — a coding-agent harness assuming a desk persona (skills + MCP, or CLI), plus a built-in agent over CLI/REPL, TUI, and eventually a webapp. Designed in **rounds** (requirements → tech/borrow survey → data+workflow spec → prototypes → integrate). Obsidian deferred; prefer borrowing MIT-licensed projects. Draft: `~/Documents/EXECUTIVE_DESK/Projects/ARCHIVE/dev-tooling-desk-old/_meta/plans/desk-platform/plan.md`.

Macro-review plan of record: `~/Documents/EXECUTIVE_DESK/Projects/ARCHIVE/dev-tooling-desk-old/_meta/plans/extenders-estate/system-cohesion-and-datamodel.md`. Extends desk decision 0021-F7 (cohesion+value eval) from desk-standard-internal to the whole estate. Related: [[reference-skills-system]].
