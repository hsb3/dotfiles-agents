_Advisor board readout playbook. Shared machinery: `references/comm-package-standard.md`. Worked example: `sample.deck.js` (the 2026-06-12 advisor-board overview, 13 slides, actuarial-signal theme)._

# Advisor board readout

Monthly or as-called, audience advisors / board. **The one job: show progress against the thesis
and make the ask of the board** - the open questions are commercial, not technical, which is
exactly what the board is for. Toolchain pptx-henry (NOT deck-builder); theme `actuarial-signal`;
`.pptx` + `.pdf` with a confidential footer; audio optional. Folder slug `-advisor-overview`.

> Invoke the `pptx-henry` skill for palette, tokens, typography, and visual QA. `sample.deck.js`
> is the gold reference for layout (cards, ledger columns, 2x2 matrix, status chips); note its
> `require` of the pptx-henry `theme-tokens.js` - keep that pattern.

## The one rule

**End on the ask; everything before it earns the right to ask.** This is an external, peer-to-peer
artifact (actuary to actuary, CFO to CFO). It is honest about what is proven vs in-build, drops
internal jargon and unexplained issue numbers, carries a "Confidential" footer, and commits to no
roadmap dates. The board's value is introductions, packaging / pricing, and sequencing - the deck
exists to surface those questions sharply.

## Deck structure (the endorsed order)

~13 slides, two acts. `sample.deck.js` is the reference layout.

| # | Slide | Content |
| --- | --- | --- |
| 1 | Title | The product in one sentence; "what we built, where it stands, the opportunity it opens" |
| 2 | Executive summary | Working engine today, platform business next; 3 stat cards |
| 3 | The problem | The three-ledger gap (true / transmitted / paid) and the regulatory clock on unfound dollars |
| 4 | What we built | Ingest to recompute to reconcile to verdicts; evidence-grade; multi-tenant + dual delivery |
| 5 | The wedge market | Who we sell first, the channel multiplier, the founder edge |
| 6 | Commercial motion | Scan (land) to recovery (convert) to recurring (keep) |
| 7 | Divider | "The expansion opportunity" - the core audit is a beachhead, not the business |
| 8 | Gaps become modules | Table: ledger gap to what it means to add-on module to revenue shape |
| 9 | Module portfolio 2x2 | Sellable-now vs needs-build, by one-time vs recurring |
| 10 | The services layer | Services attach to every module the audit opens |
| 11 | Why it sticks | Defensibility (evidence/IP boundary) + stickiness (sub-ledger under the accrual) |
| 12 | Where we are now | Status rows with chips: DONE / IN MOTION / IN BUILD |
| 13 | The ask | Introductions; packaging + pricing; module sequencing |

Act 1 (1-6) is the business as it stands; act 2 (7-13) is the expansion case and the ask. Drop
or merge expansion slides for a pure status readout; keep slide 12 (status) and 13 (ask).

## Gather

- Sources are the durable docs, not live counts: the project charter (precedence) and the product
  thesis - cite both in the footer.
- Status (slide 12) reconciled against the handoff: what is genuinely done vs in-build.
- Regulatory / domain claims (deadlines, ledger definitions) verified against the domain reference
  - this is external; do not paraphrase a regulation loosely.
- The ask (slide 13) is the deliverable - decide the three board questions before authoring.

## Voice deltas (beyond the baseline)

- External and peer-to-peer; no internal issue numbers on slides unless explained in plain terms.
- Status chips carry the honesty: IN BUILD means in build, not done; never imply certification.
- Confidential footer on every content slide; sources footer cites charter + product thesis.
- Module portfolio / sequencing is explicitly directional - "not a roadmap commitment."
