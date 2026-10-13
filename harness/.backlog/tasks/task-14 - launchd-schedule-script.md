---
id: TASK-14
title: launchd schedule script
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:07'
updated_date: '2026-10-13 03:34'
labels: []
milestone: m-0
dependencies:
  - TASK-13
references:
  - launchd-script
  - launchd
  - weekly-campaign
  - campaign
modified_files:
  - .groma/flows/weekly-campaign.md
  - .groma/systems/harness/containers/launchd-script/container.md
  - README.md
  - scripts/launchd.sh
  - test/launchd.test.ts
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
- [x] #1 scripts/launchd.sh is POSIX sh with install, uninstall, status and run subcommands as the spec describes, and a test runs sh -n on it
- [x] #2 install writes the plist with the spec Label, ProgramArguments, WorkingDirectory, StartCalendarInterval, RunAtLoad and log paths
- [x] #3 run prepends the PATH entries, fills unset API keys from secret get without printing them, runs the campaign, notifies and exits with its code
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. scripts/launchd.sh (POSIX sh): install <cases-dir> <candidates-root> writes ~/Library/LaunchAgents/com.hsb3.agent-harness.campaign.plist (Label, ProgramArguments /bin/sh <pkg>/scripts/launchd.sh run <abs cases> <abs root>, WorkingDirectory <pkg>, Monday 09:00, RunAtLoad false, expanded log paths), boots out (ignoring failure), bootstraps and prints the kickstart next step; uninstall; status (state, last exit, next fire lines or 'agent not loaded'); run (PATH prefix, unset API keys from 'secret get' without printing, bun campaign, osascript notification ignoring failure, campaign exit code).
2. test/launchd.test.ts: sh -n, install plist content and launchctl calls with a stub launchctl, uninstall, status both ways, run with stub bun/secret/osascript checking env, argv, exit code and that no secret is printed.
3. Add the Weekly campaign flow over launchd -> script -> CLI -> campaign -> grid -> trial -> ledger and campaign log, with the later evals-loader step.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Evidence: `bunx tsc --noEmit && bun test` -> 110 pass, 0 fail. test/launchd.test.ts: `sh -n` passes; install with a stub launchctl writes the plist (Label, ProgramArguments with XML-escaped absolute dirs, WorkingDirectory, Weekday 1 Hour 9 Minute 0, RunAtLoad false, expanded log paths), `plutil -lint` accepts it, bootout (failure ignored) then bootstrap with gui/<uid>, kickstart line printed; install rejects missing dirs with exit 2 without calling launchctl; uninstall; status both ways; run with stub bun/secret/osascript: PATH prefix order, unset key filled from secret get and never printed, set key untouched, bun argv, notification text ok/failed with osascript failure ignored, campaign exit code passed through. groma: the script is outside the TypeScript scanner, so the declared launchd-script container carries it; its overview updated; flow weekly-campaign added (launchd -> script -> CLI -> campaign -> grid -> trial -> ledger, reports, campaign log, then owner -> evals loader); scan clean, lint clean. README rewritten from the scaffold text.
Product calls: install exits 2 on a missing directory or wrong arguments and 1 when bootstrap fails; status strips leading whitespace from the launchctl lines; a secret counts as missing when the variable is unset or empty; uninstall and install print one confirmation line.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added scripts/launchd.sh (install/uninstall/status/run for the com.hsb3.agent-harness.campaign LaunchAgent) with 6 tests incl. sh -n and plutil lint, the weekly-campaign flow, and a README.
<!-- SECTION:FINAL_SUMMARY:END -->
