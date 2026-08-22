---
name: starting-conditions
description: >-
  Set a project's starting conditions before the code exists — the conversation that
  decides what is being built, in what language, and which quality checks are
  machine-enforced, ending in a `RULES.md` contract plus one gate command that proves it.
  Use when starting a new repo or project, adding rigor to an existing one, or when the
  ask is "set this up properly", "define done", "what gates should this repo have",
  "write a RULES.md", "how do I keep agents from making a mess in this repo", or when a
  repo's quality conventions live only in someone's head. Interview first, write second:
  every question left unanswered becomes divergence to adjudicate later. Not for repo
  layout standards (repo-meta-structure), scaffolding missing meta-structure
  (mise-en-place-scaffold), or running controlled experiments.
---

# Starting conditions

Starting conditions are the decisions that are cheap now and expensive later: what the
artifact is, what language it is written in, and what a machine will refuse to let
through. Set them once, in writing, before the first line. Everything after is
downstream of them.

Your job here is **conversational**. Interview the owner, then write. Do not open with
a draft contract — a contract written from assumptions gets ratified, not corrected,
and the assumptions ship.

## The three outputs

1. **`RULES.md`** — the contract. What we're building, the language, the gate, the
   enumerated rules, the behavioral spec, the measured baseline.
2. **One gate command** — `make check`. It is the CI, the pre-commit hook, and the
   definition of done. If there are two commands, there is no gate.
3. **A measured baseline** — what the gate says about the repo *today*, before anyone
   fixes anything.

## Procedure

1. **Interview.** Work `references/interview.md` in order. Do not skip to tooling; the
   first two questions decide the rest. Stop and ask when an answer is vague — "good
   test coverage" is not an answer, "≥85% lines, in-process" is.
2. **Sort every rule into machine-checkable or not.** This is the load-bearing step.
   Anything a tool can check becomes a gate step; only what tools cannot see stays a
   prose rule, and each of those gets a budget.
3. **Write the contract** from `assets/contract-template.md`.
4. **Build the rig** — `references/rig-cookbook.md` has the per-stack recipes. Delegate
   this to the `rig-builder` agent when the stack is known; it is mechanical work with a
   machine-checkable definition of done.
5. **Prove the gate both ways.** Green on the real tree, and *red* when it should be:
   break a rule on purpose and watch the gate catch it. A gate that cannot fail is
   decoration. Delete the sabotage afterwards.
6. **Measure the baseline and stop.** Record what fails. Do not fix it in the same pass
   — writing the contract and satisfying it are separate jobs, and a baseline measured
   after remediation is worthless.

## Hard rules

- **Machine-enforce everything a tool can check.** Quality holds exactly where a machine
  enforces it and drifts everywhere else. A prose rule is what you spend when no tool
  can see the thing.
- **Every prose rule carries a budget or a stop condition.** An unbounded rule gets
  *maximized*, not satisfied: "no magic literals" once produced a 90-line constants wall
  where 43 of 57 constants were used exactly once. Bound it — "at most one inline
  comment per function" — or do not write it.
- **Config files are read-only for whoever builds against the contract.** If a gate looks
  unsatisfiable, that is a report, not a licence to loosen it.
- **The rig is inside its own gate.** A checker that cannot pass the standard it enforces
  is advice, not law.
- **Error paths, the zero-result case, and tie-breaks are first-class spec.** Unspecified
  edges are where every implementation diverges and where the real bugs live.
- **Name the precision of every comparison.** "Sorted by timestamp" is silent about ties;
  "equal at whole-second output precision, then by name" is not.

## References

- `references/interview.md` — the question script, what a vague answer sounds like, and
  the follow-up that sharpens it.
- `references/rig-cookbook.md` — one-gate-command recipes per stack (Python, TypeScript,
  Go, Rust, prose/docs artifacts), and what to reach for when the artifact has no compiler.
- `references/worked-examples.md` — two real contracts, one for a program and one for a
  documentation artifact, and what each got wrong first.
- `assets/contract-template.md` — the `RULES.md` skeleton. Copy, do not improvise.
