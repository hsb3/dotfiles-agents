# Build the translation service — deferred adapters (CMA + mcp render)

_Residual of #6 after the Phase 3 MVP (#17) shipped skills/agents/CC-marketplace + the drift guard.
This plans only the two configured-but-unimplemented capability cells: the Claude managed-agents
(CMA) renderer and the mcp renderer. The CMA half (A) is unblocked; the mcp half (B) is blocked on a
first mcp primitive existing._

Status: draft
Date: 2026-06-29

## Tracking

Issue #6 (Phase 3 milestone; labels `type:feat`, `phase:3-translation`, `gate:cross-tool`,
`area:cli`). Origin: the MVP deferral recorded in `scripts/translate.py:10` and the technical-plan
§2.1 "MVP (resist over-building)" note. **Contract impact:** the CMA adapter must conform to the
pinned CMA contract in `CANON.md` ("Resolved — managed-agents (CMA) contract") — a source-of-truth
doc; deviations get amended there in the same change. No DB / typed-API / migration surface.

## The problem (grounded in source)

What EXISTS today:
- `scripts/translate.py` builds three targets (`TARGETS` at `:34`); claude-code and opencode render
  fully; **claude-agents is a deferred-skip loop** at `scripts/translate.py:290-301` — it iterates
  every primitive whose `targets` includes `claude-agents` and records
  `{"capability":"render","reason":"claude-agents (CMA) adapter deferred (post-MVP)","skipped":true}`.
- Confirmed in the lock: `primitives-core-translation-results.json` → `results."claude-agents"` has
  71 entries, all `"skipped": true` (e.g. `agent-dot-md-authoring`). `targets/claude-agents/` holds
  only `.gitkeep`.
- The capability cells are configured: `primitives-core-translation-config.yaml:43` (`skill` ->
  `claude-agents` = render, adapter `cma_skill_upload`), `:48` (`agent` -> `claude-agents` = render,
  `cma_agent_create`), `:50-53` (the three `mcp` render cells). None of these adapter names exist in
  `translate.py`.
- The CMA contract is already pinned (no research needed): `CANON.md` records `POST /v1/skills`
  (multipart `files[]`, all files in one dir, `SKILL.md` at root, name/desc extracted) and
  `POST /v1/agents` (`BetaManagedAgentsCreateAgentParams`: `name`+`model` required; `system`,
  `tools[]` <=128, `mcp_servers[]` <=20 remote-only, `skills[]` <=20 refs, `metadata`, `multiagent`).

What's MISSING:
- The CMA renderer (A). Real inputs exist: 53 skills + 18 agents list `claude-agents` in their roster
  `targets`.
- The mcp renderer (B). **No inputs exist** — `primitives-core/mcp/` is empty (only `.gitkeep`) and
  `grep 'type: mcp' primitives-core.yaml` returns zero. B cannot be exercised or drift-guarded until
  a first mcp primitive lands; building it now would be untested speculation.

## Deliverables

### A — CMA adapter (unblocked)
Replace the deferred-skip block (`scripts/translate.py:290-301`) with real rendering into
`targets/claude-agents/`:
- **A1 — agent payloads.** For each agent targeting claude-agents: emit
  `targets/claude-agents/agents/<id>.json` = `BetaManagedAgentsCreateAgentParams` (`name` = id,
  `model` = TBD per Q2, `system` = agent body sans frontmatter, `tools` = [] unless the source
  declares any, `skills` = [], `metadata` = {}). Deterministic JSON (`sort_keys`, no clocks).
- **A2 — skill build-sheets.** For each skill targeting claude-agents: emit
  `targets/claude-agents/skills/<id>/` (the upload set, `SKILL.md` at root — a copy) **plus**
  `targets/claude-agents/skills/<id>.upload.json` describing the `POST /v1/skills` multipart (file
  list, `display_title`). Skill folder copy reuses the existing `copy_into` helper.
- **A3 — results + guard.** `rec(...)` the new destinations with `sha256` (the platform-stable
  `sha256_path` from the hash fix); they flip from `skipped:true` to `skipped:false`. The existing
  `--check`/`make build-check` already diff every `targets/<t>` subdir, so the guard covers
  claude-agents with no change; just regenerate the lock.
  - **File scope:** `scripts/translate.py` (the claude-agents block only) + regenerated
    `targets/claude-agents/**` + `primitives-core-translation-results.json`.
  - **Acceptance:** `targets/claude-agents/` non-empty; every claude-agents result has
    `skipped:false` + `destination` + `sha256`; each `agents/<id>.json` loads and has `name`+`model`;
    `make build` twice is byte-identical; `make ci` green.

### B — mcp render adapter (blocked on a first mcp primitive)
Implement `mcp_to_claude` / `mcp_to_opencode` / `mcp_to_cma` reading the neutral
`primitives-core/mcp/<name>.json` spec → each target's own mcp schema (CC `.mcp.json`/settings
`mcpServers`; opencode `opencode.json` `"mcp"` `type: local|remote`; CMA `mcp_servers[]` remote-only).
- **File scope:** `scripts/translate.py` (new mcp branches in each target section).
- **Acceptance:** with a `type: mcp` primitive in the roster, `make build` renders it to all three
  targets and `make ci` stays green — **deferred until that primitive exists** (see Q3).

## Gate & contract hygiene

| Gate | Fires? | Why |
| ---- | ------ | --- |
| `make ci` (roster + targets) | YES | always on PR; this changes generated output |
| Targets drift guard (`make build-check`) | YES | A regenerates `targets/claude-agents/` + the lock; must commit them in the same PR |
| Roster drift (`make check`) | NO for A | A adds no primitives. YES for B only if an mcp primitive is added |
| `yamllint` / `actionlint` | ONLY IF | the config or `.github/workflows/` is edited (A may touch neither) |
| CMA contract in `CANON.md` | KEEP IN SYNC | amend the pinned note if the adapter shape deviates |
| DB / infra / API-codegen | NO | none in this repo |

## Parallelism + landing order

| Unit | Parallel with | Serializes on | Order |
| ---- | ------------- | ------------- | ----- |
| A1 agent payloads | A2 | `scripts/translate.py` claude-agents block (shared file, one owner for A) | 1 |
| A2 skill build-sheets | A1 | same file as A1 | 1 (same owner) |
| A3 results/guard | (none) | follows A1+A2 (lock regenerated last) | 2 |
| B mcp render | independent file regions | a first mcp primitive must exist first | deferred |

A1+A2 touch the **same function** in `translate.py` (the claude-agents section) — one owner, not
parallel writers. B is a disjoint code region but gated on an input that doesn't exist, so it lands
separately. Recommend: **A as one PR closing #6's CMA half; B as a tracked follow-up.**

## Open questions / owner decisions

1. **Static payloads vs live upload?** Recommend **static** — the adapter emits committed,
   drift-guarded `targets/claude-agents/` artifacts; actually POSTing to the API is a deploy concern
   (dotfiles-bootstrap), consistent with how CC/opencode targets are placed, not called. (Default: static.)
2. **CMA agent `model` field.** `BetaManagedAgentsCreateAgentParams` requires `model`. CC agents carry
   a tier alias (`sonnet`/`opus`) the opencode transform currently drops. Options: (a) omit and set a
   single default model in the payload, (b) map tier -> a pinned model id. Recommend **(a) a configurable
   default** (e.g. `anthropic/claude-sonnet-4-5`) in the config, to avoid brittle per-agent version pins. (Default: a.)
3. **Build B now or defer?** No mcp primitive exists. Recommend **defer B to a follow-up issue**
   ("render the first mcp primitive") and close #6 on A — building an untestable renderer is
   speculation the drift guard can't protect. (Default: defer B.)
4. **Scope of `tools`/`skills` in agent payloads.** CC agents rarely declare tool allowlists; the
   migrated agents don't. Recommend emitting `tools: []`, `skills: []` for now (the agent's behavior
   is in `system`), and revisit when an agent needs a tool/skill binding. (Default: empty arrays.)
