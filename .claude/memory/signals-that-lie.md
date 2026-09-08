---
name: signals-that-lie
description: Five tools here report success while failing; judge each by its real end state, not its own message
metadata:
  type: project
---

Judge by the observed end state, never by a tool's own success signal. Five measured cases:

- **`make ci` prints ✗ lines on a green run.** They are gate tests exercising failure paths against tempdir fixtures (`✗ identity-neutrality`, `✗ roster<->disk drift`, `✗ opencode laydown — refusing to build into non-empty dir`), and they name real-looking paths. Judge by exit code only: `make ci >/dev/null 2>&1; echo $?`. Re-run before inheriting anyone's claim that the tree is red; a 2026-08-11 handoff reported three failures that did not exist.
- **mermaid-cli exits 0 when the render fails** (a `(` in a node label, `load --> end`): no output file, stack trace on stderr, `$?` clean, and the same diagram renders blank on GitHub with no error. Assert `test -s out.svg`, and for shipped diagrams confirm every label survived into the SVG. The house rule and static gate are in `docs/readme-diagram-standard.md`.
- **A Kaneo bulk write reverts silently.** `PATCH /task/bulk` reported `applied N cells` and every agent-attributed status change was undone 1–5s later by an unattributed write; the single-field `PUT /task/status/{id}` persisted. Applies to the shipped `board-triage` kaneo adapter (open card dvt3): write one field at a time and re-read after ~15s before reporting.
- **An unknown `kata` subcommand exits 0.** `kata label remove <ref> <label>` prints the `kata label` help and exits 0 — the subcommand is `rm`. So `kata label remove ... && echo ok` reports success having changed nothing, and with output redirected the no-op is invisible (measured 2026-09-08: three cards kept the label they were meant to lose and silently ended up with two `area:*` labels each). Cobra does this for any mistyped subcommand, so it is not specific to `label`. Never trust `&&` after a `kata` write — re-read the issue, or assert the invariant over `kata list --json`.
- **A probe harness can pass while testing nothing.** An env dict never passed to `subprocess.run(env=...)` let ~80 probes "pass" on the documented fallback; `git status --porcelain` stayed empty while a probe wrote into a gitignored `logs/`. Run one probe first whose result is impossible unless the variable landed; record `os.walk` of the target before and after; delete your own artifacts between runs.

**Why:** each of these produced a confident wrong report that a later session had to unwind. Related: [[no-unguarded-counts-in-prose]], [[measure-a-heuristic-against-a-corpus]].
