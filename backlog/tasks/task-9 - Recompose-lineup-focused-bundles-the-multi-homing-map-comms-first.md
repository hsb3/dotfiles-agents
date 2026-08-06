---
id: TASK-9
title: 'Recompose lineup: focused bundles + the multi-homing map (comms first)'
status: Done
assignee: []
created_date: '2026-08-04 00:42'
updated_date: '2026-08-04 02:55'
labels:
  - refactor
  - decision
milestone: m-0
dependencies:
  - TASK-2
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/221'
priority: medium
type: feature
ordinal: 600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Migrated from GH #221. Under the symlink architecture a standalone is a directory + marketplace entry, so the mechanism is free; what remains is the ruling: which skills dual-home (comms first), bundle-composition principle as ADR extension, code-desk audit dispositions. Convention touchpoints (output dirs, handoff location) parameterized per-project — ties into task-15.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Bundle-composition principle ratified
- [x] #2 comms installable without code-desk
- [x] #3 Disposition recorded per code-desk skill
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Owner 2026-08-04: comms-first direction approved IN PRINCIPLE, but gated on a design pass — session drafts the ADR-0017 bundle-composition extension + per-code-desk-skill dispositions for owner ratify BEFORE any build. Ruling not yet final (AC#1 pending the ratified ADR).

**2026-08-06 — partially built; AC#2 is NOT met and needs a re-ruling.**

Design pass (`_meta/plans/task-9-lineup/design-pass.md`) was drafted, ratified via
`_meta/signoff/2026-08-06-m0-rulings/` (items B/C/D all approved), and built: 3 new standalone
plugins (mise-en-place-scaffold, readme-value-and-proof, repo-meta-structure) + pptx-themes
already standalone = 4 dual-homing skills; lineup 15 → 18. AC#1 and AC#3 satisfied.

**The discrepancy:** the design pass recommended `comms` STAY bundle-only, and the owner
approved that table — but this directly contradicts AC#2 and the task's own "comms first"
framing from the 2026-08-04 in-principle ruling. The session authored that recommendation
without flagging that it reversed the owner's prior direction, and the sign-off form did not
surface the conflict, so the approval cannot be read as a deliberate reversal.

The stated rationale ("too coupled to the desk ecosystem") is also weak: `comms` composes
against `pptx-themes`, which is now itself standalone-installable, and its `requires:
[local-mcp]` is unchanged by which assembly ships it. Nothing mechanical blocks a `comms`
standalone.

**Resolved same day.** Owner re-ruled: split comms standalone, as originally directed. Built
— `plugins/comms/` + marketplace entry + a `primitives-core/skills/comms/README.md` symlinked
into the assembly. AC#2 now genuinely met. Grounding that the first pass skipped: comms'
`local-mcp` requirement is the deck-builder MCP (external to every bundle), and its declared
siblings are `pptx-themes` (standalone) and `handoff` (foreman-kit, never in code-desk) — so
bundle membership never satisfied its dependencies. Correction trail in the design pass.

**Final shape:** 5 dual-homing skills (comms, mise-en-place-scaffold, pptx-themes,
readme-value-and-proof, repo-meta-structure); 5 bundle-only (repo-compliance-audit,
project-memory, dev-focus, planning-desk, board-triage). Lineup 15 → 19 plugins; marketplace
0.3.0 → 0.4.0.
<!-- SECTION:NOTES:END -->
