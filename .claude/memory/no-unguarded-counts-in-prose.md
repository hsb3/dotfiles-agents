---
name: no-unguarded-counts-in-prose
description: Owner rule — never hardcode counts in prose or repo metadata unless a gate checks them; guarded numbers are fine
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 143854bf-3f7b-45e1-92ce-1069a124586e
  modified: 2026-08-06T19:20:51.491Z
---

Owner direction 2026-08-06 (setting the GitHub About box, and applied to `README.md` in the
same breath): **do not put a count in prose or in repo metadata unless something mechanically
verifies it.** "20 plugins" in a description, a lede, or an About box is a maintenance burden
that falsifies itself the moment the lineup changes.

**Why:** this is the exact defect TASK-031 was opened to fix. The README claimed "eleven
standalone one-skill plugins" when there were sixteen, and `marketplace.json`'s
`metadata.description` carried its own hand-enumerated lineup that no gate read. Prose counts
rot silently and nobody notices until a visitor does.

**How to apply:** guarded numbers are fine and preferred — the catalog table's `Contents`
column keeps its counts because `scripts/check_catalog.py` verifies them against disk. Prose
counts, About-box text, and any enumeration a gate cannot reach get phrased so that adding the
next item does not make the sentence false. When you must state a count, ask first whether a
check can read it; if not, rewrite the sentence.

Related: [[backlog-md-task-management]] holds the task system this was recorded against.
