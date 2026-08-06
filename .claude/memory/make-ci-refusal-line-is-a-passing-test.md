---
name: make-ci-refusal-line-is-a-passing-test
description: "make ci prints an \"✗ opencode laydown — refusing to build into non-empty dir\" line that is a PASSING test's own output — judge by exit code, not by scanning for ✗"
metadata: 
  node_type: memory
  type: project
  originSessionId: d6661eac-d9a4-4ee1-937a-b9a5141ce8ca
  modified: 2026-08-06T05:28:16.467Z
---

`make ci` output contains `✗ opencode laydown — refusing to build into non-empty dir: /var/...` even on a fully green run — it is a unit test exercising the generator's refusal path, printing the refusal message to stdout as part of PASSING (suite reports `OK`, exit 0).

**Why:** grepping CI output for `✗`/`FAIL` false-positives on this line; verified 2026-08-06 by running `make ci` on a clean tree (same line, exit 0).

**How to apply:** judge `make ci` by its exit code (`make ci > /dev/null 2>&1; echo $?`), never by scanning for ✗ glyphs. Related: [[backlog-cli-rewrites-sibling-tasks]].
