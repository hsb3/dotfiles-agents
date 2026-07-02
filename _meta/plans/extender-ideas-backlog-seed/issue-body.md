> **Tracking:** #49, from Henry's 2026-07-02 notes (`_meta/NOTE.md`, "ideas for future extenders"). Capture the idea list into the use-case-driven extender backlog so each is ranked or explicitly declined — none lost in a notes file.

## Problem

Eight future-extender ideas exist only in a personal notes file (`_meta/NOTE.md`, untracked). The ratified `use-case-driven-backlog` decision (vault, 2026-07-02) says extender investment is prioritized by named use cases, and vault task T-23 (wishlist to ranked backlog) is queued — but these ideas are not yet anywhere that process can see. Henry's annotation: "I likely have resources already for a lot of these," so each entry must carry its source-material pointers or the head start is lost.

The captured ideas:

1. **openspec expertise add-on** — do more with openspec-generated files; source material at `~/dotfiles/_docs/reference/openspec`. Builds on the four existing `openspec-*` roster skills (provenance pending under #31).
2. **claude-code expertise add-on** — no source pointer given.
3. **api-server-design enhancement** — roster skill exists (`primitives-core.yaml` line 32); fold in Henry's API-documentation notes from the ra-platform project.
4. **comms improvements** — roster skill exists; rename candidate, deck styling improvements, and additional presentation-preference material to roll in or pair.
5. **CMS data-mart trio** — `cms-bigquery-etl-generator` (evaluate: replace with Google's BigQuery skill + homegrown knowledge?), `cms-json-data-dictionary`, `cms-pdf-to-markdown` — all three already on the roster; needed for a CMS data mart Henry plans to build soon.
6. **dbt expert** (agent/skill) — nothing exists yet; needed for data marts.
7. **dlt-pipelines expert** (agent/skill) — roster has a `dlt-pipelines` skill (line 173); assess whether it covers "reliable pipelines for transferring data" or needs a build-out.
8. **diagrams consolidation** — several utilities/experiments/draft skills scattered across Henry's projects; roster has a `diagrams` skill.

## Deliverables

- A — Each idea lands as an entry in the extender wishlist/backlog (wherever T-23 establishes it; interim home acceptable if T-23 has not run), carrying: the driving use case, what already exists (roster/workbench/other repos), and the source-material pointers above.
- B — Ideas that duplicate existing roster coverage (3, 4, 5, 7, 8) are framed as enhancement entries against the existing primitive, not as new-extender entries.

## Acceptance criteria

- [ ] All eight ideas appear in the backlog/wishlist with use case + existing-asset pointers, or are explicitly declined with a one-line reason.
- [ ] Zero of the eight remain only in `_meta/NOTE.md`.
- [ ] Entries for ideas 1, 3, 4, 5 cite their named source material (openspec reference dir, ra-platform notes, presentation-preference material) concretely enough that a builder can find it cold.

## Dependencies & gates

- Interacts with vault T-23 (wishlist to ranked backlog standard) — if T-23 has not landed, seed an interim list and note it for T-23 to absorb; do not block on it.
- No repo gates fire (no `primitives-core/` or `targets/` edits; capture/planning only).

## Out of scope

- Building any of the extenders.
- Ranking beyond the standard triage rubric (Impact/Effort on the board).
