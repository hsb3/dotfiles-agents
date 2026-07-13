---
title: "chore: decide the vendored-third-party boundary + per-item disposition for the 22 sourced primitives"
type: proposed-issue
status: draft
created: 2026-07-12
purpose: Staged issue for the owner directive (2026-07-12) to address the skills in primitives-core written by others - the audit found the labels truthful but the storage policy undefined.
notes: Awaiting owner approval to file. Grounded in a full 65-item provenance audit (this session); counts re-verified against primitives-core.yaml by grep, not taken from the audit agent on faith.
---

> **Tracking:** #TBD, owner directive 2026-07-12 ("there are a lot of skills in primitives-core/skills
> written by not me that we need to address - audit all items"). A full-roster provenance audit ran
> the same day; this issue carries its remediation.

## What the audit found (2026-07-12, all 65 items)

- **The roster labels are truthful.** All 22 `origin: sourced` items carry a real upstream + pinned
  ref (the guard works); spot-checked authored items are genuinely in-house (they reference this
  repo's own conventions and workflows). No mislabeled vendor-doc dumps found.
- **But 22 of 65 primitives are third-party content stored INSIDE `primitives-core/`:** the
  10 langchain-stack skills (langchain-ai), 4 openspec skills (Fission-AI), 3 deep-agents skills
  (langchain-ai), framework-selection (langchain-ai), shadcn (shadcn-ui), skill-creator (anthropics),
  find-skills (vercel-labs), devcontainer-setup (trailofbits).
- **Four plugins are 100% third-party content** (langchain-stack, openspec, deep-agents, meta);
  frontend-extras is half (shadcn).
- **The governing rule is undefined at charter level.** `CLAUDE.md` says "externals are tracked,
  not vendored: third-party extenders live in externals.yaml; the build clones them" - but
  `docs/CHARTER.md` (which wins) is silent on the sourced-vs-external boundary, and current
  practice (the #81 re-triage) flips origins to sourced rather than moving items out. Two rules
  in tension, neither ratified.

## Deliverables

- **A - the boundary decision, as an ADR** (`docs/decisions/`): when does third-party content
  live in `primitives-core/` as `origin: sourced` (an adopted, locally-maintained fork we
  deliberately diverge) vs in `externals.yaml` (tracked upstream, cloned at build - the #36
  capability) vs not at all. Charter gets a one-line pointer.
- **B - per-item disposition for all 22 sourced items** applying the ADR: adopt-as-fork
  (divergence rationale recorded) | move to externals (depends on #36) | retire to the salvage
  pile. Recorded on the roster (coordinate the mechanism with #39).
- **C - upstream-drift cadence:** pinned refs go stale silently; define the recurring upstream
  review step (the private-fork skill's upstream-review cycle is the SOP model) for whatever
  stays vendored.

## Acceptance criteria

- [ ] The ADR exists, is Accepted, and CLAUDE.md/CHARTER language agrees with it (no more
      tracked-not-vendored vs sourced-in-core contradiction).
- [ ] All 22 sourced items have a recorded disposition; `make ci` and the sourced-entry guard
      stay green through any moves.
- [ ] Items moved to externals render identically from `externals.yaml` (`make build` drift
      guard proves it) or are explicitly retired with their plugin membership updated.
- [ ] The upstream-review cadence is written where the curation loop will actually hit it
      (workbench lifecycle docs or the roster README), not a flat note.

## Dependencies & gates

- Depends on: #36 (clone-at-build externals) for any move-to-externals disposition; coordinates
  with #39 (roster provenance field) and the sibling plugin business-case retrofit proposal
  (whether langchain-stack / openspec / deep-agents / meta earn distribution at all is ITS
  question; this issue owns where their content lives).
- Gates: `make ci` (roster guard, validate, build drift); ADR discipline per project protocol.

## Open owner decisions

1. **The boundary itself** - recommended default: `sourced` in primitives-core ONLY for items we
   intentionally maintain/diverge; everything tracked-verbatim moves to externals.yaml once #36
   lands (until then, status quo with the ADR stating the intent).
2. **Whether "written by not me" also targets the agent-generated authored items** - the 18
   agents and several authored skills were largely produced by Claude sessions; if the concern
   covers those too, the business-case retrofit (sibling proposal) is the vehicle that judges
   them, item by item, against real use.
