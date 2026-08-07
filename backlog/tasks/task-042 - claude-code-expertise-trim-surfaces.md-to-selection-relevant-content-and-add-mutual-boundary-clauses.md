---
id: TASK-042
title: >-
  claude-code-expertise: trim surfaces.md to selection-relevant content and add
  mutual boundary clauses
status: To Do
assignee: []
created_date: '2026-08-07 00:51'
labels:
  - primitives
milestone: m-2
dependencies: []
priority: medium
type: chore
ordinal: 21000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Follow-up from the TASK-040 spike, which ruled the two plugins stay separate but found the duplication that caused three shipped defects. Those three are already fixed; this card removes the conditions that produced them.

The overlap is asymmetric and confined to one file: roughly 88 of the 152 lines in primitives-core/skills/claude-code-expertise/references/surfaces.md (sections 2 hooks, 4 MCP, 5 settings/permissions) restate material claude-code-config covers in more depth. claude-code-config restates nothing of expertise's. So the fix is one-directional: thin the expertise copy, leave config alone.

expertise's job is helping someone CHOOSE a surface. It needs the one line per surface that supports that choice, not the authoring contract for surfaces another skill owns. The spike named the specific passages to drop: the hook events list, the settings.json hook-wiring example, the hook I/O contract, the hook-directory rationale, the .mcp.json example, and the settings.json permissions example — keeping the trigger-model one-liners and the 'MCP adds capability, a hook gates it' boundary.

Second half: neither description disclaims the other's territory. claude-code-config has a 'What this skill does NOT do' section that never names expertise; expertise has a boundary line that disclaims the official builders but not config. A boundary that lives only in one body and in neither description cannot arbitrate which skill a matcher picks. The measured consequence: 'how do hooks work?' routes to expertise — the shallower copy — because expertise owns the explain verbs while config owns the action verbs.

CONSTRAINT that shapes the fix: expertise's own rules (references/authoring.md:63, references/distribution.md:81-83) forbid a standalone-eligible skill from referencing a sibling skill by path or wikilink, since the sibling may not be installed. Any pointer to claude-code-config must therefore name it in prose only. A link would break the standalone-eligibility rule the skill itself states.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 surfaces.md sections 2, 4, and 5 retain only selection-relevant content; the authoring/contract detail claude-code-config owns is removed, not reworded
- [ ] #2 No factual claim about hooks, MCP, or settings survives in surfaces.md that contradicts or shallowly duplicates claude-code-config's version
- [ ] #3 Both skills' description frontmatter carries a mutual boundary clause, so a matcher can tell which one owns a given prompt
- [ ] #4 The prose pointer to the sibling skill names it without a path or wikilink, per authoring.md:63 and distribution.md:81-83
- [ ] #5 make ci is green
<!-- AC:END -->
