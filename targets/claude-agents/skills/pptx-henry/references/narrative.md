# Narrative and Slide Composition

Distilled from the mcp-deck playbook (Henry's HTML deck server). These rules
are about what a slide *says* and how a deck *argues* — they apply to any
render target.

## Design Principles

1. **Action titles.** A content slide's title is the takeaway as a full
   sentence, not a topic label. "Revenue grew 18% on enterprise wins" beats
   "Revenue". The body exists to prove the title.
2. **One message per slide.** If a slide has two messages, split it.
3. **BLUF.** Lead with the conclusion. An exec deck opens title →
   executive summary, then evidence, then the ask.
4. **Cite sources.** Put a source footer on any slide with data.
5. **Be scannable.** ≤6 bullets, ≤~10 words each. Prefer numbers and short
   phrases over sentences. Spotlight the one number that matters with
   `textAccent` or bold.
6. **Show, don't list.** Reach for a framework layout (2×2 matrix, timeline,
   numbered steps, stat callouts) over yet another bullet list when the
   content has structure. Short enumerable facts across options → a table,
   not parallel bullet columns.
7. **Numbers → chart, not bullets.** When a slide is a series of numbers
   (counts, trends, share-of-total), draw a bar/line/donut chart in theme
   data-series colors instead of writing the numbers as text.

## Slide Vocabulary (intent → layout)

| You need to… | Layout pattern |
|---|---|
| Open the deck | Title: light canvas, kicker line, large title, supporting card |
| Mark a new part | Section divider: `surfaceInverse` background (light themes only) |
| State the whole story up front | Executive summary: stat callouts + narrative bullets |
| Make a body argument | Action-title slide: takeaway-sentence title, top-aligned proof |
| Headline several metrics | KPI row: stat cards with value, label, and delta |
| Make one number the hero | Big stat: 48pt+ number, small label, one supporting line |
| Compare two options | Two columns with a verdict row or callout |
| Prioritize on two axes | 2×2 matrix with axis labels in the gutters |
| Show a schedule or history | Timeline: dots on a line, label/title/detail per item |
| Explain a method | Numbered step columns of equal width |
| Land a decisive point | Takeaway: one hero callout, generous whitespace |

## Deck Recipes (scenario → sequence)

- **Executive readout:** title → executive summary → action-title slides
  (evidence) → KPI row or chart → takeaway (the ask).
- **Strategy recommendation:** title → section (situation) → action-title
  slides → 2×2 matrix (options) → roadmap → takeaway.
- **Status update:** title → KPI row (health) → action-title (progress) →
  timeline (milestones) → action-title (risks) → takeaway.
- **Data story:** title → big stat → chart → action-title (implication) →
  takeaway.

## Composition Pitfalls

- **Don't stack a narrow callout above a left-pinned bullet list** — the pair
  reads as two orphaned boxes with the right half of the slide dead. Put the
  hero action in one column and the follow-on items in the other, or fold
  everything into one callout.
- **Don't leave the lower third empty** under a title plus one short
  horizontal element (a step row, KPI row, or timeline). Vertically center
  the body content in the space below the title.
- **Don't let footers collide with content** — reserve a footer band and keep
  body content above it.
- **Fix overflow by trimming or splitting first**; shrink type only as a last
  resort, and never below ~70% of the intended size.
