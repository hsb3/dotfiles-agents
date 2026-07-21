# deep-research

Run a deep, multi-source, fact-checked research investigation that ends in a cited
report — not a single web lookup. The workflow scopes the question, decomposes it into
~5 distinct search angles, fans out searches (parallel subagents where the harness offers
them, serial otherwise), dedupes and tiers sources, extracts falsifiable claims, then
adversarially tries to refute every load-bearing claim before anything is asserted.

## When it triggers

Use it when the user asks to "research X", "do a deep dive", or wants a multi-source,
verified answer to a substantive question. The skill enforces scope discipline first
(underspecified questions get 2-3 clarifying questions with recommended defaults), and
the final report carries per-claim citations, confidence labels
(verified / contested / unverified / refuted), and a negative-findings section — what
did NOT hold up stays on the record.

## Install

```
claude plugin install deep-research@dotfiles-agents
```

Standalone-only — it does not ship inside any bundle. Uses the harness's web-search and
fetch tools; degrades gracefully when subagents are unavailable.
