---
id: TASK-051
title: >-
  Plugin READMEs carry no visual: standardize one Mermaid diagram per plugin and
  gate it
status: In Progress
assignee: []
created_date: '2026-08-07 14:41'
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
- [ ] #1 backlog/docs/readme-diagram-standard.md states the format, the canonical placement slot, the content rule, and the constraints
- [ ] #2 .github/CONTRIBUTING.md points at that standard from the human-facing loop
- [ ] #3 scripts/check_plugin_diagrams.py exists, is stdlib-only and deterministic, and is wired into make check
- [ ] #4 The gate fails when a plugin README has no mermaid fence
- [ ] #5 The gate fails on a banned character in a node or edge label per the mermaid house rule
- [ ] #6 The gate fails on a hardcoded fill colour that would go invisible on dark GitHub
- [ ] #7 The gate fails when a fence exceeds the node ceiling
- [ ] #8 The gate fails when a diagram node names a primitive that plugin does not ship, and a fixture proves that check can go red
- [ ] #9 All six plugin READMEs carry a diagram in the canonical slot
- [ ] #10 Every diagram is proved by a real mermaid-cli render, not by reading it
- [ ] #11 Each of the six plugins is version-bumped in both plugin.json and marketplace.json
- [ ] #12 make ci exits 0
<!-- AC:END -->
