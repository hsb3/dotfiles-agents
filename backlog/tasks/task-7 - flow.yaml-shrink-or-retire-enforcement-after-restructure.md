---
id: TASK-7
title: 'flow.yaml: shrink or retire enforcement after restructure'
status: Done
assignee: []
created_date: '2026-08-04 00:42'
updated_date: '2026-08-04 02:19'
labels:
  - refactor
milestone: m-0
dependencies:
  - TASK-3
priority: low
type: chore
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Post-restructure the DAG is ~8 nodes. Decide whether check_flow.py enforcement stays or flow.yaml demotes to documentation; regenerate docs/FLOW.md either way.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 flow.yaml + FLOW.md reflect the post-restructure graph
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Ruled with the restructure: check_flow.py enforcement STAYS. Rationale: it caught real drift twice during the ADR 0017 execution (unclaimed top-level path when plugins/ landed; FLOW.md doc drift at each node change), and the graph shrinks again automatically when task-6 extracts evals/harness. flow.yaml + FLOW.md were regenerated at every step of tasks 2-4 and reflect the post-restructure graph (16 nodes, 10 edges).
<!-- SECTION:NOTES:END -->
