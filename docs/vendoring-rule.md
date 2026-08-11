# The vendoring rule — when third-party content may live in-tree

_Governance rule. Provenance: backlog decision-6 (externals materialization =
pinned-vendored-copy) + owner ruling 2026-08-04. This rule defines the **minimum bar** that
gates the `origin: vendored` provenance class; the [ADR 0015](decisions/0015-self-authored-primitives-only.md)
amendment and `scripts/check_provenance.py` enforcement are built under backlog task-10 and
cite this document._

## The default: do not vendor

`primitives-core/` is self-authored (ADR 0015). Third-party content is normally **not copied
in** — it is either recorded by reference in [`../externals.yaml`](../externals.yaml) (upstream
+ pinned SHA) and installed from upstream, or re-authored as an original first-party primitive.
Vendoring — committing a verbatim third-party body into the tree — is a **narrow exception**,
never a default. It re-hosts someone else's bytes, which is exactly what ADR 0015 was written to
prevent; the exception exists only where composition genuinely requires the base in-tree.

## The minimum bar (all four must hold)

A body may be vendored only if a human can answer **yes to all four**:

1. **Composition, not convenience.** We build on top of, wrap, or bundle the third-party body —
   we do not merely want to redistribute it. (If we only want to ship it as-is, that fails —
   see *Excluded* below.)
2. **In-tree is necessary.** The composition cannot work through reference-only /
   install-from-upstream — the base bytes must be present in the tree for our layer or bundle to
   function or ship coherently.
3. **Pinnable + attributable.** The upstream is a real repo with an immutable commit SHA to pin
   against, a license that permits vendoring, and a clear attribution target. A branch name, a
   missing license, or an unresolvable upstream fails the bar.
4. **Contract-ready.** The entry will carry the full `origin: vendored` contract (below). If it
   can't, it isn't vendored.

Anything that fails the bar is **not** vendored: it is reference-only in `externals.yaml`,
re-authored as first-party, or dropped.

## Sanctioned scenarios

Two composition shapes are known to clear the bar (owner-ruled 2026-08-04). They are examples,
not an exhaustive list — a new shape must still pass all four criteria above.

1. **Modification of an external** — we compose our own layer on top of a third-party body and
   need that base in-tree for the layer to build on. _Example:_ `pptx-themes` = the Anthropic
   `pptx` base (`skills/pptx` @ `anthropics/skills`) vendored under
   `primitives-core/skills/pptx-themes/base/`, with our palette / motif / design-judgment layer
   authored on top. The theme layer is meaningless without the base mechanics, and cannot reach
   them by reference at author time.
2. **Bundle of homegrown + external** — a plugin or bundle that must ship first-party and
   third-party pieces together as one coherent, self-contained unit, where splitting the
   third-party piece out to install-from-upstream would break the bundle's promise of working
   on install.

## Excluded: re-hostable upstreams

If a third-party extender is installable directly from its upstream and we only want to
**catalog or redistribute** it — with no composition on top — it does **not** get vendored. It
is **reference-only** (`externals.yaml`, install-from-upstream). This is why decision-6 dropped
the four plugin externals (`frontend-design`, `code-simplifier`, `typescript-lsp`,
`skill-creator`): all install straight from `anthropics/claude-plugins-official`, and we compose
nothing on top of them, so re-hosting them would be pure passthrough — the anti-pattern ADR 0015
forbids.

## The `origin: vendored` contract

Every vendored body must carry, at minimum:

- **`origin: vendored`** in its roster entry (distinct from `authored` and `sourced`), with
  non-null `upstream` + an immutable `ref` (commit SHA, never a branch or tag).
- **`LICENSE`** (or `LICENSE.txt`) from the upstream, present in the vendored dir.
- **Attribution** in the entry's README naming the upstream repo + pinned ref — never split from
  or dropped off the vendored content.
- Subjection to the **drift checker** (task-10): `up_to_date | behind | diverged | not_found`
  against the pinned ref; `diverged` (upstream rewrote history at the ref, or our copy was
  hand-edited outside the compose layer) is a loud failure.

A vendored entry whose upstream later disappears is not deleted — it is reclassified
`disposition: orphaned` and reviewed under task-11 (vendored-skill quality).

## Relationship to other rules

- **ADR 0015** (self-authored-only) is amended by task-10 to permit `origin: vendored` under
  this bar; `origin: sourced` bodies under `primitives-core/` remain forbidden. This rule is the
  criteria that amendment enforces.
- **decision-6** is the ruling that created the `vendored` class and this bar.
- **task-11** owns the quality gate + feedback-channel layer that sits on top of any vendored
  (or distributed) skill.
