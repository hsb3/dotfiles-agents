---
title: "primitives-core is self-authored only; externals by reference"
type: decision
status: Accepted (amended by decision-6)
created: 2026-07-22
summary: Every body under primitives-core/ is origin authored; third-party material is recorded by reference in externals.yaml, never vendored into the source tree.
---

> **Amendment note (2026-09-09):** Decision-6 and [the vendoring rule](../vendoring-rule.md) add the qualified `origin: vendored` exception enforced by `check_provenance.py`. The original self-authored-only rationale is preserved below.


# 0015 · primitives-core is self-authored only; externals by reference

_The source tree holds homegrown primitives only — third-party material is a reference
(`externals.yaml`), never a copy._

- **Provenance:** the composition principle ratified on the pre-rebuild desk (old-desk
  decisions 0005·0007); enforced from the clean-room rebuild by `scripts/check_provenance.py`.
  This ADR is the in-repo mirror of that old-desk decision, carried in verbatim-number form
  per the D7 mirror convention (see [`README.md`](README.md) — old-desk numbers are preserved,
  which is why the local sequence jumps from 0008 to 0015).
- **Raised by:** plugin-pipeline audit finding that the rule was enforced and cited across the
  tree (`primitives-core/README.md`, `check_provenance.py`, `externals.yaml`, `CLAUDE.md`) but
  had no on-disk record (#203).

## Context

The whole system depends on a clean provenance line: `origin: authored` (homegrown, edited
here) vs `origin: sourced` (third-party, tracked elsewhere). Copying a third-party skill,
agent, or hook body into `primitives-core/` erases that line — the copy drifts silently from
its upstream and becomes indistinguishable from authored work. This is the "wholesale
passthrough" the composition principle forbids: this marketplace composes its own primitives,
it does not re-host other people's.

[ADR 0003](0003-externals-tracked-not-vendored.md) settles *how* externals are recorded
(upstream + pinned ref, cloned at build). This decision settles the complementary
*placement* invariant: what is allowed to live under `primitives-core/` at all.

## Decision

**`primitives-core/` holds self-authored primitives, with a narrow vendoring exception.**
Every roster entry whose `source` lives under `primitives-core/` must be `origin: authored`
or `origin: vendored`. Third-party material is normally recorded by reference in
[`../../externals.yaml`](../../externals.yaml) (non-null `upstream` + `ref`) and never copied
into the source tree.

**Exception:** `origin: vendored` entries — third-party bodies committed into the tree with
full provenance record — are permitted only where a human can answer yes to all four criteria
in [`../vendoring-rule.md`](../vendoring-rule.md) (composition, in-tree necessity, pinnable +
attributable, contract-ready). This rule defines the minimum bar and two sanctioned scenarios.

`scripts/check_provenance.py` enforces this as a machine floor (`make provenance`, in
`make ci`): invariant (1) is the placement rule above (no `origin: sourced` under
primitives-core); invariant (2) is the externals-intent rule (every `externals.yaml` entry
carries `upstream` + `ref`); invariant (3) enforces the vendored contract (every `origin:
vendored` entry carries `LICENSE`, non-null upstream + immutable ref). The `origin: sourced
⇒ non-null upstream+ref` roster rule is enforced separately by `check_roster.py`.

## Consequences

- A third-party body may be vendored under `primitives-core/` only if it meets the four
  criteria in [`../vendoring-rule.md`](../vendoring-rule.md); otherwise it is referenced in
  `externals.yaml` instead. Promotion of an external into first-party status means
  **re-authoring** it as an original for the same job (`origin: authored`, no upstream), not
  copying the shipped body — see the eval promotions executed under #155–#157.
- The provenance check is a required PR gate; a `sourced` body under `primitives-core/`, or a
  `vendored` body missing its license/upstream/ref/attribution, fails `make ci`.
- Grandfathered in-roster `sourced` copies (pre-dating the rule) are an exception and
  carry explicit `origin: sourced` + `upstream`/`ref` — see
  [ADR 0003](0003-externals-tracked-not-vendored.md).

## Affects

`primitives-core/` (all bodies) · `primitives-core.yaml` (`origin` field) ·
`externals.yaml` · `scripts/check_provenance.py` · `scripts/check_roster.py` ·
`primitives-core/README.md` · `CLAUDE.md` · `evals/ingest.py` (promotion provenance).
