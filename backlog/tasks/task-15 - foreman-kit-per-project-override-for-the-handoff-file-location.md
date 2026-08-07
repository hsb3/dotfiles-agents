---
id: TASK-15
title: 'foreman-kit: per-project override for the handoff-file location'
status: Done
assignee: []
created_date: '2026-08-04 00:43'
updated_date: '2026-08-07 01:23'
labels:
  - primitives
  - decision
milestone: m-2
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/220'
priority: high
type: feature
ordinal: 200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Migrated from GH #220. The hardcoded trio (_meta/HANDOFF.md / HANDOFF.md / .claude/HANDOFF.md) bakes in the code-desk taxonomy; Backlog.md-managed projects (now including THIS repo) have no sanctioned home. Decision: override via .claude/foreman-kit.local.md frontmatter key (recommended) vs env var. Honor in both handoff hooks + the handoff skill.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Override mechanism ruled and implemented in surfacer + freshness-guard + SKILL.md
- [x] #2 Standard trio unchanged when override absent
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented per the owner ruling. Key name: 'handoff' — follows the activation file's existing single-noun style (effort, enforce, protected) with no redundant _path suffix, matching how 'enforce' is not 'enforce_mode'.

Parser: reused the SHAPE of the tolerant frontmatter parser from config-custody/worker-context but duplicated it physically into each hook rather than importing across hook directories, following the convention worker-context/hook.py documents in its own source — each hook directory is copied and symlinked independently, so a shared module breaks the moment one is installed without the other.

Resolution semantics, each pinned by a test: override absent, unparseable activation file, or activation file present without the key all resolve to None, so the standard candidate search runs on the same code path as before. An override naming an existing in-root file wins outright, even over a standard candidate that also exists. An override naming a NON-EXISTENT path is treated as definitive with no fallback — deliberate, so a stale file left in one of the standard locations from before the override was configured is never resurrected. An override pointing outside the project root is rejected by path arithmetic BEFORE touching the filesystem (tested with a real existing file, /etc/hosts, to prove it is a jurisdiction check rather than an existence check), then falls back to the standard search.

Red run captured before implementation: 3 failures + 1 error, including '_meta/HANDOFF.md' != 'docs/HANDOFF.md' and a case where the guard used a stale standard candidate instead of the fresh override. Green after: 7 + 8 tests OK across two new suites; full suite 373 OK; check_hook_layout exit 0.

Fail-open preserved: each new helper carries its own try/except returning None, backstopped by the pre-existing outer handler. An invalid override degrades to the standard search's own decision and never causes a spurious block.

Incidental fix on code already being touched: handoff-freshness-guard's 'no handoff file found' message hardcoded a duplicate of the candidate-path list. It now derives that phrase from CANDIDATE_PATHS itself via a helper, verified byte-identical to the original literal by test — so the message cannot drift from the actual list. That satisfies the repo's no-unguarded-counts rule on prose that previously violated it.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: session 2026-08-06
created: 2026-08-06 14:13
---
META-06 half of this task resolved 2026-08-06 (owner sign-off, recorded in decision-8): the published repo-meta-structure checklist now accepts the handoff hooks' precedence trio (_meta/HANDOFF.md, HANDOFF.md, .claude/HANDOFF.md), and DOCS-03..05 accept backlog/decisions/ as the ADR home. This repo's .claude/HANDOFF.md location is now standard-conformant. Residual scope of this task: the per-project handoff-location override feature in foreman-kit itself.
---

author: @claude
created: 2026-08-07 01:09
---
Owner ruling 2026-08-07: the override is a KEY IN .claude/atelier.local.md, not an environment variable.

The card framed this as an open choice, but the ground shifted after it was written: atelier now ships a per-project activation file at .claude/atelier.local.md carrying effort/enforce/protected, and both the config-custody and worker-context hooks re-read it per call. So the mechanism already exists and this is one more key rather than a new surface.

The deciding property is when a change takes effect. The activation file is re-read per call, so an edit applies to the very next tool call; env vars are read once at startup and would need a fresh session. For a setting whose whole purpose is telling the hooks where to look, needing a restart to point them somewhere new is the wrong ergonomics.

Implement in the session-handoff-surfacer hook, the handoff-freshness-guard hook, and the handoff skill's SKILL.md. AC#2 stands unchanged: with no override present, the standard three-location search order is unaffected.
---

author: @claude
created: 2026-08-07 01:23
---
Follow-up left for the foreman skill's owner: primitives-core/skills/foreman/references/activation.md documents the .claude/atelier.local.md schema (effort, enforce, protected) and does not yet list the new 'handoff' key. That file sits under the foreman skill, outside this card's owned scope. The schema reference should gain the key so it stays complete.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A project can now relocate its handoff file with a 'handoff' key in .claude/atelier.local.md, honored consistently by the session-handoff-surfacer hook, the handoff-freshness-guard hook, and the handoff skill. The activation file was chosen over an environment variable because it is re-read per call, so an edit applies to the very next tool call rather than needing a fresh session. With no override present the three standard locations are searched exactly as before, proved by test rather than asserted. Six error cases are pinned including the two that matter most: a non-existent override does not silently fall back to a stale standard file, and an override outside the project root is rejected before any filesystem access.
<!-- SECTION:FINAL_SUMMARY:END -->
