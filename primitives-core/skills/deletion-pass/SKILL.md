---
name: deletion-pass
description: Simplify a module to irreducible against its contract — remove or collapse every line that cannot name the commitment it keeps, without changing observable behavior. Use when asked to simplify or tighten a module against its spec, to produce a dry-run deletion report, or when invoked by layer-cycle after a build or fix pass.
---

# Deletion pass

Every line is a commitment: pure transformation (the spec's semantics),
mutation control (validation, guards, error paths), development-time
constraint (types), or observability. A line that can name none of these
is noise. This pass deletes the noise and reports what it learned.

## Inputs (ask only for what's missing)

- **target** — module (implementation + tests).
- **contract** — the spec that defines observable behavior and declared
  concerns. No contract → offer to draft one first; never guess.
- **gate** — the one-command check (typecheck/lint/format/tests+coverage).
- **mode** — `edit` (default) or `dry-run` (report only, no edits kept).

## Preconditions

Gate green and git state clean before touching anything. Capture golden
outputs first: run the program on representative invocations — normal
case, error paths, empty case — and save stdout/stderr/exit codes/files.
Tests under-cover; behavior is pinned by golden diff *plus* the suite.

## Process

1. Classify each line's stratum: transformation | mutation control |
   type constraint | observability | **unclassifiable**. Unclassifiable
   lines are primary candidates; redundant members of other strata
   (duplicate guards, constants used once, indirection with one caller)
   are secondary.
2. Per candidate, smallest first: delete or collapse → run gate → diff
   golden outputs.
   - All green and identical → it was noise. Keep the deletion; ledger it.
   - Anything breaks → restore. If what broke is **not in the contract**,
     that is a finding: `spec-hole` or `undeclared-commitment` — the line
     was load-bearing for something nobody wrote down.
3. Sweep until a full sweep produces no change. Irreducible is the done
   condition — never a line-count target.
4. Formatter, final gate, final golden diff.

In `dry-run` mode do the same probing but revert every kept-deletion at
the end; the ledger is the entire deliverable.

## Output — the ledger

One markdown report, three sections:
1. **Removed** — each deletion + why nothing broke (what stratum it
   pretended to be).
2. **Collapsed** — simplifications that preserved behavior.
3. **Kept, with findings** — lines that survived only because of an
   unwritten commitment; each becomes a proposed contract amendment.
   Amendments flow up to the orchestrator/owner — never apply them here.

## Guardrails

- Never weaken a test, lower a threshold, or touch config to make a
  deletion survive.
- Never change observable behavior; bugs found are findings, not fixes.
- Work on clean git state so the pass is one reviewable diff.
