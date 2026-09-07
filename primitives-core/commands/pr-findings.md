---
description: Triage a pull request's review findings — read the inline comments, the review and summary bodies, and the gate status, then report what is actionable and what is deferred as pre-existing, with nothing dropped.
argument-hint: "[pr number]"
allowed-tools: Skill, Bash
---

Load the `code-desk:pull-request` skill and drive it. **The procedure lives in the skill** —
which surfaces to read, how to classify a finding, and the shape of the report. Read it
there and follow it; do not restate it here and do not re-derive it from memory.

## What to do

1. Load `code-desk:pull-request`.
2. Target PR: `$1` if a number was given, otherwise the current branch's open PR, resolved
   the way the skill says. If the branch has no open PR, report that and stop — do not open
   one and do not substitute another PR.
3. Run the skill's collection step over **all three** surfaces, then its classification
   rule over every finding it returned.
4. Report in the skill's shape.

## How to report

This runs because a green check hides unaddressed comments, so a report that leads with the
check status has answered the wrong question. Lead with the findings.

Both sets are always present with their counts, including empty ones — a missing
**DEFERRED — pre-existing** section is indistinguishable from a triage that never looked,
which is the exact failure this exists to stop. State it as "none" when it is empty.

Never collapse the result to "CI is green" or "no blockers". Say how many findings were
read, how many are actionable, and name each deferred one with its location and the
one-line reason it is out of this PR's scope. If a finding was ambiguous and you called it
actionable by default, say so rather than presenting the call as clean.

Stop after reporting. Fix the actionable set only if the person asks in the same turn, or
if the ask that invoked this was already "address the review feedback" — and if you do,
report what you pushed and re-read afterwards, because the reviewers run again on the new
commit.
