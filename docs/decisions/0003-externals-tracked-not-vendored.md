---
title: "Externals are tracked-and-cloned, never vendored"
type: decision
status: Accepted (amended by decision-6)
created: 2026-06-28
updated: 2026-07-03
summary: Third-party extenders are references (upstream + pinned ref) cloned at build; never copied into primitives-core.
---

> **Amendment note (2026-09-09):** Decision-6 later permits narrowly qualified pinned vendoring; see [the current rule](../vendoring-rule.md). The absolute ban below describes the original decision.


# 0003 · Externals are tracked-and-cloned, never vendored

_Third-party extenders are references (upstream + pinned ref) cloned at build time —
`primitives-core/` holds homegrown source only._

- **Provenance:** ratified in CANON 11 (2026-06-28); extended by CANON 16 for mcp
  (2026-06-29); ADR backfilled 2026-07-03 per #40
- **Raised by:** strategy-desk CANON decision 11; vault decision
  `third-party-extenders-clone-from-source`

## Context

Third-party skills/plugins copied into the source tree drift silently from their upstreams
and blur the provenance line the whole system depends on (`origin: authored` vs `sourced`).
Distribution here is private and self-only, so redistribution/licensing is a non-issue —
the real risk is drift.

## Decision

External extenders are **never copied into `primitives-core/`**. `externals.yaml` records
each one's upstream repo + pinned ref; the build **clones them into `targets/` at
distribution time**. Two refinements hold:

- **mcp is spec, not code** (CANON 16): a connection spec is config — self-authored specs
  live in `primitives-core/mcp/`, third-party specs at `externals/mcp/<id>.json` tracked by
  `externals.yaml kind: mcp`.
- **In-roster sourced items** (copies that pre-date this rule, kept in core by the T-15
  ruling) carry `origin: sourced` + non-null `upstream`/`ref` — guard-enforced
  (`check_roster.py`), so their provenance is explicit even though the content lives in-tree.

## Consequences

- The clone-at-build step for `kind: skill|plugin` externals is the roster's last unbuilt
  capability (#36); ~30 tracked externals await upstream research + ref pinning.
- The workbench gate routes thin wrappers of public extenders to `externals.yaml` (J2),
  never into `primitives-core/`.
- Moving refs are blockers: a branch name pins nothing (gate provenance rule).

## Affects

`externals.yaml` · `scripts/translate.py` (externals parsing; #36 clone step) ·
`primitives-core.yaml` sourced entries · workbench `docs/promotion-gate.md` (J2 /
sourced-candidate provenance).
