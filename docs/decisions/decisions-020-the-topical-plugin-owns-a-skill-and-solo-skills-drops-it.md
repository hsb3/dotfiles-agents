---
id: "decision-020"
title: The topical plugin owns a skill and solo-skills drops it
date: '2026-09-08'
status: accepted
---
**Amended 2026-09-08:** PR #509 placed task-authoring in mise-en-place; PR #515
swept the remaining 18 dual-homed solo-skills memberships. The per-skill rollout and
open-decision wording below describes the original ruling, not the later completed sweep.
Decision-024 separately establishes board-desk as task-authoring's new topical home.

**Implementation note 2026-09-10:** Decision-024 makes board-desk the topical home
while retaining mise-en-place's task-authoring membership for its planning-desk dependency.
The shared source is unchanged; enabling both plugins can list the skill twice.

## Context

A consuming project reported (2026-08-29, GitHub issue #442) that enabling both `pocketbase`
and `solo-skills` listed each PocketBase skill **twice** in the session's skill list.

Nothing was duplicated on disk. Under ADR 0017 there is exactly one source per skill in
`primitives-core/skills/`, and a plugin assembly is a symlink over it, so both plugins ship
the same bytes. What the consumer saw was two *memberships* of one source: the harness lists
what each enabled plugin declares, and neither plugin can suppress the other. `solo-skills`'
own README claimed the opposite — "installing both homes loads each skill once" — which is
the sentence the field report disproved.

`solo-skills` was built on the rule that it carries **every** standalone-capable skill, and
`scripts/check_solo_skills.py` enforced that in both directions: an ineligible skill inside it
is red, and an eligible skill outside it is red. That second direction is what made
dual-homing mandatory rather than incidental. Under it, a skill with a perfectly good topical
plugin had no way to stop being a `solo-skills` member without acquiring a fake dependency or
an exemption written for something else.

## Decision

Owner ruling (sign-off 2026-09-08, item D): **the topical plugin owns a skill, and
`solo-skills` is the home for skills with no topical plugin.**

Four skills lose their `solo-skills` membership under it:

| Skill | Topical plugin that keeps it |
|---|---|
| `pocketbase` | `pocketbase` |
| `pocketbase-best-practices` | `pocketbase` |
| `comms` | `code-desk` |
| `pull-request` | `code-desk` |

`scripts/check_solo_skills.py`'s second direction is amended to match: a standalone-capable
skill absent from `solo-skills` is red **only when no other plugin ships it**. "Has a topical
plugin" is **derived** from the symlink assemblies — any `plugins/<id>/skills/<skill>` where
`<id>` is not `solo-skills` — never from a hand-maintained list, so a skill gains or loses its
topical home the moment an assembly changes and there is no second inventory to forget.
`SYSTEM_EXEMPTIONS` keeps its existing, different meaning: a skill that prescribes an opt-in
system and must stay OUT of `solo-skills`. None of the four is added to it.

**The amendment is permissive, not prescriptive.** It *permits* a dual-homed skill to leave
`solo-skills`; it does not require it, and a dual-homed skill that stays is still green.
Whether the remaining dual-homed skills should also leave is an **open owner decision**, queued
separately — this ruling is executed per-skill on the four named above, not swept across the
roughly twenty skills dual-homed with `atelier`, `diagrams`, `obsidian-toolkit`, `carbon`,
`kaneo`, and `code-desk`.

## Consequences

- **This is a break for anyone who was getting those four skills from `solo-skills`.** The
  consumer-facing consequence is one sentence: enable the topical plugin to get the skill —
  `pocketbase` for the two PocketBase skills, `code-desk` for `comms` and `pull-request`.
  `solo-skills` takes a minor bump (0.14.0, shared with the same wave's other catalog change).
- **`solo-skills` no longer promises every standalone-capable skill.** Its plugin.json and
  marketplace descriptions, its README, and the root catalog all now say it is the home for
  skills with **no topical plugin**. The membership gate is still derived and still
  bidirectional; only the second direction's condition moved.
- **The disproved sentence is gone.** `solo-skills`' README no longer claims installing both
  homes loads a skill once; it says outright that both homes list the skill twice, because that
  is what the harness does.
- **`pocketbase` takes a patch bump** (0.2.1 → 0.2.2). Its assembly is unchanged, but the two
  skill READMEs it dereferences moved, so its published bytes did.
- **The removal is declared in the commit that makes it**, per `scripts/check_removals.py`. The
  four symlinks leave `plugins/solo-skills/skills/`; nothing leaves `primitives-core/`, so the
  roster is untouched and all four skills still ship.
- **One README outside this change's scope is knowingly stale**: `primitives-core/skills/comms/`
  is owned by another crew in the same wave and its install block still names `solo-skills` as a
  home. It is being corrected separately rather than edited across an ownership boundary.
