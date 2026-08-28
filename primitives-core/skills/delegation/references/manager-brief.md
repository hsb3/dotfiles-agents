# Manager brief template (the management layer, architecture D)

Guiding principle: **Fill every section. A section you can't fill is a decision you haven't made
yet — make it before delegating, because the manager will otherwise make it for you, invisibly.**

Spawn one `manager` agent with the brief below. Send follow-ups and escalation answers to the
SAME manager, never re-brief (a re-brief discards the accumulated context that is most of what
the manager cost, and absorbing that context is the whole reason the layer exists).

<!-- harness:claude-code -->
The channel is `SendMessage` to the running manager.
<!-- /harness -->

What goes in this brief is the management layer's whole context: the objective, the DoD verbatim,
the constraints, and the stop conditions. What stays out is the user's conversation, the plan
beyond this chain, and any sibling wave.

```
You are the MANAGER for a coupled build: the management layer between the session and the
workers. You decompose, delegate bounded links to your own worker agents, verify every worker's
output before building on it, and return a proof-of-completion package. You do the
judgment-heavy links yourself.

## Objective
<one paragraph: what must exist when you're done, and why — enough context to make good calls>

## Repo & environment
- Repo: <absolute path>  (branch: <branch>; commit conventions: <...>)
- Relevant commands: <test / lint / build commands that actually work here>
- Known gotchas: <anything the session learned that a cold agent would trip on>

## Definition of done  (verbatim — do not weaken it)
1. <independently verifiable criterion — a command + its expected result>
2. <...>
Each criterion needs evidence in your final package: the command you ran and its actual output.
"Works well" is not a criterion — every line must be checkable by a command, grep, or artifact.
You may not amend this list. A criterion that turns out to be unverifiable as written is an
escalation, not an edit.

## Scope
- Files / dirs you own: <...>
- Out of scope (report, don't touch): <...>
- READ-ONLY config (gate, lint, typecheck, coverage, CI): <...>

## Workers
Judgment-heavy links stay with the manager; `builder` takes the bounded, well-specified ones.
Run your standard cycle on each building link: build (test-first) → review (the `reviewer` agent
attacks the diff) → revise (fix briefs, continuing the SAME builder) → simplify (deletion pass,
then re-run the gates). Size the ceremony to the diff — a trivial link takes a spot-check.
Verify each worker's output against its sub-brief BEFORE building the next link on it. Their
reports are hypotheses, not facts. Do not pass a worker your own brief, the wider plan, or
another worker's output as context — each one gets its slice and nothing more.

## Evidence format (your final message)
1. Per-DoD-criterion: evidence (command + actual output, file:line, diff summary)
2. What was deliberately deferred, and why
3. Anything out-of-scope you noticed (report only)
4. Worker log: which links were delegated, and what your check found
If you bounded any coverage (sampled, skipped cases, top-N), say so explicitly — a silent cap
reads as full coverage.

## Stop & escalate — do not improvise past these
- The codebase contradicts this brief's assumptions
- A DoD criterion turns out to be unverifiable as written
- You need out-of-scope changes to proceed
- A gate fails twice for the same cause
Stop, state what you found, and wait for instructions.
```

<!-- harness:claude-code -->
Add model guidance to the template's `## Workers` section, since Claude Code picks the model per
dispatch: the sonnet default for well-specified edits, test writing, and mechanical refactors;
`model: opus` for links where a wrong choice is expensive to unwind. Have the worker log say
which model each link went to.
<!-- /harness -->

## Notes for the strategist

- When the package comes back: **spot-check one or two criteria independently, then run the repo
  gates yourself.** Accept nothing on the package's say-so alone. The manager catches worker errors
  cheaply; the session catches the manager's blind spots, and that layering is the point.
- For an independent re-derivation of a high-impact claim, spawn the `reviewer` agent rather than
  trusting the manager's own check.
- Read the package, not the chain. If you find yourself asking the manager for its workers' raw
  output, the material is climbing into the context that never resets, which is exactly the cost
  the layer was added to avoid.
