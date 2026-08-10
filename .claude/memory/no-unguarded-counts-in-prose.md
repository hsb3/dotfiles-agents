---
name: no-unguarded-counts-in-prose
description: Owner rule — no count in prose or repo metadata unless a gate mechanically checks it
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f88d2c41-439c-40b6-bbea-2ee31abb84ec
  modified: 2026-08-10T02:02:05.022Z
---

Owner direction 2026-08-06 (set while writing the GitHub About box, applied to `README.md` in the
same breath): **never state a count in prose or repo metadata unless something mechanically
verifies it.** The README had claimed "eleven standalone one-skill plugins" when there were
sixteen, and `marketplace.json`'s `metadata.description` carried a hand-enumerated lineup no gate
read. Prose counts falsify themselves the moment the lineup changes, silently.

**How to apply:** guarded counts are fine and preferred — the catalog table keeps its `Contents`
numbers because `scripts/check_catalog.py` verifies them against disk. Everything a gate cannot
reach gets phrased so adding the next item does not make the sentence false. Before writing a
number, ask whether a check can read it; if not, rewrite the sentence.
