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

A report that leads with the check status has answered the wrong question — this runs
because a green check hides unaddressed comments. Lead with the findings, in the shape the
skill's report step fixes.
