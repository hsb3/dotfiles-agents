---
name: comment-hygiene
description: Strip history and commentary out of source comments before work lands — harvest the reasoning onto its tracker item, keep only what a reader would break something without. Use before a PR or a milestone commit, when a file's comments read as narrative, or when invoked by layer-cycle's refine phase.
---

# Comment hygiene

History and commentary belong on the related task, not in the code. A
comment is read at 3am by someone fixing something else; one that narrates
how the code came to be costs that reader a paragraph and pays nothing.

Writing scratch commentary while building is expected. This is the cleanup
step that runs before the work lands, not a ban on thinking in comments.

## The keep test

A comment survives iff a competent reader would break something without it:

- non-obvious external behavior (an endpoint that returns 200 on failure)
- ordering or precedence not visible at the call site
- why the obvious alternative is wrong
- an invariant a future edit would violate

Everything else is history.

## The cut list

Issue and board refs (`PROJ-412`, "board card 7", a bare issue number),
dates, attributions ("owner report 2026-08-10", "per the review call"), CI
run ids, "this used to X", "the first version of this", investigation
narratives, and anything restating what the line below plainly says.

## Process

1. **Harvest before you cut.** The history is not worthless, it is in the
   wrong place. Append it to the related tracker item (board task, issue,
   or the repo's decisions log) BEFORE deleting it. Never delete
   undocumented rationale outright — with no tracker item, open one.
2. **Rewrite, don't just delete.** A 16-line narrative usually holds one
   real constraint. State it in present tense as a fact about the system,
   not as the story of discovering it.
3. Re-read the diff. Done when every surviving comment passes the keep test.

Before:

```py
# We originally used one global lock here (PROJ-412). During the 2026-08-10
# incident we found the per-request path could re-enter under load, and CI
# run 31458505007 caught it as a flake. Owner ruled we move to per-account.
```

After:

```py
# Per-account, not global: the request path re-enters under load.
```

## When it runs

Before a PR or a milestone commit; invoked by `layer-cycle`'s refine phase
alongside `deletion-pass`. Division of labor: `deletion-pass` cuts CODE that
cannot name its commitment, this cuts PROSE that cannot. They compose.

## Guardrails

- Never change behavior. Comments-only diffs, so the pass reviews in one read.
- Keep `ponytail:` markers verbatim — each names a deliberate ceiling and its
  upgrade path, which is an invariant, not history.
- Keep a lint suppression's justification. An unexplained `biome-ignore` or
  `eslint-disable` is worse than the comment it replaced.
