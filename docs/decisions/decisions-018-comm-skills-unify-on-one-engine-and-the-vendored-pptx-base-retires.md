---
id: "decision-018"
title: comm skills unify on one engine and the vendored pptx base retires
date: '2026-08-26'
status: accepted
---
## Context

A three-angle design pass (minimal-delta, clean-room, consumer-first) found `comms`,
`pptx-themes`, and `owner-signoff` re-implementing one workflow — structured input, style and
tone config, package, check, refine, present — three times over. Five questions went to the owner
via a sign-off form. Ruled on kata card `0jqa`; filed here 2026-09-07, having lived only in that
card until then.

The options weighed were: one skill (engine plus deliverable types, themes, and voice profiles,
with section-map specs validated against declarative type definitions, doctrine as an
all-errors-at-once lint, and the sign-off form as both a deliverable type and the approval loop)
versus keeping three separate skills; build-beside-then-retire-per-type versus a single big-bang
cutover; deleting the verbatim-vendored `pptx-themes/base/` versus keeping it; building a pptx
auto-renderer now versus deferring it; and deleting a stale `pptx-themes/evals/evals.json` that
asserted an abandoned theme and font configuration.

The card's original text cited a Kaneo task as the analysis that started this. That reference
does not resolve — the task closed before the 2026-09-02 cutover and was never imported. Recorded
here rather than silently dropped.

## Decision

Owner-signoff form, answered 2026-08-26, all five items ratified as written.

1. **One skill: engine plus types, themes, and voices.** Specs are YAML/JSON section maps; legacy
   `slides.json` arrays stay valid via a shim. The owner directed a descriptive name, and the
   session named it `comm-kit`, extending the existing "comm package" vocabulary.
2. **Build beside, retire per type.** Increment 1 = engine, presenter, and the morning-briefing
   type, proven by re-rendering a real briefing; increment 2 = remaining types plus the form
   presenter; consolidation only after demonstrated parity, in one batched version-bump wave.
3. **Delete the vendored `pptx-themes/base/`.** Verified unreachable from the authored layer;
   deleting it removes the proprietary-license obligation and the network drift gate along with
   the files. Re-vendor at a newer pin later if a real need appears.
4. **Defer the pptx auto-renderer.** When built: HTML/tsx/jsx first, then convert to
   PowerPoint/PDF, for the lighter dependency footprint. Go/no-go test — a new deliverable type
   must cost one config file and zero engine changes before any pptx presenter is built.
5. **Delete `pptx-themes/evals/evals.json`.**

This partially reverses decision-6 (externals materialization as a pinned vendored copy) for this
one entry: the copy goes, the reference-not-vendor law of ADR 0015 is what remains.

## Consequences

- The roster loses its `origin: vendored` entry once `base/` is deleted, so
  `scripts/check_vendored_drift.py`'s pptx entry and the matching `externals.yaml` record need
  removal in the same wave.
- `comms`, `owner-signoff`, and `pptx-themes` were meant to retire as separate skills at the
  consolidation phase, merging their triggers into one description.
- A `comm-kit`-shaped plugin was to become the first "job-sized plugin", feeding the open
  distribution question about what plugin granularity this marketplace ships. That framing is
  moot now that the engine folded into `comms`, but the distribution question is still open and
  still needs an answer.
- The voice contradiction and the placement of the narrative doctrine are resolved by
  construction (voice profiles; one composition doc) — not verifiable until consolidation lands.
- No membership-gate contract changes anywhere.

Execution status, checked 2026-09-06 on `0jqa`. The ruling is settled and undisputed; execution
has diverged in one respect and is incomplete in two others.

- **Naming diverged.** Increment 1 did not create a standalone `comm-kit` skill; the engine
  (`deliver.py`, `types/`, `themes/`, `voices/`) was merged directly into the existing `comms`
  skill, and `primitives-core/skills/comm-kit/` does not exist. The fold commit gives the reason:
  comm-kit's engine was a strict superset of comms' old `render_deck.py` and already accepted the
  bare `slides.json` shape.
- **Items 3 and 5 are ratified but not executed.** `primitives-core/skills/pptx-themes/base/`
  still ships and is still `origin: vendored` in the roster; `pptx-themes/evals/evals.json` still
  exists. Carried on card `g3nq`.
- **Item 2's consolidation phase is unstarted.** `owner-signoff` and `pptx-themes` both still ship
  standalone, and `comms/README.md` still routes external-audience decks to the standalone
  `pptx-themes` toolchain rather than a folded-in presenter. Carried on `g3nq` and `jy78`.
