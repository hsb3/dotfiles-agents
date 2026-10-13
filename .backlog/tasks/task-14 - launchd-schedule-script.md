---
id: TASK-14
title: launchd schedule script
status: To Do
assignee: []
created_date: '2026-10-13 03:07'
labels: []
milestone: m-0
dependencies:
  - TASK-13
references:
  - launchd-script
  - launchd
priority: high
type: feature
ordinal: 14000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The owner schedules the campaign weekly through launchd with an optional POSIX sh script that installs, removes, inspects and runs the LaunchAgent (SPEC.md Scheduled campaign). Builds the launchd-script container.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 scripts/launchd.sh is POSIX sh with install, uninstall, status and run subcommands as the spec describes, and a test runs sh -n on it
- [ ] #2 install writes the plist with the spec Label, ProgramArguments, WorkingDirectory, StartCalendarInterval, RunAtLoad and log paths
- [ ] #3 run prepends the PATH entries, fills unset API keys from secret get without printing them, runs the campaign, notifies and exits with its code
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
