---
name: dev-focus
description: Keep a work session scoped and on-track — a mid-session focus check that flags drift from the original task, and a scope triage that sorts a task list into MUST/DEFER/CUT. Use when the user says "focus check", "are we still on track", "am I drifting", "scope this", "scope review", "run the scope hammer", "what should we cut", or "MUST/DEFER/CUT", or whenever a session has sprawled past its original goal and needs re-anchoring before more work lands.
---

# Dev Focus

Two lightweight session-discipline moves for keeping a work session anchored to what it set out to do. Reach for **focus check** mid-session to detect drift, and **scope review** whenever a task list needs pruning to what actually matters this iteration. Both produce a short, scannable output — not a wall of text.

## Focus check — are we on track or drifting?

Use mid-session to re-anchor. Assess the session against its original goal:

1. **What was the original task?** Restate it in one sentence.
2. **What have we actually done?** List the completed steps.
3. **Are we still on track?** Flag any drift from the original scope.
4. **What's left?** List the remaining steps.
5. **Should anything be deferred?** Identify items that can wait.

Output in this format:

```
Task: [one sentence]
Done: [bullet list]
Remaining: [bullet list]
Drift: [none / description of drift]
Defer: [none / items to defer]
```

## Scope review — the scope hammer

Use to sort a set of tasks/features into what to do now versus later versus never. Take the in-scope items from the conversation, task list, or the user's input, and categorize each:

- **MUST** — doesn't work without it; blocks the core goal.
- **DEFER** — valuable but not required for this iteration.
- **CUT** — a nice-to-have disguised as a requirement, or something a simpler approach solves.

**Default bias: move things to DEFER or CUT.** Make the user argue items back into MUST rather than starting everything as essential.

Output in this format:

```
## Scope Review

### MUST (do now)
- [item] — [why it's essential]

### DEFER (next iteration)
- [item] — [why it can wait]

### CUT (remove)
- [item] — [why it's not needed]

### Flags
- [red flags: everything marked must, missing criteria, hidden dependencies]
```

Challenge the scope whenever:

- Everything lands in MUST (no real prioritization happened).
- An item lacks clear acceptance criteria.
- Total effort exceeds what fits in one focused session.
- Items depend on infrastructure that isn't built yet.

Done when the focus check names any drift plainly and the scope review leaves every item in
exactly one bucket with a one-line reason.
