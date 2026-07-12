# chore: retire the frontend-extras plugin shell; keep its skills standalone

> **Draft — staged, not filed.** Follow-on from #48 curation-plan.md. Owner approves before filing.

## Problem

`frontend-extras` (plugins.yaml:20, v0.0.1, "shadcn/ui component patterns and React diagnostics")
bundles `react-doctor` + `shadcn`. It is **installed on no machine** (`~/.claude/plugins/cache/dotfiles-agents/`
holds only media-gen + project-workflow; not in `enabledPlugins`). Both bundled skills are
frontend-core in their own right (#48 core set), so the plugin shell adds membership overhead
with no live surface.

## Deliverables

- Remove the `frontend-extras` plugin entry from `plugins.yaml`.
- Drop `frontend-extras` from the `plugins:` list on `react-doctor` (primitives-core.yaml:569)
  and `shadcn` (primitives-core.yaml:623); both remain toggle-shelf skills reachable raw.
- Regenerate `targets/` via `make build` (never hand-edit).

## Acceptance

- [ ] `rg -c "frontend-extras" plugins.yaml primitives-core.yaml` → 0.
- [ ] `make build-check` passes (targets regenerated, no drift).
- [ ] react-doctor and shadcn still resolve as standalone skills across the three targets.

## Gates

- Roster drift guard (`make check`) — plugin membership change.
- Targets drift guard (`make build-check`) — plugins.yaml + primitives-core.yaml edit.

## Out of scope

- Renaming react-doctor / shadcn (that is the core-rename follow-on).
- Any change to the roster disposition of the two skills (they stay).
