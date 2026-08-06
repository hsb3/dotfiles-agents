---
id: TASK-030
title: 'iterm2 skill: preferences model, shell integration, default-terminal bindings'
status: Done
assignee: []
created_date: '2026-08-06 16:02'
updated_date: '2026-08-06 17:07'
labels: []
dependencies: []
priority: medium
type: feature
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Author an iterm2 skill covering iTerm2 configuration and its distinguishing features. No terminal-emulator skill existed in the marketplace.

The skill front-loads two silent-failure classes that defeat naive automation:

1. iTerm2 holds its whole configuration in memory and rewrites the plist on quit, so a defaults write issued while it runs is clobbered with no error. Both obvious guards misreport: pgrep -x iTerm2 never matches (pgrep compares the full executable path, and bare pgrep iTerm matches only the iTermAI/iTermServer helpers), and the ps | grep -q rewrite returns 141 under pipefail via SIGPIPE, inverting the check.
2. Shell integration is inert until installed, and the standard rc guard turns a missing install into a silent no-op rather than an error.

References cover configuration (prefs keys, dynamic profiles, custom prefs folder for repo-tracking), shell integration and utilities, the five-UTI macOS default-terminal binding (duti exits 0 on bindings LaunchServices discarded), and a power-feature catalog.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 SKILL.md exists at primitives-core/skills/iterm2 with a trigger-rich description
- [x] #2 References cover configuration, shell integration, default-terminal bindings, and the feature catalog
- [x] #3 Thin symlink assembly at plugins/iterm2 per ADR 0017, listed in marketplace.json
- [x] #4 Roster entry present in primitives-core.yaml
- [x] #5 make ci passes
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
iterm2 skill shipped: SKILL.md + 4 references (configuration, shell-integration, default-terminal, features) at primitives-core/skills/iterm2; thin symlink assembly at plugins/iterm2 (ADR 0017) listed in marketplace.json; roster entry in primitives-core.yaml. Verified via make ci (exit 0) on dev tip e8cf954. Merged via PR #248, published to main (commit 19f1df5, publish: dev@e8cf954) via local publish workaround during a GitHub Actions outage.
<!-- SECTION:FINAL_SUMMARY:END -->
