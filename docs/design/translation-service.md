---
title: "Translation service — uncommitted design deltas (Cowork hook-less subset + trigger policy)"
type: technical-design
status: active
created: 2026-07-02
updated: 2026-07-05
summary: The two translation-service design decisions that are NOT yet reflected in code/config — the Cowork (hook-less harness) subset model and the PR-merge-vs-release trigger policy. Everything else in the original TDD is already committed (CHARTER portability table, primitives-core-translation-config.yaml, scripts/translate.py).
migrated_from: hsb-2026 vault 1_Engineering/technical-designs/translation-service-architecture.md (2026-07-05)
---

# Translation service — uncommitted design deltas

_The as-built translation service (type x target matrix, skip-and-record, results-record schema, two
marketplace catalogs, determinism) is already committed: `docs/CHARTER.md` portability table,
`primitives-core-translation-config.yaml`, `scripts/translate.py`, ADR 0003. This note captures only
the design that had **no committed home** so it isn't lost when the source TDD is archived._

## 1. Cowork (hook-less harness) subset — a fourth harness through three outputs

Claude Cowork is a fourth consumption harness but has **no hook support** — so a primitive set that
includes hooks must ship a hook-less subset for it. Two options were weighed:

- **(a) A fourth output dir** `targets/claude-code-cowork/` — rejected: breaks the "three outputs"
  invariant and duplicates most content.
- **(b) A generated exclusion manifest honored at deploy (recommended)** — keeps "three outputs"
  true and puts the variance where variance already lives (deploy time). The build emits a manifest
  listing hook primitives to exclude for Cowork; the deploy step honors it.

Plus **bundle-level degradation:** a plugin that contains hooks ships a **hook-less subset of
itself** for Cowork rather than being dropped whole. The roster `requires:` field (already shipped,
issues #79/#81) is the input for this subsetting, but `translate.py` does **not** consume it for
Cowork subsetting yet — that is the unbuilt work.

## 2. Trigger policy (Q-05) — PR-merge, with releases layered on top

When does translation regenerate `targets/`? The options: on every PR-merge (freshest, matches the
drift guard) vs on a release cycle (pinnable for consumers). Trade-off across consistency,
consumer-view, clone-at-build cost.

**Recommendation:** keep **PR-merge as the mechanism** (it is what the `make build-check` drift guard
already enforces), and **layer releases on top as tagged snapshots** when a consumer needs pinning —
not either/or. (ADR 0004's translation config work and issue #36's clone-at-build both assume the
PR-merge baseline; a future release-tagging layer is additive.)

## Related

- Clone-at-build edge cases (null-upstream skip-vs-remove, hash-mismatch loud-fail, separate network
  CI lane) are captured on issue #36.
- The rules/memory translation policy is [ADR 0004](../decisions/0004-rules-and-memory-translation-policy.md).
- opencode hook support is settled CC-only in the config and [ADR 0002](../decisions/0002-hooks-as-script-plus-config.md); opencode parity rework is #59.
