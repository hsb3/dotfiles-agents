---
title: "chore: retrofit a business case for each of the 8 plugin distributions"
type: proposed-issue
status: draft
created: 2026-07-12
purpose: Staged issue for the owner directive (2026-07-12) to retrofit a stated-need/scope business case onto every existing plugin distribution, per the scope-first standing policy.
notes: Awaiting owner approval to file. On filing, update the Tracking line with the real issue number, create the plan folder + README row, and assign a milestone (proposed P1 - Lifecycle live).
---

> **Tracking:** #TBD, owner directive 2026-07-12 ("let's retrofit business case for each plug-in
> distribution"). Applies the scope-first standing policy (owner ruling 2026-07-12: creation and
> promotion always start from a stated-need/scope doc) retroactively to the 8 plugins that predate it.

## Problem

All 8 plugin distributions (`project-workflow`, `langchain-stack`, `openspec`,
`obsidian-plugin-dev`, `deep-agents`, `frontend-extras`, `meta`, `media-gen`) were assembled
before the scope-first policy existed. None has a written business case: no stated driving use
case, no evaluation against no-skill or a reputable off-the-shelf alternative, no overlap
statement. 62 of 65 roster items are `grandfathered-pending-use`, so plugin membership is
currently the only signal of intent - and it is not a judgable one. Without a case per plugin,
the next re-triage (the #81 precedent) has no basis to keep, trim, or retire a distribution.

## Deliverables

- **A - one business-case doc per plugin (8 docs).** Each carries the entry-form shared core
  (`primitives-core/skills/planning-desk/references/entry-forms-and-milestones.md`): driving use
  case (named project/workflow + how soon the need is real), what the plugin bundles (member ids
  from `primitives-core.yaml`), acceptance/evaluation criteria including the beats-no-skill /
  beats-off-the-shelf test, known overlaps, source pointers. Proposed home: `docs/plugins/<name>.md`
  (owner decision 1 below).
- **B - roster linkage.** Each plugin's case is discoverable from the roster/docs (mechanism to
  coordinate with #39, the roster provenance-field decision - do not invent a second free-text field).
- **C - dispositions for case-less plugins.** Any plugin that cannot produce a credible driving
  use case gets a retire-or-merge proposal instead of a padded case (the salvage-pile rule: material
  is claimed by use cases, never self-promoting).

## Acceptance criteria

- [ ] Each of the 8 plugins has a business-case doc carrying all five shared-core fields, or a
      filed retire/merge proposal in its place.
- [ ] Every case states its evaluation against no-skill and the best off-the-shelf alternative
      (naming the alternative, or stating none exists), per the scope-first ruling.
- [ ] Docs and roster cross-link both ways; `make ci` stays green (drift guards unaffected).
- [ ] The next board re-triage can cite a case (or a retire proposal) for every plugin - zero
      plugins with neither.

## Dependencies & gates

- Standing policy: scope-first extenders (owner ruling 2026-07-12, recorded in
  `_meta/plans/frontend-extenders-curation/scope.md`); CANON recording is an open owner TODO.
- Coordinates with: #39 (roster provenance/notes field - linkage mechanism), #36 (clone-at-build
  externals - sourced members may move), the sibling roster-authorship-audit proposal (its
  findings feed the per-plugin content honesty), and #48 (frontend-extras is likely superseded by
  the salvage-pile handling there - expect a retire/merge proposal, not a case).
- Gates: `make ci` (validate + drift lanes); docs land under the DOCS discipline (status headers).

## Open owner decisions

1. **Home for the case docs** - recommended default: `docs/plugins/<name>.md` (canonical,
   travels with the repo); alternative: one consolidated `docs/plugin-business-cases.md`.
2. **Single-skill plugins** (`meta`, `media-gen`) - full case each, or fold into their skill's
   own scope statement?
