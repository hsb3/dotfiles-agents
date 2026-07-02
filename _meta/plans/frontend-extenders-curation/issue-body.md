> **Tracking:** #48, from Henry's 2026-07-02 notes (`_meta/NOTE.md`). Inventory every "frontend" skill/agent/plugin across the roster and the workbench, and produce a curation plan down to a deliberate core set.

## Problem

The frontend surface has accumulated too many overlapping drafts, with no single view of what exists or which items are meant to survive. Today it spans at least two repos and nine bundles:

- **Roster** (`primitives-core.yaml`): `carbon-builder` (line 62), `obsidian-chat-ui` (line 403), `react-doctor` (line 513), `shadcn` (line 563, also a pending sourced-origin flip under #31).
- **Workbench** (`REGISTRY.md`): `carbon-webapp-team` (line 11, has commands/ to fold), `design-system-toolkit` (line 15, client-token blocker), `frontend-quality-guard` (line 17, client-token blocker), `style-canon` (line 25, client-token blocker), `webapp-designer` (line 27, parked — 8 skills + 6 agents + 3 MCP, "decompose on promotion").

Henry's directive (2026-07-02): "inventory all the frontend skills/agents/plugins and make a plan to curate to a core set. there are way too many drafts." No issue currently owns this; the workbench rows each carry individual blockers but nothing looks at the set as a whole, so overlap (e.g. carbon-builder vs carbon-webapp-team, shadcn vs webapp-designer internals, design-system-toolkit vs style-canon) is invisible.

## Deliverables

- A — **Inventory**: one document (suggested: `_meta/plans/frontend-extenders-curation/plan.md`, or a workbench `docs/` note if the gate process prefers it there) listing EVERY frontend skill/agent/plugin across `primitives-core.yaml`, workbench `REGISTRY.md`, and any live-config stragglers (`~/.claude/skills`, plugin caches), each with type, home, status, and what it actually covers.
- B — **Overlap map**: which items duplicate or subsume each other (the two carbon bundles; shadcn vs webapp-designer's internals; design-system-toolkit vs style-canon).
- C — **Curation plan**: the named target core set, plus a disposition for every other item (keep / merge-into / demote / retire), each with a one-line rationale. Executions become follow-on issues; this issue delivers the plan only.

## Acceptance criteria

- [ ] Every frontend item in `primitives-core.yaml` and workbench `REGISTRY.md` appears exactly once in the inventory with a disposition — grep of the inventory against both manifests finds no frontend item missing.
- [ ] The plan names the core set explicitly and every non-core item has a stated disposition and rationale.
- [ ] Follow-on issues are filed (or explicitly declared unnecessary) for each merge/demote/retire disposition.

## Dependencies & gates

- Soft dependency on #31 (Q-13 batch triage) — dispositions written there inform, but do not block, the inventory.
- No repo gates fire for this issue itself (report-only; no `primitives-core/` or `targets/` edits). Roster drift guard (`make check`) and targets drift guard (`make build-check`) fire on the follow-on execution issues.

## Out of scope

- Executing any merge/retire/demote — follow-on issues.
- Non-frontend curation (the general Q-13 pass is #31).
