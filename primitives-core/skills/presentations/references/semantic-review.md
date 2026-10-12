# Semantic review

Render and package checks prove a deck opens and looks right. They cannot show that it does
its job for its audience. This file adds a contract written before authoring and a review
run against it after the render checks pass.

## Intent contract

Write it before building any slide. A short outline or the speaker notes is enough. No extra
tool, no schema, no approval loop. For a simple edit, a one-line contract is enough.

Whole artifact:

- Purpose: why the deck exists.
- Audience: what they hold at the start and what they must hold at the end.
- Ask: the decision or action the deck requests, stated against the original goal,
  including any hard requirements that goal carried.

Each slide:

- Purpose and the one takeaway.
- Input to output: what the audience must already hold, and what they hold after.

Each meaningful component (chart, table, diagram, quote, image):

- Its job on the slide.
- Its evidence source.

## Semantic review

Run it as its own step, separate from render and package QA, against the contract. A green
render or a valid package never implies the goal is achieved. This is a reasoned check, not a
measurement of human comprehension. A consequential deck gets the review from an independent
reviewer: someone or some agent that did not author the deck.

1. Trace the ask. Follow the recommendation or closing action back to the original goal and
   its evidence. Flag scope substitution: an answer to a narrower question than the one asked,
   or an option that does not meet the stated hard requirements (for example, "act now" when
   no candidate satisfied every requirement).
2. Sequence and coverage. Each slide's prerequisites appear before it. Nothing
   decision-relevant is omitted: a test or comparison that exercises only part of a
   multi-part requirement is a defect, not a summary.
3. Deletion test. For each component, ask what audience understanding breaks if it is removed.
   If nothing breaks, it is decorative and goes.
4. Titles, claims and cover. Every title is supported by its slide's content, and every
   claim and table cell by the evidence source the contract names; an unsourced claim is a
   finding. The cover names the
   topic, purpose and scope before it states the bottom line; the bottom line then sits in a
   cover decision strip or on the first content slide, never as the cover title.

Record findings as rows, then give a verdict.

| Slide / component | Observed defect | Correction |
|---|---|---|
| 1 | Opens on a recommendation before naming topic and purpose | Title the topic and purpose; carry the recommendation as a decision strip or the first content slide |
| 6 test | Exercises only one part of a four-part requirement | Cover every part, or state the gap |
| 9 close | "Pilot now" though no option met every hard requirement | Restate the ask to match the evidence |

Verdict: accept or reject the deck against the contract. Reject while any row is open.
Fix, rerender, and review again.
