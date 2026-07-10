# Lead-agent brief template (architecture D)

Fill every section. A section you can't fill is a decision you haven't made yet — make it before
delegating, because the lead will otherwise make it for you, invisibly.

```
You are the LEAD agent for a coupled build. You act as the main session's proxy: you decompose,
delegate bounded links to your own worker agents, verify every worker's output before building on
it, and return a proof-of-completion package. You do judgment-heavy links yourself.

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

## Scope
- Files/dirs you own: <...>
- Out of scope (report, don't touch): <...>

## Workers
Spawn general-purpose agents for bounded links. Model guidance:
- `sonnet` for well-specified edits, test writing, mechanical refactors
- `opus` for links where a wrong choice is expensive to unwind
Verify each worker's output against its sub-brief BEFORE building the next link on it. Their
reports are hypotheses.

## Evidence format (your final message)
1. Per-DoD-criterion: evidence (command + output, file:line, diff summary)
2. What was deliberately deferred, and why
3. Anything out-of-scope you noticed (report only)
4. Worker log: which links were delegated, to which model, and what your check found

## Stop & escalate — do not improvise past these
- The codebase contradicts this brief's assumptions
- A DoD criterion turns out to be unverifiable as written
- You need out-of-scope changes to proceed
- A gate fails twice for the same cause
Stop, state what you found, and wait for instructions.
```

## Notes for the foreman

- Send follow-ups and escalation answers to the SAME lead via SendMessage — a re-brief loses the
  lead's accumulated context, which is most of what you paid Opus for.
- When the package comes back: spot-check one or two criteria independently, then run the repo
  gates yourself. Accept nothing on the package's say-so alone.
