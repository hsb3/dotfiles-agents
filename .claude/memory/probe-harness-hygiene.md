---
name: probe-harness-hygiene
description: "Two ways a verification probe lies — env that never reached the child, and artifacts git status cannot see"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f88d2c41-439c-40b6-bbea-2ee31abb84ec
  modified: 2026-08-10T02:01:26.819Z
---

A probe harness that shells out can pass everything while testing nothing. Two measured failures:

**The env never landed.** I built an env dict, then called `subprocess.run(..., cwd=...)` without
`env=e`. ~80 probes "passed" by silently exercising the code's documented fallback
(`CLAUDE_PROJECT_DIR` → payload `cwd`); the override path was never tested at all. Fix: run one
probe first whose result is *impossible* unless the var landed (point an output path somewhere
unique, assert the file appears there). Also snapshot the ambient env — popping a var from a dict
you never pass is a no-op if the parent already exports it.

**`git status --porcelain` is not a filesystem check.** A live-tree probe wrote
`logs/config-custody.jsonl`; porcelain stayed empty because `logs/` is gitignored, so
"nothing was written to the real repo" would have been a false all-clear. The leftover file then
changed a later run's failure count, which read as flakiness in the code under test. Fix: record
`os.walk` (or `ls -la`) of the target before and after, and delete your own probe artifacts
between runs and at the end — that is cleanup, not "fixing the code", and does not violate
report-only.

Re-run the whole suite after fixing a harness bug; never patch forward from partial results.
Same family as [[make-ci-refusal-line-is-a-passing-test]] and
[[mermaid-cli-exits-zero-on-failure]]: judge by the right signal, not the obvious one.
