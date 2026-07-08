---
title: "Rules stay Claude-Code-only; auto-memory translates lossily to opencode"
type: decision
status: Accepted
created: 2026-07-02
updated: 2026-07-05
summary: Rules are gated out of opencode bundles by default; auto-memory ships lossily (files + AGENTS.md reference).
---

# 0004 · Rules stay Claude-Code-only; auto-memory translates lossily to opencode

_Rules and auto-memory fail differently when translated to opencode, so they get per-primitive
policies, not one blanket rule._

- **Provenance:** decided 2026-07-02; migrated from the strategy vault to a repo ADR 2026-07-05
- **Raised by:** Q-03 (opencode has no path-scoped rules and no lazy-pull memory); evidence in the
  workbench `opencode-expertise` skill's CC→OC mapping

## Context

opencode has no path-scoped rules (only always-on `instructions` globs) and no lazy-pull memory. The
two primitives fail differently when translated, so a single blanket policy would be wrong for one of
them. Options weighed: (A) translate both lossily — but a path-scoped rule forced always-on fires
outside its scope, worse than no rule; (B) gate both CC-only — safe but discards memory portability,
the whole point of the memory standard; (C) split by failure mode — chosen.

## Decision

- **Rules: Claude-Code-only by default.** The roster `requires:` capability flags gate them out of
  opencode bundles (same mechanism as hooks — see [ADR 0002](0002-hooks-as-script-plus-config.md) and
  the distribution capability matrix). A per-rule opt-in exists for rules genuinely safe as always-on
  instructions.
- **Auto-memory: translate lossily.** Ship the memory files + an `AGENTS.md` reference; lazy-pull
  economics are lost, but the worst case is extra context, never wrong behavior.

## Consequences

- opencode sessions run rule-poorer than Claude-Code sessions — an honest asymmetry, not degraded
  parity claimed as parity.
- The translation config gains a per-rule opt-in flag; bundle generation subsets rules out for
  opencode as it does hooks.
- Closes Q-03.

## Affects

`primitives-core-translation-config.yaml` (per-rule opt-in flag) · `scripts/translate.py` (rule
subsetting for opencode) · the roster `requires:` schema · opencode target bundles. The opt-in flag's
exact name/location in the roster schema is engineering detail for the roster work, not fixed here.
