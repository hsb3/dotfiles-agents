# Tier cutoff — measuring where the cheap model tier stops being adequate

**Tier here means model tier** (haiku / sonnet / opus), never the org layer. Layer says what
an agent is for; tier says how much judgment is bought for it.

The kit's economics rest on `scout`=haiku and `builder`=sonnet defaults, with opus reserved for
judgment-heavy slices. **That cutoff has never been measured.** The lab that produced this kit
dispatched opus for every model-bearing call it made and never exercised the cheaper tiers, so the
defaults are reasoning, not evidence. This is the protocol that would settle it. Until someone
runs it, treat the cheat-sheet defaults as `[untested]` and keep a strict DoD so an under-powered
worker fails loudly.

The design is the lab's, reduced to one variable: **the dispatch model, and nothing else.**

## Procedure

1. **Pick a real brief.** Never a synthetic exercise — the whole question is about real work.
   Freeze its text; it is the contract for both arms.
2. **Dispatch two arms in parallel**, identical in every respect except `model`. Same agent type,
   same brief text, same owned file list, same gate. Use `isolation: worktree` so both arms write
   without colliding.
3. **Verify both arms the same way** before judging: run the gate yourself on each. An arm that
   fails its gate scores nothing and is recorded as a gate failure, which is itself the cleanest
   possible result.
4. **Judge blind.** Hand both artifacts to a `rubric-panel` run against an anchored rubric, with
   the arms labelled A and B — never "the sonnet one". Each judge scores both. Flag a
   greater-than-1.5 spread as contested rather than averaging it away.
5. **Record the row** (schema below) including token cost per arm, taken from the delegation
   ledger once it records the subagent's own model and usage rather than the parent's.
6. **Repeat across archetypes** until a shape appears. One comparison is an anecdote.

## The archetypes worth covering

Cheapest-to-hardest, because the cutoff is expected to sit somewhere in the middle:

| Archetype | Example | Prediction to test |
|---|---|---|
| Mechanical transform | rename across 30 sites, one codemod | Cheap tier adequate; opus is waste |
| Bounded feature | add a flag, wire it, test it | Cheap tier adequate with a strict DoD |
| Test authoring | write the suite for an existing module | Unknown — test design is judgment-shaped |
| Coupled slice | change a signature and everything it touches | Expected to need opus |
| Underspecified slice | acceptance criteria that need interpretation | Expected to need opus |
| Read-only synthesis | reconcile evidence across many files (scout tiers) | haiku vs sonnet, separate question |

## What to record per comparison

```json
{
  "brief_id": "<slug>", "archetype": "mechanical-transform",
  "arm_a": {"model": "sonnet", "gate": "pass", "score": 4.31, "output_tokens": 18422},
  "arm_b": {"model": "opus",   "gate": "pass", "score": 4.55, "output_tokens": 21107},
  "contested_dimensions": ["error-paths"],
  "verdict": "cheap-adequate | premium-required | inconclusive"
}
```

`verdict` is a judgment call with two mechanical inputs: a gate failure on the cheap arm is
`premium-required` outright, and a score delta inside the panel's own noise band (the largest
same-arm judge spread observed in that run) is `inconclusive`, not a win.

## Reading the result honestly

- **Within-run ranking is the signal; cross-run score levels are not.** Panels differ, and judges
  in a later run dig deeper than judges in an earlier one. Never compare a score from one
  comparison to a score from another and call the difference a finding.
- **Report the cost ratio next to the quality delta.** "Opus scored +0.24 at 1.9× the output
  tokens" is a decision; "opus scored higher" is not.
- **A cheap arm that fails its gate is the most useful outcome available.** It tells the
  strategist exactly where the cutoff is without any judging at all, which is also why every brief
  in this protocol needs a gate that has been proved red.
- **Expect the cutoff to be brief-shaped, not task-shaped.** A well-specified brief with a strict
  DoD moves work down a tier; the same work under a vague brief does not. If cheap arms
  consistently fail on one archetype, check whether the brief was underspecified before blaming
  the tier.

## Then update the doctrine

Replace the `[untested]` tag on the cheat-sheet defaults with the measured claim and its date, or
keep the tag and say plainly that it is still unmeasured. Do not quietly leave a reasoned guess
looking like a finding — the provenance tags exist so a future session can tell the difference.
