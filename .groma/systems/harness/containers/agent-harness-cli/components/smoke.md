---
type: C4 Component
title: Smoke
description: Checks that a candidate loads under each harness
status: stable
groma:
  id: smoke
  parent: agent-harness-cli
  technology: TypeScript
  draft: v1
  code:
    - scanner: typescript
      file: src/smoke.ts
---

Serves `--smoke`. For each (harness, model) cell that passes preflight it injects the candidate into an empty workspace in a fresh run dir exactly as a `with` trial would (same injection, argv, environment and isolation, through the trial's agent-run step), sends `Reply with exactly: OK` with the cell's model and `--timeout`, writes the raw stdout to `<runs-dir>/<harness>-smoke-<candidate>-<stamp>-<hex>.log` and deletes the run dir. It prints one block per cell: harness, kind, the plugins loaded (claude only; `(not reported)` elsewhere), one `✗ plugin_error:` line per plugin error (a failed codex plugin install included), the exit line when the exit code is not 0, and the verdict. A kind the harness cannot host prints a skip line and fails the cell. It loads no cases, grades nothing and writes no ledger row; it exits 0 only when at least one cell ran and every cell that ran passed.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/smoke.ts](../../../../../../src/smoke.ts) | [src/candidate.ts](../../../../../../src/candidate.ts) | Loads the candidate | function call |
| [src/smoke.ts](../../../../../../src/smoke.ts) | [src/harnesses.ts](../../../../../../src/harnesses.ts) | Preflights each cell | function call |
| [src/smoke.ts](../../../../../../src/smoke.ts) | [src/trial.ts](../../../../../../src/trial.ts) | Runs the agent like a with trial | function call |
| [src/smoke.ts](../../../../../../src/smoke.ts) | [src/commands.ts](../../../../../../src/commands.ts) | Writes command output | Io callbacks |
| [src/smoke.ts](../../../../../../src/smoke.ts) | [src/grid.ts](../../../../../../src/grid.ts) | Lists the harness × model cells | function call |
| [src/smoke.ts](../../../../../../src/smoke.ts) | [trial-logs](../../trial-logs/container.md) | Writes the smoke log | file |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/smoke.ts](../../../../../../src/smoke.ts) | [src/candidate.ts](../../../../../../src/candidate.ts) | Calls imported function: loadCandidate | typescript |
| [src/smoke.ts](../../../../../../src/smoke.ts) | [src/commands.ts](../../../../../../src/commands.ts) | Invokes supplied callbacks: err, out | typescript |
| [src/smoke.ts](../../../../../../src/smoke.ts) | [src/grid.ts](../../../../../../src/grid.ts) | Calls imported function: cells | typescript |
| [src/smoke.ts](../../../../../../src/smoke.ts) | [src/harnesses.ts](../../../../../../src/harnesses.ts) | Calls imported functions: adapterFor, preflight | typescript |
| [src/smoke.ts](../../../../../../src/smoke.ts) | [src/trial.ts](../../../../../../src/trial.ts) | Calls imported functions: errorField, logStamp, makeRunDir, randomHex, runAgent | typescript |
