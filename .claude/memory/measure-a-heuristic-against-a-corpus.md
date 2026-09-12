---
name: measure-a-heuristic-against-a-corpus
description: A text-matching heuristic (linter, scanner, advisory hook) can pass every unit test and still be mostly wrong — replay it over git history and score it against a stdlib parser before shipping
metadata:
  node_type: memory
  type: project
---

Unit tests prove a heuristic fires on the cases someone thought of. They say nothing about its
**precision on real input**, and for an advisory that nobody is forced to obey, precision is the
whole currency: one that cries wolf gets ignored, which costs more than the findings it would
have surfaced.

Measured on `comment-hygiene-gate` (2026-08-11), which arrived with 7 passing tests and a clean
self-review:

- Replayed over the last 40 commits, it would have fired on **25 of them**, with **73 of 75
  findings in markdown** — flagging backlog cards and `HANDOFF.md`, the exact places history is
  supposed to live. It inverted its own thesis.
- Scored against Python's `tokenize` on the 156-file Python corpus, real precision was **79%**,
  and **every** finding in an HTML file was wrong (CSS hex colours read as issue refs).

Both defects came from the numbers. Neither was visible in the code or the tests.

**How to apply:** before shipping any scanner, two cheap passes, each a throwaway script — no
fixtures, no framework.

1. **Replay over history.** Import the module, run its scan function over
   `git diff <sha>^ <sha>` for the last ~40 commits, and count how often it would fire and on
   what file types. A concentration in one extension is the tell.
2. **Score against an oracle.** Where the stdlib already parses the format authoritatively, use
   it as ground truth rather than eyeballing samples — `tokenize` for Python comments,
   `ast`, `json`, `csv`, `email`. Diff the heuristic's hits against the oracle's and read the
   misses one by one.

Report precision as a number, not as "looks clean." Then mark the residue with a `ponytail:`
comment naming the measured rate, so the next session inherits the size of the ceiling rather
than a vague warning.
