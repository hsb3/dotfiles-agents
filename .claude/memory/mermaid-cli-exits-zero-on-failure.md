---
name: mermaid-cli-exits-zero-on-failure
description: "mermaid-cli returns exit 0 when a render fails and writes no file — assert on the output file, never on $?"
metadata: 
  node_type: memory
  type: reference
  originSessionId: f88d2c41-439c-40b6-bbea-2ee31abb84ec
  modified: 2026-08-10T02:02:00.807Z
---

`npx @mermaid-js/mermaid-cli` **exits 0 when the render fails.** Measured 2026-08-07 building the
plugin-README diagram gate: a `(` inside a node label, and `load --> end` (reserved word as a bare
node id), each produced **no output file at all** while the process reported success. The stack
trace goes to stderr; `$?` says everything is fine. The same failures render **blank on GitHub
with no error**, so neither the renderer, the exit code, nor reading the source will tell you a
diagram is broken.

**How to apply:** verify a render with `test -s out.svg`, and for anything shipping to consumers
confirm every node and edge label survived into the SVG text (partial renders happen). The
banned-character house rule and its static gate live in `backlog/docs/readme-diagram-standard.md`;
that rule is deliberately wider than the current renderer's tolerance (`&` renders fine today and
is still banned). Related: [[make-ci-refusal-line-is-a-passing-test]].
