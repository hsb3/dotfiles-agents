---
id: TASK-066
title: >-
  kaneo: preflight catches the MCP registration that silently authenticates the
  owner
status: Done
assignee:
  - '@claude'
created_date: '2026-08-11 15:54'
updated_date: '2026-08-11 15:54'
labels:
  - primitives
milestone: m-1
dependencies: []
priority: high
type: bug
ordinal: 45000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A server also named `kaneo` registered directly in ~/.claude.json outranks the plugin's. Headerless, it makes Claude Code fall back to interactive OAuth, whose browser consent authenticates the human owner rather than the repo's agent — so every tool call succeeds under the wrong name and every claim comment is misattributed. Nothing errors.

Observed 2026-08-11 in learn-pocketbase (session 5faa46f5): ~40 messages and four restarts, because the docs pointed at the wrong cause. configuration.md said owner identity meant 'the wrong key is wired' (it was correct throughout) and SKILL.md framed the two tool-name forms as a benign naming detail.

Also corrects restart semantics: '/reload-plugins' and resume do not respawn MCP servers; headers expand once at process start.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 kaneo-preflight reports a headerless direct kaneo registration, in both user and project scope, separately from the board-unavailable causes
- [x] #2 a direct registration carrying its own Authorization header stays silent, case-insensitively
- [x] #3 configuration.md names the shadow as the more likely cause of owner identity, with the remove command
- [x] #4 every 'restart the session' instruction says fully quit and relaunch, and says why
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
kaneo-preflight gains identity_problems(), reported in its own message block with its own header/footer (the remedy and stakes differ from the absent-tools causes, and 'board NOT available' is the wrong thing to read while the tools work). Only headerless registrations flagged; a deliberate one with its own header is supported and silent. Docs corrected in SKILL.md, references/configuration.md, the hook README, and the bundle README. Version 0.4.2 -> 0.5.0.

Verification: 6 new tests (tests/test_kaneo_policy.py) covering both scopes, the authed-and-silent case, case-insensitive header matching, cross-project non-leakage, and both failure kinds together. make ci exit 0. PR #310 green on both checks. Hook also run by hand against a fixture replicating the exact observed ~/.claude.json shape, and it emits the wrong-identity message with the remove command.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
kaneo-preflight now catches the shadowing MCP registration at session start and reports it as a wrong-identity failure rather than an unavailable-board one; restart semantics corrected everywhere. Verified with 6 new tests, make ci exit 0, green PR CI, and a hand-run against a replica of the config that actually caused the incident.
<!-- SECTION:FINAL_SUMMARY:END -->
