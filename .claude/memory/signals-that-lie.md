---
name: signals-that-lie
description: Tool success output is insufficient when the resulting state can be checked directly
metadata:
  type: project
---

Judge by the observed end state when it is cheap to inspect. Retained cases:

- **`make ci` prints ✗ lines on a green run.** They are gate tests exercising failure paths against tempdir fixtures (`✗ identity-neutrality`, `✗ roster<->disk drift`, `✗ opencode laydown — refusing to build into non-empty dir`), and they name real-looking paths. Judge by exit code only: `make ci >/dev/null 2>&1; echo $?`. Re-run before inheriting anyone's claim that the tree is red; a 2026-08-11 handoff reported three failures that did not exist.
- **mermaid-cli exits 0 when the render fails** (a `(` in a node label, `load --> end`): no output file, stack trace on stderr, `$?` clean, and the same diagram renders blank on GitHub with no error. Assert `test -s out.svg`, and for shipped diagrams confirm every label survived into the SVG. The house rule and static gate are in `docs/readme-diagram-standard.md`.
- **A mistyped `kata` subcommand can exit 0.** `kata label remove <ref> <label>` printed help and exited successfully; the subcommand is `rm`. Re-read the issue after a kata write, or assert the intended invariant over `kata list --json`.
- **A probe harness can pass while testing nothing.** An env dict never passed to `subprocess.run(env=...)` let ~80 probes "pass" on the documented fallback; `git status --porcelain` stayed empty while a probe wrote into a gitignored `logs/`. Run one probe first whose result is impossible unless the variable landed; record `os.walk` of the target before and after; delete your own artifacts between runs.

Each case produced a confident wrong report that later work had to unwind. The diagram-specific render rule is maintained in [the diagram standard](../../docs/readme-diagram-standard.md).

Keep existing plugin caches intact while runtime evidence is incomplete. Fixture investigations did not establish an actual-use plugin failure; verify the installed context before proposing any cache or configuration change.
