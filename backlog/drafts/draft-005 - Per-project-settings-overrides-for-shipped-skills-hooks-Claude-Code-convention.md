---
id: DRAFT-005
title: >-
  Per-project settings overrides for shipped skills/hooks (Claude Code
  convention)
status: Draft
assignee: []
created_date: '2026-08-06 15:01'
updated_date: '2026-08-06 21:31'
labels:
  - primitives
  - decision
dependencies:
  - TASK-15
type: feature
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Owner ask (2026-08-06): add the settings override files for the skills, hooks etc. Claude Code has a convention for that; it can be used to override the `_meta/` locations.

Shipped primitives hard-code conventions that consuming repos may not share, most visibly `_meta/` paths (this repo itself no longer has `_meta/` after decision-8). Claude Code already provides a convention layer: `.claude/settings.json` / `settings.local.json` (env vars, hook wiring) plus project-local config files. Precedent already shipped: the context-watermark hook reads CONTEXT_WATERMARK_SOFT/HARD env vars with shell-default expansion in hooks.json (2026-08-06), and foreman-kit reads `.claude/foreman-kit.local.md` for an effort override.

Scope: pick THE override convention per primitive type (env-via-settings for hooks; a documented project-local file for skills), then apply it to the known hard-coded `_meta/` locations: the handoff file location (generalizes task-15), the comms skill `_meta/briefings/` output dir, and the owner-signoff `_meta/signoff/` batch dir.

Related: task-15 (per-project handoff-file override) is the special case this generalizes; absorb it or state its residual scope explicitly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The override convention is documented once: where overrides live, precedence order, and one worked example per primitive type (hook and skill)
- [ ] #2 The three named `_meta/` assumptions are overridable (handoff file location, comms `_meta/briefings/` output dir, owner-signoff `_meta/signoff/` batch dir) and each affected README Configuration section documents the override
- [ ] #3 The context-watermark env-var pattern is recorded as the ratified override mechanism for hooks
- [ ] #4 task-15 is either absorbed into this work or explicitly linked with its residual scope stated
<!-- AC:END -->
