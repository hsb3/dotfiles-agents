---
id: TASK-17
title: 'Port 3 ideas from the parked assembly app (github-sync, schema, vars)'
status: Done
assignee: []
created_date: '2026-08-04 00:43'
updated_date: '2026-08-07 00:51'
labels:
  - assembly
milestone: m-1
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/193'
priority: low
type: feature
ordinal: 1700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Migrated from GH #193. Item 1 (github-sync) already routed into the externals mechanism (task-10). Standing PARK ruling on functionform-asmbl itself is decision record d-3.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Each idea gets a disposition: ported, folded into an existing task, or dropped
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Dispositions recorded 2026-08-07 against the source capture issue (GH #193, now closed), which named all three ideas and their gating conditions.

IDEA 1 — GitHub-sourcing + sync_status (the issue's 'highest value'): SUPERSEDED IN PART, RESIDUAL STILL OPEN. The issue routed this to #36 as 'when building #36, adapt that code'. The externals mechanism landed via TASK-10 (Done) and externals.yaml now carries researched entries with immutable SHA pins. But the freshness half did NOT land: externals.yaml's own header states the clone-at-build step under a byte-diff drift guard 'is separate work (DEV-34 / GitHub #36)', and a grep for sync_status/freshness/stale across externals.yaml and scripts/check_provenance.py returns nothing. So the pin exists, the staleness detection does not — a pinned ref never reports that upstream moved. Residual belongs with the externals-freshness work, not here.

IDEA 2 — ordered assembly/composition schema (position, transform, condition, version_pin, parent_assembly_id): DROPPED, condition not met. The issue gated it on 'if bundles ever need ordered / parameterized / version-pinned composition (today they are flat id lists)'. ADR 0017 moved further AWAY from that shape, not toward it: plugin membership is no longer a list at all — it IS the symlink assembly on disk, and the roster explicitly carries no membership field. An ordered-composition schema has no host to attach to.

IDEA 3 — build-time {{placeholder}} parameterization + per-primitive design_spec rationale: DROPPED, condition not met. Gated on 'if/when a bundle needs per-target parameterization'. Nothing generated is tracked (ADR 0017); the one install-time generator, gen_opencode.py, is required to be deterministic with no parameterization surface. Rationale continues to live in ADRs, which is where the issue said it lives today.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
All three ported ideas dispositioned against GH #193's own gating conditions, so nothing is lost when the parked source app is next touched. Idea 1 (github-sync/sync_status) is partly superseded by TASK-10's externals mechanism, with the freshness/drift-detection half confirmed still unbuilt and belonging to the externals-freshness work rather than to this card. Ideas 2 and 3 are dropped: both were explicitly conditional on bundles needing ordered or parameterized composition, and ADR 0017 moved the architecture away from that shape — membership is the symlink assembly on disk, and no tracked generated artifact exists to parameterize. Verified against externals.yaml's header, a grep for freshness markers, and the ADR 0017 rules in AGENTS.md.
<!-- SECTION:FINAL_SUMMARY:END -->
