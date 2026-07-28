## What

Institute quality controls for the vendored/distributed skill supply chain this repo manages:

1. **Registry coverage** — every vendored skill actually in use is registered in
   `externals.yaml` with upstream + immutable ref (per its own schema). Motivating gap: the
   PocketBase skill vendored into `hsb3/learn-pocketbase` (`.claude/plugins/pocketbase/`,
   commit `ae6d8f6`) has NO recorded upstream, no pin, and no entry here.
2. **Quality checks** — a gate (accuracy spot-check / eval-harness pass) that vendored and
   distributed skill content must clear before it ships to targets, so factual claims in
   references are verified against the tool version they describe.
3. **Feedback channel** — every distributed skill/plugin carries a standard pointer for
   reporting inaccuracies (e.g. a "found an error? file it at hsb3/dotfiles-agents" line in
   SKILL.md or the plugin README), so findings in consuming repos flow back upstream instead
   of dying as local edits.

## Why

A vendored skill shipped a **false factual claim that survived into live use**: the PocketBase
skill's `references/file-handling.md` asserts protected-file tokens are "single-use
(invalidated after first successful use)". Disproven live on PocketBase v0.39.9 — the same
token fetched a protected file twice, 200 both times (learn-pocketbase docs/15 erratum;
tracked as hsb3/learn-pocketbase#56, fixed locally there). Because the skill has no provenance
entry and no feedback channel, the correction stays stranded in the consuming repo — nothing
routes it upstream or to other consumers.

## Done when

- [ ] `externals.yaml` (or successor registry) covers every vendored skill in active use,
      including the PocketBase skill, with upstream + pinned ref (or an explicit
      "no-upstream / locally authored" disposition).
- [ ] A documented quality-check step exists for distributed skill content (what is checked,
      when it runs, what blocks distribution).
- [ ] All distributed skills/plugins carry the standard feedback-channel pointer.
- [ ] The PocketBase single-use-token inaccuracy is recorded as the motivating case, and the
      corrected text is what any future distribution of that skill carries.

## Context

- Consuming-repo record: hsb3/learn-pocketbase#56 (docs/15 erratum — file tokens REUSABLE
  ~2 min on v0.39.9).
- Vendoring commit with no provenance: learn-pocketbase `ae6d8f6` (2026-07-25).
- Repo rule this collides with: provenance manifests required for every vendored external
  artifact (project-protocol).
