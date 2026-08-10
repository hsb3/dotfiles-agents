---
id: TASK-059
title: >-
  check_solo_skills has no rule for hook dependencies, so a reword can make a
  hook-dependent skill solo-eligible
status: To Do
assignee: []
created_date: '2026-08-10 05:30'
labels:
  - gates
milestone: m-1
dependencies: []
priority: medium
type: bug
ordinal: 38000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The membership gate derives which skills are standalone-capable, and a skill that depends on a plugin hook at runtime is not — it will load in `solo-skills` and silently do nothing useful, because the hooks it needs ship in a different plugin.

Found while shipping the `activation` skill (TASK-058). That skill depends on atelier five hooks: its `check` subcommand importlib-loads them by relative path, and its whole subject is the file those hooks read. The gate correctly excludes it — but only incidentally, because its prose happens to contain the literal string `skills/delegation`, which trips the sibling-path rule. **Reword that one sentence and the skill flips to solo-eligible while its runtime dependency is unchanged.**

So the gate reads a proxy, not the property. Sibling-path and sibling-id mentions are evidence of coupling, not the definition of it, and a skill can be coupled to a plugin through code paths the prose never names.

This matters because the membership gate is derived, not recorded — that is the design, and it is the right one. A derived gate reading the wrong signal is worse than a recorded list, because it looks trustworthy while being wrong.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A skill whose shipped code resolves paths into a sibling primitive directory is excluded from solo-skills regardless of what its prose says
- [ ] #2 The `activation` skill stays excluded when the literal `skills/delegation` is removed from its body
- [ ] #3 A test covers a skill that is coupled only through code, with no coupling visible in its prose
- [ ] #4 The rule distinguishes evidence of coupling from the definition of it, so a future skill cannot pass by wording alone
<!-- AC:END -->
