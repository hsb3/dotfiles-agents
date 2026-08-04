---
id: TASK-26
title: >-
  Draft the vendoring rule: minimum bar + sanctioned scenarios for vendoring an
  external
status: To Do
assignee: []
created_date: '2026-08-04 03:28'
updated_date: '2026-08-04 03:28'
labels:
  - externals
  - decision
milestone: m-0
dependencies: []
priority: high
ordinal: 650
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Author the rule that governs when third-party content may be vendored into this repo (as origin: vendored, per decision-6). Vendoring re-hosts other people's bytes — the narrow exception ADR 0015 is being amended to permit — so it must clear a minimum bar rather than be a default. Define that bar and the sanctioned scenarios; the rule then feeds the ADR 0015 amendment built under task-10.

Owner-named sanctioned scenarios to encode (2026-08-03):
1. MODIFICATION of an external — we compose a layer on top of a third-party body and need the base in-tree (e.g. pptx-themes = the Anthropic pptx base + our theme/design layer).
2. BUNDLE of homegrown + external — a plugin/bundle that must ship first-party and third-party together as one coherent unit.

The bar should make 'just re-host an upstream we could install directly' fail it (that is reference-only / install-from-upstream, not vendoring — cf. the 4 plugin externals dropped in decision-6).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Minimum-bar criteria for vendoring are written and testable-by-a-human
- [ ] #2 Both sanctioned scenarios (modification-of-external; homegrown+external bundle) are recorded with the pptx-themes example
- [ ] #3 Rule explicitly excludes re-hostable upstreams (reference-only, not vendored)
- [ ] #4 Rule is referenced by the ADR 0015 amendment (task-10)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Draft the minimum-bar criteria + the two sanctioned scenarios as a short rule doc (candidate home: docs/ or a primitives-core/README section).
2. Reconcile with ADR 0015's amended text and the new origin: vendored class (decision-6 / task-10).
3. Land the rule so task-10's ADR amendment can cite it.
<!-- SECTION:PLAN:END -->
