---
id: TASK-042
title: >-
  claude-code-expertise: trim surfaces.md to selection-relevant content and add
  mutual boundary clauses
status: To Do
assignee: []
created_date: '2026-08-07 00:51'
updated_date: '2026-08-10 02:25'
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
Follow-up from the TASK-040 spike: claude-code-expertise and claude-code-config stay separate, but ~88 of surfaces.md's 152 lines (hooks, MCP, settings/permissions sections) restate what claude-code-config covers in more depth — the cause of three already-fixed defects. The overlap is one-directional: config restates nothing of expertise's, so only expertise needs to shrink.

expertise's job is helping someone choose a surface, not authoring one. Drop the hook events list, the settings.json hook-wiring example, the hook I/O contract, the hook-directory rationale, the .mcp.json example, and the settings.json permissions example. Keep the trigger-model one-liners and the "MCP adds capability, a hook gates it" boundary line.

Neither skill's description discloses the other's territory today, so a query like "how do hooks work?" routes to expertise's shallower copy instead of config's. Add a mutual boundary clause to both.

Constraint: expertise's own rules (references/authoring.md:63, references/distribution.md:81-83) forbid a standalone-eligible skill from referencing a sibling by path or wikilink. Any pointer to claude-code-config must name it in prose only.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 surfaces.md sections 2, 4, and 5 keep only selection-relevant content; authoring/contract detail owned by claude-code-config is removed, not reworded
- [ ] #2 No factual claim about hooks, MCP, or settings in surfaces.md contradicts or shallowly duplicates claude-code-config's version
- [ ] #3 Both skills' description frontmatter carries a mutual boundary clause so a matcher can tell which one owns a given prompt
- [ ] #4 The prose pointer to claude-code-config names it without a path or wikilink, per authoring.md:63 and distribution.md:81-83
- [ ] #5 `make ci` is green
<!-- AC:END -->
