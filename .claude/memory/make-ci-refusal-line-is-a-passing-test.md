---
name: make-ci-refusal-line-is-a-passing-test
description: "The \"✗ opencode laydown — refusing…\" line in make ci output is a passing test's own output — judge by exit code, not by scanning for ✗"
metadata: 
  node_type: memory
  type: project
  originSessionId: f88d2c41-439c-40b6-bbea-2ee31abb84ec
  modified: 2026-08-10T02:01:55.841Z
---

A fully green `make ci` prints several `✗` lines. They are unit tests exercising the check
scripts' failure paths against synthetic tempdir fixtures, printing the failure message as part
of **passing** (suite reports `OK`, exit 0; verified 2026-08-06 and again 2026-08-11).
Seen so far: `✗ opencode laydown — refusing to build into non-empty dir`,
`✗ identity-neutrality: 1 violation(s)`, `✗ roster<->disk drift: 1 problem(s)`.

**Tell a fixture from the real repo by its counts.** The fixture output says "1 primitives
(command=1)" or "1 plugin(s), 2 symlink(s)"; the real repo says 53 primitives and 6 plugins. The
fixture also names real-looking paths (`primitives-core/commands/activate.md`), so the path alone
proves nothing.

**How to apply:** judge `make ci` by its exit code (`make ci >/dev/null 2>&1; echo $?`), never by
grepping output for `✗` or `FAIL`. **Re-run it yourself before inheriting anyone's claim that the
tree is red** — on 2026-08-11 a session handoff reported "3 pre-existing failures on HEAD" that
did not exist, and mis-attributed two of them to a test file that was passing. Same lesson,
opposite direction: [[mermaid-cli-exits-zero-on-failure]].
