---
id: TASK-13
title: Weekly campaign command
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:07'
updated_date: '2026-10-13 03:32'
labels: []
milestone: m-0
dependencies:
  - TASK-11
references:
  - campaign
  - campaign-logs
  - grid
  - cases-directory
  - candidate-extender
modified_files:
  - .groma/systems/harness/containers/agent-harness-cli/components/campaign.md
  - .groma/systems/harness/containers/agent-harness-cli/components/commands.md
  - src/campaign.ts
  - src/commands.ts
  - test/campaign.test.ts
priority: high
type: feature
ordinal: 13000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The weekly schedule runs every cased candidate with a dated label so a same-day rerun resumes, and logs the transcript (SPEC.md Campaign). Builds groma components campaign and the campaign-logs store.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Requires --cases-dir and --candidates-root; discovers candidates as sorted subdir names minus _template and smoke-echo; none prints "no candidates discovered under <dir>" and exits 1
- [x] #2 Resolves each candidate path (first <root>/*/<name>/ in sorted order, else <root>/agents/<name>.md), warning and failing a missing one
- [x] #3 Runs each candidate as the run command would with the campaign flags and default label weekly-<YYYYMMDD>, printing FAILED lines, the reports and the completion line, and appends everything to <dir of --results>/campaign-logs/<label>.log
- [x] #4 --dry-run prints the DRYRUN lines, runs and writes nothing, and exits by the same rule
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. src/campaign.ts: discoverCandidates (sorted subdirs of --cases-dir minus _template, smoke-echo), resolveCandidatePath (first <root>/*/<name>/ in sorted order, else <root>/agents/<name>.md), runCampaign(opts, root, dryRun, io): header, candidates line, per-candidate runCandidate with the campaign flags (WARN for a missing path, FAILED for a non-zero exit), per-candidate report sections, completion line with the log path; every printed line also appended to <dir of --results>/campaign-logs/<label>.log; --dry-run prints DRYRUN lines and writes nothing.
2. commands.ts: dispatch campaign; --cases-dir and --candidates-root required (exit 2).
3. test/campaign.test.ts through the CLI with stubs: discovery and exclusions, path resolution order, WARN and FAILED paths, output order, log appended and resumed on a same-day rerun, dry run, no candidates.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Evidence: `bunx tsc --noEmit && bun test` -> 104 pass, 0 fail. test/campaign.test.ts: discovery and exclusions, path resolution order (group dirs sorted before agents/<name>.md), a full campaign through src/cli.ts with stubs (header, candidates line, WARN for a missing candidate, two candidates run with the weekly-<date> label, report sections incl. "no result rows", completion line with the log path, exit 1, log containing every stdout and stderr line), same-day rerun resuming and appending to the log, FAILED for a candidate exiting 2 with the campaign continuing, ok/exit 0, dry run (exact DRYRUN lines with and without --model, no log, no CLI calls, exit by the same rule), missing inputs exit 2, no candidates exit 1. groma: matched 1; accepted campaign and 6 planned relations; added campaign -> commands and campaign -> trial; a duplicate-logic finding (isDir in campaign.ts vs cases.ts) was refactored away; lint clean.
Product calls: "no candidates discovered" goes to stderr with no header and no log; WARN and FAILED lines go to stderr and into the log; the dry run prints the header, the candidates line, the DRYRUN (or WARN) lines and the completion line without the log part; --candidates-root is resolved to an absolute path, so WARN shows it absolute; candidate dirs found through symlinks count.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added src/campaign.ts (candidate discovery and path resolution, per-candidate grid runs with the dated label, FAILED/WARN handling, report sections, completion line, campaign log tee, --dry-run) and dispatched campaign from commands with its required flags. Verified by 6 campaign tests through the CLI.
<!-- SECTION:FINAL_SUMMARY:END -->
