---
name: reproduce-before-fixing-a-card
description: "A board card is a filer's inference, not a measurement — reproduce the reported behaviour live before building the fix"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9d591bf7-65f7-4cdb-b70d-05786a343b87
  modified: 2026-08-17T21:06:06.722Z
---

Before building anything from a tracker card, re-run the card's own repro against the
current tree and the live system. Two distinct failures showed up in one session
(2026-08-17):

- **The defect was already fixed.** DFA-214 described `manager.md`'s unquoted description;
  it had been quoted weeks earlier in #298 and was correct on `dev`, on `main`, and in the
  installed plugin. Only the card's *second* half (the missing gate) was real work.
- **The card's technical claims were wrong.** DFA-245's four API defects were reproduced
  against a scratch project and four claims did not hold — a definition-row `DELETE`
  returns 200 not 400, a colour `PUT` does not cascade (a rename does), `PATCH /task/{id}`
  is a bare 404 not a silent no-op.

Related: **a card marked done on a partial fix regenerates itself.** DFA-222 closed having
added only an env override, leaving the broken default in place; the same defect was then
filed twice more (DFA-228, DFA-242) from two other projects.

**Why:** field-observation cards record what the filer *inferred* from a symptom. Building
straight from one either redoes finished work or writes the inference into documentation as
fact, where it outlives the card. The board/GitHub two-way mirror ([[DFA-226]], still open)
makes staleness routine here, not exceptional.

**How to apply:** run the repro first; if it does not reproduce, say so on the card and
work out what part is genuinely outstanding rather than closing or re-fixing blindly. When
a card asserts an API contract, measure it — on a throwaway project when the operation is
destructive — and put the measurement in the docs, with the card's corrections recorded in
a comment. See [[testing-means-real-proof]] and
[[feedback-verify-state-before-staging-decisions]].
