---
type: C4 Component
title: Campaign
description: Runs the weekly campaign over every cased candidate
status: stable
groma:
  id: campaign
  parent: agent-harness-cli
  technology: TypeScript
  code:
    - scanner: typescript
      file: src/campaign.ts
---

Serves `agent-harness campaign`, which needs `--cases-dir` and `--candidates-root`. It discovers the candidates as the sorted subdirectory names of the cases dir, minus `_template` and `smoke-echo` (none prints `no candidates discovered under <dir>` and exits 1), and resolves each one's path as the first `<root>/<group>/<name>/` directory in sorted order, else `<root>/agents/<name>.md` (none warns and fails that candidate). Each candidate runs through the grid exactly as `agent-harness <name> --candidate-dir <path>` would, with the campaign's flags and the `weekly-<YYYYMMDD>` label (so a same-day rerun resumes); a non-zero exit prints `FAILED` and the campaign continues. It then prints each candidate's report and the completion line, appending everything it prints to `<dir of --results>/campaign-logs/<label>.log`. `--dry-run` prints the `DRYRUN:` commands instead and writes nothing. Exits 0 only when every candidate's run exited 0.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/campaign.ts](../../../../../../src/campaign.ts) | [src/grid.ts](../../../../../../src/grid.ts) | Runs each candidate | function call |
| [src/campaign.ts](../../../../../../src/campaign.ts) | [src/report.ts](../../../../../../src/report.ts) | Prints each report | function call |
| [campaign](campaign.md) | [campaign-logs](../../campaign-logs/container.md) | Appends the transcript | file |
| [campaign](campaign.md) | [cases-directory](../../../../../externals/cases-directory.md) | Discovers candidates | directory listing |
| [campaign](campaign.md) | [candidate-extender](../../../../../externals/candidate-extender.md) | Resolves candidate paths | directory lookup |
| [src/campaign.ts](../../../../../../src/campaign.ts) | [src/commands.ts](../../../../../../src/commands.ts) | Writes command output | Io callbacks |
| [src/campaign.ts](../../../../../../src/campaign.ts) | [src/trial.ts](../../../../../../src/trial.ts) | Formats the campaign timestamp | function call |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/campaign.ts](../../../../../../src/campaign.ts) | [src/commands.ts](../../../../../../src/commands.ts) | Invokes supplied callbacks: err, out | typescript |
| [src/campaign.ts](../../../../../../src/campaign.ts) | [src/grid.ts](../../../../../../src/grid.ts) | Calls imported function: runCandidate | typescript |
| [src/campaign.ts](../../../../../../src/campaign.ts) | [src/report.ts](../../../../../../src/report.ts) | Calls imported function: report | typescript |
| [src/campaign.ts](../../../../../../src/campaign.ts) | [src/trial.ts](../../../../../../src/trial.ts) | Calls imported function: localTs | typescript |
