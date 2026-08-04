---
id: decision-6
title: 'Externals materialization: pinned-vendored-copy, not clone-at-install'
date: '2026-08-04 03:28'
status: accepted
---
## Context

task-10 (from GH #36) was scoped to build "clone-at-**build**" for the third-party externals
in `externals.yaml`. ADR 0017 removed the build step and tracked `dist/` entirely, leaving only
two live options — clone-at-**install** or **pinned-vendored-copy**. The owner's task-10
sign-off note pointed at vendoring ("might just be simpler to keep a pinned, vendored copy in
the repo"). A decisions memo weighed both, canonicalised the scattered "decisions 1–7," and
found a working vendored precedent already in-tree (`pptx-themes/base/` — a verbatim,
LICENSE-carrying copy of the Anthropic pptx skill that escapes ADR 0015 only via a roster-entry
loophole). Full analysis: `_meta/plans/externals-clone-vs-vendor/memo.md`. Owner ruled
2026-08-03.

## Decision

**Materialization = pinned-vendored-copy.** Supersedes the clone-at-build design of GH #36 /
ADR 0003. The seven decisions resolve as:

- **D1 (strategy):** vendored-copy, not clone-at-install.
- **D2 (network/CI lane):** dissolves — no install-time network; offline CI lanes unchanged.
- **D3 (ref-pin):** immutable commit SHA only; never a branch or tag.
- **D4 (integrity):** a maintenance drift checker using the `up_to_date | behind | diverged |
  not_found` model; **diverged = loud failure**, behind = informational.
- **D5 (null-upstream):** require-or-**reclassify** (an upstream-less entry becomes
  `origin: vendored, disposition: orphaned` or is re-authored as first-party) — never
  require-or-remove.
- **D6 (drop policy):** dissolves — we hold the bytes, so a vanished upstream never breaks an
  install; it only downgrades the entry to `orphaned` for a task-11 review.
- **D7 (provenance placement):** add a first-class **`origin: vendored`** class (upstream + pin
  + `LICENSE` + attribution); **amend ADR 0015** from "never copied in" to "copied in only as an
  `origin: vendored` entry meeting the contract; `origin: sourced` under `primitives-core/`
  stays forbidden." `check_provenance.py` grows a vendored arm enforced at file granularity
  (closes the pptx-base loophole). Quality gate + feedback channel remain task-11's charter.

**Additional owner rulings (2026-08-03):**

- **Drop the 4 plugin externals** — `frontend-design`, `code-simplifier`, `typescript-lsp`,
  `skill-creator` are installable directly from `anthropics/claude-plugins-official`; we do not
  re-host them. Only `pptx` stays (we compose `pptx-themes` on top of it). Re-hostable upstreams
  are reference-only / install-from-upstream, not vendored.
- **Vendoring needs a minimum bar** — it is a narrow exception, not a default. Two sanctioned
  scenarios: (1) *modification* of an external (compose a layer on the third-party base, as
  pptx-themes does), (2) a *bundle of homegrown + external* shipping as one unit. The rule is
  drafted under **task-26** and cited by the ADR 0015 amendment.

## Consequences

- **task-10 build scope** (gated on task-26): amend ADR 0015 + record the vendored model (new
  ADR or supersede ADR 0003); drop the 4 plugin entries from `externals.yaml`; reclassify
  `pptx-themes/base` (and the pptx entry) as `origin: vendored` with LICENSE + attribution;
  add the `check_provenance.py` vendored arm; add an optional `make externals-drift` checker
  (adapt functionform-asmbl's sync model).
- **task-26** (new): draft the vendoring rule / minimum bar + the two sanctioned scenarios.
- **task-11** unchanged in charter (quality + feedback), now sitting on a sanctioned vendored
  substrate rather than a loophole.
- ADR 0003's clone-at-build assumption and #36's original mechanism scope are retired.
- The principle ADR 0015 protects (clean, attributed, non-silent provenance) is preserved; only
  the mechanism widens from reference-only to vendor-with-record.
