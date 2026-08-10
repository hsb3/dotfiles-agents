---
name: make-ci-refusal-line-is-a-passing-test
description: "The \"✗ opencode laydown — refusing…\" line in make ci output is a passing test's own output — judge by exit code, not by scanning for ✗"
metadata: 
  node_type: memory
  type: project
  originSessionId: f88d2c41-439c-40b6-bbea-2ee31abb84ec
  modified: 2026-08-10T02:01:55.841Z
---

A fully green `make ci` still prints
`✗ opencode laydown — refusing to build into non-empty dir: /var/...`. It is a unit test
exercising the generator's refusal path and printing the refusal message as part of **passing**
(suite reports `OK`, exit 0; verified 2026-08-06 on a clean tree).

**How to apply:** judge `make ci` by its exit code (`make ci >/dev/null 2>&1; echo $?`), never by
grepping output for `✗` or `FAIL`. Same lesson, opposite direction:
[[mermaid-cli-exits-zero-on-failure]].
