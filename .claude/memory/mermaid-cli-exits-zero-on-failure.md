---
name: mermaid-cli-exits-zero-on-failure
description: "mermaid-cli returns exit 0 when a render fails and writes no file — assert on the output file, never on $?"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 390113e2-409d-45c8-80b8-186cc32d27d2
  modified: 2026-08-07T14:54:34.187Z
---

`npx @mermaid-js/mermaid-cli` **exits 0 when the render fails.** Measured 2026-08-07 while
building the plugin-README diagram gate: a `(` inside a node label and `load --> end`
(reserved word as a bare node id) each produced **no output file at all**, and the process
still reported success. A stack trace goes to stderr, but `$?` says everything is fine.

The same failures render **blank on GitHub with no error**, so neither the renderer, the
exit code, nor reading the source will tell you a diagram is broken.

**Why:** the CLI's error path does not propagate the in-page render exception to the process
exit status.

**How to apply:** verify a render by asserting the output file exists and is non-empty —
`test -s out.svg` — and for anything shipping to consumers, confirm every node and edge
label survived into the SVG text (a partial render is also possible). Never conclude a
diagram is correct from a green exit code. Related: the banned-character rule and the gate
that enforces it statically live in `backlog/docs/readme-diagram-standard.md`; a separate
measured fact is that `&` currently renders fine despite being banned, so the house rule is
deliberately wider than one renderer's present tolerance. See also
[[make-ci-refusal-line-is-a-passing-test]] — same lesson, opposite direction: judge a tool
by the right signal, not the obvious one.
