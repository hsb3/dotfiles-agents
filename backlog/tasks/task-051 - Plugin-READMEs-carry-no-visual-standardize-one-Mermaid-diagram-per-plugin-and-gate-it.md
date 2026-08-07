---
id: TASK-051
title: >-
  Plugin READMEs carry no visual: standardize one Mermaid diagram per plugin and
  gate it
status: Done
assignee: []
created_date: '2026-08-07 14:41'
updated_date: '2026-08-07 14:54'
labels:
  - distribution
milestone: m-1
dependencies: []
priority: medium
type: feature
ordinal: 30000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Every plugin README is prose plus a 'What you get' table. A table names the pieces one at a time; it cannot show what makes each piece fire, in what order, or what comes out — so a reader deciding whether to install has to assemble the relationships themselves.

Adopt one standard for plugin-README visuals and backfill all six. Format is inline Mermaid, not a rendered asset: ADR 0017 forbids tracked generated artifacts, and a committed SVG rendered from a .mmd source is exactly that. Mermaid also renders natively on GitHub, which is the surface these READMEs are read on, and diffs like code so a stale diagram surfaces in review.

The governing content rule is 'draw the trigger and the flow, never the inventory' — if the arrows can be deleted without loss, the diagram is the table redrawn.

Ship the convention with a gate rather than as prose someone remembers. The load-bearing check is the ghost-primitive one: a renamed or retired primitive leaving a stale node in a picture nobody re-read is the foreman->atelier class of bug, and nothing currently catches it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 backlog/docs/readme-diagram-standard.md states the format, the canonical placement slot, the content rule, and the constraints
- [x] #2 .github/CONTRIBUTING.md points at that standard from the human-facing loop
- [x] #3 scripts/check_plugin_diagrams.py exists, is stdlib-only and deterministic, and is wired into make check
- [x] #4 The gate fails when a plugin README has no mermaid fence
- [x] #5 The gate fails on a banned character in a node or edge label per the mermaid house rule
- [x] #6 The gate fails on a hardcoded fill colour that would go invisible on dark GitHub
- [x] #7 The gate fails when a fence exceeds the node ceiling
- [x] #8 The gate fails when a diagram node names a primitive that plugin does not ship, and a fixture proves that check can go red
- [x] #9 All six plugin READMEs carry a diagram in the canonical slot
- [x] #10 Every diagram is proved by a real mermaid-cli render, not by reading it
- [x] #11 Each of the six plugins is version-bumped in both plugin.json and marketplace.json
- [x] #12 make ci exits 0
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Shipped in PR #288, squash-merged into dev as 9e41442; branch deleted.

WHAT LANDED
- backlog/docs/readme-diagram-standard.md — format (inline Mermaid, never a rendered asset: ADR 0017 forbids tracked generated artifacts), canonical slot (## How it fits together, before the section enumerating the pieces), the content rule (draw the trigger and the flow, never the inventory), and the constraints.
- .github/CONTRIBUTING.md — a Plugin READMEs section pointing at it, plus the make check table row.
- scripts/check_plugin_diagrams.py — six checks, wired into make check so it rides an existing CI job name (job names are pinned by branch protection).
- tests/test_check_plugin_diagrams.py — 25 tests; every check has a fixture that makes it go red.
- Six diagrams: atelier/code-desk/plugin-feedback as lifecycles, diagrams/obsidian-toolkit as routers, solo-skills draws its membership rule (30 boxes would only be the table redrawn).
- Six version bumps in both manifests.

MEASURED, NOT ASSUMED (2026-08-07, mermaid-cli)
mermaid-cli EXITS 0 WHEN THE RENDER FAILS. A '(' in a node label and 'load --> end' each produced no output file at all while the process reported success. Checking $? tells you everything is fine. Assert on the output file instead. This is recorded in the standard and is the reason the gate is static rather than render-based (make ci is stdlib-only, zero-install).
Second finding: '&' in a label renders fine today, though the house rule bans it. The rule is deliberately wider than one renderer's present tolerance so GitHub, IDE previews, and mermaid-cli all agree — kept as-is, and the gate's docstring says so rather than implying every banned character breaks.
Third: 'load --> end' is a hard parse failure, so a reserved-word-as-bare-node-id check was added beyond the planned five. Detected by adjacency to an arrow, so a legitimate 'end' closing a subgraph is untouched.

VERIFICATION
- make ci exit 0; 438 tests (413 before, +25 here).
- python3 scripts/check_version_bump.py clean (run by hand — it is CI-only, needs network for origin/main).
- All six diagrams rendered through mermaid-cli with the output file asserted non-empty, and every node and edge label confirmed present in the resulting SVG. The atelier diagram was additionally rendered to PNG and read back visually.
- CI green on #288 (both required checks).

DESIGN NOTE
The ghost-primitive check derives each plugin's membership from the assembly on disk (same basis as check_catalog._assembly_counts and check_solo_skills._members), never from a recorded list — per the standing 'derive a set, never consume a recorded one' rule.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Adopted one standard for plugin-README visuals and backfilled all six: inline Mermaid under a '## How it fits together' heading, governed by 'draw the trigger and the flow, never the inventory'. Shipped with scripts/check_plugin_diagrams.py (in make check) so the convention cannot drift — its load-bearing check derives plugin membership from disk and fails when a diagram names a primitive that plugin does not ship, the foreman->atelier class of bug no other gate catches. Verified: make ci exit 0 with 438 tests, 25 of them new with a red-path fixture per check; every diagram proved by a real mermaid-cli render with the output file asserted and all labels confirmed in the SVG; CI green on #288. Found and recorded along the way: mermaid-cli exits 0 when a render fails, so the exit code cannot be trusted.
<!-- SECTION:FINAL_SUMMARY:END -->
