---
name: deletion-pass
description: Simplify a module to irreducible against its contract — remove or collapse every line that cannot name the commitment it keeps, without changing observable behavior. Use when asked to simplify or tighten a module against its spec, to produce a dry-run deletion report, or when invoked by layer-cycle after a build or fix pass.
---

# Deletion pass

<!-- harness:claude-code -->
In Codex, first read [Codex distribution](../delegation/references/dispatch-knobs.md#codex-distribution)
for installed role setup, native dispatch, isolation prerequisites, and completion routing.
That section supplies the Codex procedures wherever this workflow names Claude Code tools.
<!-- /harness -->

Every line is a commitment: pure transformation (the spec's semantics),
mutation control (validation, guards, error paths), development-time
constraint (types), or observability. A line that can name none of these
is noise. This pass deletes the noise and reports what it learned.

## When not to use

- **Already clean.** A prior pass converged (full sweep, no change) and nothing has been
  added since — re-running finds nothing and burns a cycle.
- **Not understood yet.** You cannot yet state the contract or trace what each line keeps;
  read/trace first, or draft the contract, before deleting against it.
- **About to be rewritten wholesale.** A module slated for a full rewrite doesn't need its
  noise classified — the rewrite discards it anyway.

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
   condition — never a line-count target. **Rule of 500:** past ~500 lines
   a module is too big to hold in one pass — split the module, or split
   the pass into sections, rather than sweeping it all at once.
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
- The rationalizations that save a line — none survive the gate test in Process step 2:

  | Excuse | Honest reading |
  | --- | --- |
  | "Might need it later" | Not in the contract now; git history gets it back if that ever happens. |
  | "It's only one line" | One unclassifiable line is still noise; size isn't the test. |
  | "Someone else wrote it" | Authorship isn't a stratum; it still has to name a commitment. |
  | "It's tested so it must matter" | A test pins behavior, not necessity — delete both and rerun the gate. |
  | "Removing it is out of scope" | The contract, not the diff size, sets scope; if it's not in the contract, it's in scope for this pass. |
