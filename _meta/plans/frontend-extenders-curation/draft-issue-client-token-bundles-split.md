# refactor: split the three client-token frontend bundles — capability out, tokens to client store

> **Draft — staged, not filed.** Follow-on from #48 curation-plan.md. Owner approves before filing.
> Applies ruling 48.4 + the wb#25 precedent (raptorxai-decks → presentation-designer split).

## Problem

Three workbench candidates fail the hard-check on client tokens: `design-system-toolkit`
(`raptorgpt`, SETTINGS_TEMPLATE.md:40-41), `frontend-quality-guard` (`raptorgpt`, TESTING.md:11/17/240/276/314/379/390),
`style-canon` (`functionform`, TESTING.md:11). **Contamination is doc-only** — the
skills/agents/commands carry no hardcoded client tokens; only the testing/settings docs do. So the
capability can be extracted client-agnostic, and the tokens route to the client memory store.

## Deliverables

- **design-system-toolkit**: fold `styling-system-patterns` into the new `frontend-design-tokens`
  core merge (#48 core #5); retire `storybook-best-practices` as a duplicate of webapp-designer's
  (overlap B row 7); strip SETTINGS_TEMPLATE.md client paths → client memory store.
- **frontend-quality-guard**: keep `frontend-architecture` + `eslint-v9-migration` as
  genericized candidates (client-agnostic); scrub TESTING.md client paths → client store.
- **style-canon**: fold `color-tokens` + `spacing-scale` + `motion-timing` into
  `frontend-design-tokens` (Carbon-scoped variants); retire `browser-diagnostics` as a duplicate
  of webapp-designer's browser skills (overlap B row 6); scrub TESTING.md → client store.
- Record each disposition in workbench `docs/promotions-log.md` (per the #31 precedent).

## Acceptance

- [ ] `rg -i "raptorgpt|raptorxai|functionform" incubator/{design-system-toolkit,frontend-quality-guard,style-canon}` → 0.
- [ ] Surviving skills carry no absolute `/Users/` machine paths.
- [ ] promotions-log.md records the split for all three bundles.
- [ ] Client tokens/paths relocated to the client memory store (not in any tracked extender).

## Gates

- Workbench-side: `docs/promotions-log.md` records (no da roster gate until a skill promotes).
- Roster/targets drift guards fire only on the eventual promotion of `frontend-design-tokens` to core.

## Out of scope

- Building the merged `frontend-design-tokens` skill itself (that is the design-tokens merge task,
  can be folded here or split — owner call).
- carbon-webapp-team's `commands/` fold (its own workbench blocker).
