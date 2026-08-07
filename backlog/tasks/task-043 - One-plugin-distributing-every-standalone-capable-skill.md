---
id: TASK-043
title: One plugin distributing every standalone-capable skill
status: To Do
assignee: []
created_date: '2026-08-07 01:10'
labels:
  - assembly
milestone: m-1
dependencies: []
priority: medium
type: feature
ordinal: 22000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Owner instruction 2026-08-07, verbatim: 'create a plugin that distributes all skills that can stand on their own.'

Today the marketplace ships most standalone-eligible skills as their own one-skill plugin — the large majority of current entries are that shape. This asks for a single plugin that carries all of them instead of, or in addition to, that pattern.

BLOCKED ON A CLARIFICATION BEFORE ANY BUILD. The instruction arrived alongside a ruling that the lab-setup skill (TASK-29) should ship standalone, and the two readings imply very different work:

Reading A, additive — the existing one-skill plugins stay exactly as they are, and this new plugin is an aggregate convenience install for someone who wants everything without picking. Cost: every standalone skill is then dual-homed, so a consumer installing both the aggregate and an individual plugin needs the dual-homing behavior to hold (one primitives-core source symlinked into two assemblies loads the skill once).

Reading B, replacing — the aggregate becomes the distribution shape and the per-skill plugins are retired. Cost: a breaking marketplace change removing many entries, dangling every existing install record, with no alias or redirect mechanism in this marketplace's shape.

A is cheap and reversible. B is a marketplace restructure and, under AGENTS.md, a major information-architecture change needing the owner's approval before it is built. Settle the reading first.

Also to determine once the reading is fixed: what 'can stand on their own' means mechanically. check_symlinks now encodes a standalone rule (exactly one skill, no agents, no hooks), but that describes an ASSEMBLY, not a skill's self-sufficiency. A skill that references a sibling by path is not standalone-capable regardless of how it is packaged — claude-code-expertise's own authoring rules state exactly this. The membership test needs to be that property, not the current packaging.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The owner has ruled between the additive and replacing readings, and the ruling is recorded before any file changes
- [ ] #2 'Standalone-capable' is defined as a checkable property of the skill (no sibling-skill references by path or wikilink), not as a description of its current packaging
- [ ] #3 A gate enforces that every skill in the new plugin meets that property, so membership cannot silently drift
- [ ] #4 If the additive reading wins, dual-homing is verified: installing both the aggregate and an individual plugin loads the skill once
- [ ] #5 make ci is green and the catalog guard's counts and names match the new lineup
<!-- AC:END -->
