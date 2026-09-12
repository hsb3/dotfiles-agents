---
title: "Marketplace lineup recomposition — exec-desk folded into code-desk"
id: decision-029
type: decision
status: Accepted
created: 2026-07-22
summary: exec-desk retires as a bundle (its skills fold into code-desk); opencode-expertise and private-fork become standalone-only; memory-taxonomy merges into project-memory; update-config renames to claude-code-config; tech-eval-research is added — 15 named plugins total.
---

# Decision 029 · Marketplace lineup recomposition — exec-desk folded into code-desk

_Retires the exec-desk bundle into code-desk and reshapes the standalone catalog, landing the
marketplace at one desk bundle, three kits, and eleven standalone skills._

- **Provenance:** decided during the estate-restructure rebuild (branch
  `feat/estate-restructure`), 2026-07-22. This ADR is the durable record for a decision that
  was already in flight as an inline shorthand ("ruling 0020") in `primitives-core.yaml`'s
  roster header and `plugins.yaml`'s header comment before this file existed.
- **Raised by:** estate-restructure rebuild plan (marketplace lineup recomposition slice).

## Context

The marketplace had grown two desk bundles — `code-desk` (next-release execution +
repo-standards hygiene) and `exec-desk` (executive-desk overhead: planning-desk, comms,
board-triage, pptx-themes). Running two desk bundles side by side added install-time and
maintenance overhead without a clear line between them in practice — most consumers install
both together, and the boundary between "engineering desk" and "executive desk" work didn't
hold up as primitives moved. Separately:

- `opencode-expertise` and `private-fork` were shipping inside `code-desk` as well as
  standalone, but neither is core to day-to-day desk work — they're opt-in tools, better
  reached only via their standalone plugin.
- Two adjacent memory skills — `memory-taxonomy` (the taxonomy reference) and `project-memory`
  (opt-in/migrate mechanics) — had grown enough overlap that maintaining them as two skills was
  pure friction; a consumer wanting one nearly always wants the other.
- `update-config` had a name that undersold its scope; it is, in practice, THE Claude Code
  configuration skill, not one config update among several.
- A gap: no standalone skill existed for technology/tooling evaluation research, a
  recurring need surfaced during the rebuild.

## Decision

Fold `exec-desk` into `code-desk` and reshape the standalone catalog in the same pass:

1. **exec-desk retired as a bundle.** `planning-desk`, `comms`, `board-triage`, and
   `pptx-themes` move into `code-desk`. `code-desk` becomes the sole desk bundle in the
   marketplace.
2. **`opencode-expertise` and `private-fork` become standalone-only** (`plugins: []` in the
   roster) — removed from `code-desk`'s membership.
3. **`memory-taxonomy` merges into `project-memory`.** One skill now carries both the taxonomy
   reference and the opt-in/migrate mechanics; `memory-taxonomy` no longer exists as a
   separate entry.
4. **`update-config` renamed to `claude-code-config`**, reframed as THE Claude Code
   configuration skill (not one config skill among several).
5. **`tech-eval-research` added** as a new standalone one-skill plugin (`origin: authored`).
6. **`project-memory` and `pptx-themes` ship in both `code-desk` and standalone** — they are
   frequently useful stand-alone but also belong in the desk bundle's default install.

Resulting counts: `code-desk` = 10 skills; standalone catalog = 11 skills; marketplace = 15
named plugins (1 bundle + 3 kits: `diagrams`, `foreman-kit`, `obsidian-toolkit` + 11
standalone: `claude-code-config`, `claude-code-expertise`, `dataviz`, `deep-research`,
`github-project-board`, `opencode-expertise`, `owner-signoff`, `pptx-themes`, `private-fork`,
`project-memory`, `tech-eval-research`).

## Consequences

- Consumers who previously installed `exec-desk` for planning-desk/comms/board-triage/
  pptx-themes now get them via `code-desk`, or standalone for `pptx-themes` alone.
- `opencode-expertise` and `private-fork` are no longer pulled in automatically by a
  `code-desk` install; consumers who relied on that must add the standalone plugin
  explicitly.
- Any reference to `memory-taxonomy` as a distinct skill (docs, roster entries, other ADRs)
  is stale as of this decision; `project-memory` is the sole successor.
- Any reference to `update-config` (roster id, plugin id, doc mentions) is stale; use
  `claude-code-config`.
- If a future need re-separates "executive desk" concerns from `code-desk`, that is a new
  decision superseding this one — this ADR does not rule out re-splitting, but the default
  going forward is one desk bundle.
- The inline "ruling 0020" shorthand previously carried in `primitives-core.yaml`'s roster
  header comment and `plugins.yaml`'s header comment now resolves to this ADR; there is no
  ADR numbered 0020 — that number was never a real ADR file, only an inline placeholder used
  before this document existed.

## Affects

- `primitives-core.yaml` (the roster — membership changes for every moved/renamed/merged
  primitive)
- `plugins.yaml` (bundle/plugin metadata — exec-desk entry removed, code-desk description
  updated)
- `skill-catalog.yaml` (standalone catalog — additions, removals, and the rename)
- `bundles/` (exec-desk bundle directory retired; code-desk bundle content grows)
- `primitives-core/skills/` (memory-taxonomy content merged into project-memory;
  update-config directory renamed to claude-code-config; tech-eval-research added)
- `scripts/gen_marketplace.py` (no logic change expected, but the generated
  `.claude-plugin/marketplace.json` and `PLUGINS.md` reflect the new lineup)
- `README.md` (marketplace lineup description)
- `tests/test_gen_marketplace.py` (membership, build-list, and PLUGINS.md kind assertions
  retargeted to the new lineup)
