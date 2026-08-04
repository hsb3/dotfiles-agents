---
id: TASK-22
title: 'Harness: fix isolation gaps + log environment preconditions'
status: To Do
assignee: []
created_date: '2026-08-04 00:44'
labels:
  - harness
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/172'
priority: medium
type: bug
ordinal: 1400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Work item for GH bug #172 (stays open as the report; close on fix). Symmetric runner isolation, log runtime self-installs as preconditions, --keep-workspaces for campaigns, resolve agent candidates without a staged temp dir. Source: W3 adversarial review 3.4-3.8.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Both runners load only intended plugins
- [ ] #2 --keep-workspaces preserves passing-trial workspaces
- [ ] #3 make harness-eval resolves flat agent candidates
- [ ] #4 GH #172 closed on merge
<!-- AC:END -->
