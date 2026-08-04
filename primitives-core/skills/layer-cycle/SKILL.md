---
name: layer-cycle
description: Drive a module through create → evaluate → refine cycles until convergence or budget exhaustion, translating panel findings into scoped fix briefs. Use when asked to "run the cycle", take a module through review and refinement, or iterate a module against a contract. Companions: rubric-panel (evaluate), deletion-pass (refine).
---

# Layer cycle

Quality is layered, not single-pass. This skill is the L1 orchestrator:
it owns the contract, the rubric, and the cycle budget, and is the only
level that knows layering exists. Workers get discrete briefs; findings
flow up, intentions flow down, nothing else crosses levels.

## Inputs (ask only for what's missing)

**target**, **contract**, **rubric**, **gate**; optional cycle budget
(default 3) and effort level.

## Process, per cycle

1. Verify the gate. Red → dispatch a fix brief before anything else.
2. **Evaluate**: invoke rubric-panel (optionally /code-review for deeper
   defect hunting).
3. **Triage** findings by type:
   - `defect` → L2 fix brief: contract citation + the failing case,
     encoded as a test first (red observed) before the fix.
   - `noise` → fold into one deletion-pass invocation.
   - `spec-hole` / `undeclared-commitment` → amend the contract. This is
     an L1 act — only this level edits the spec. Then decide whether the
     amendment implies new behavior (→ fix brief).
   - Contested scores (>1.5 judge spread) → targeted re-judge with a
     tiebreaker persona, or a note to the human.
4. **Refine**: dispatch briefs — fixes first, then deletion-pass, then
   optional hardening (adversarial inputs beyond what the contract
   names).
5. Re-verify gate + golden behavior; record the cycle's scores and diff.

## Stop conditions

- **Convergence**: a full cycle produces no findings and no diff.
- **Budget exhausted**: report remaining findings as known-state.
- **Regression**: scores drop → stop and escalate to the human; never
  silently accept a worse artifact.

## Guardrails (delegation discipline)

- Worker briefs never mention the cycle budget, remaining passes, or
  rubric scores — an L2 agent told about future passes gold-plates the
  current one.
- Each brief includes: read the contract only, no peeking at git history
  or sibling implementations, leave no scratch files, report and stop.
- Contract edits happen only at this level; verify worker claims
  independently (rerun the gate, diff observable outputs) before
  accepting a cycle as done.
- Consult the human only for: contract amendments changing user-visible
  behavior, score regressions, budget increases.
