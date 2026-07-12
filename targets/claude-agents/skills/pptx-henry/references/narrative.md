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

## Explanatory Register (Henry's confirmed preference)

Validated 2026-07-10 on the HeadCase north-star reset briefing: a terse
29-slide cut was rejected as "too terse/cryptic"; its explanatory 30-slide
rebuild was rated "excellent". The scannability rules above govern tables,
cards, and bullet fragments — they do NOT mean the deck reads like shorthand.
For a comprehensive or decision briefing:

- **More slides beats denser slides.** When Henry asks for comprehensive,
  expand the slide count rather than compressing the prose.
- **Every content slide opens with a lede**: 1-3 full sentences under the
  title saying what the slide means and why it matters, BEFORE any table,
  chart, or card grid. The title carries the claim; the lede carries the
  context.
- **Spell out references.** An issue/ticket number always gets its title
  inline ("#167 — agent team builds CMS analytic data marts"), never a bare
  number the reader must look up.
- **Define jargon in place** on first use (internal codenames, acronyms,
  project shorthand). Do not assume the reader carries context between slides.
- **Callouts, ledes, and takeaway lines are complete sentences**; fragments
  stay inside tables and stat cards where structure explains them.
- **Orientation up front pays**: an early slide mapping where the underlying
  artifacts live (and how the material was produced) earns trust for
  everything after it.

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
- **Guard against the two-line-title collision.** If the lede/body sits at a
  fixed Y below the title box, a title that wraps to two lines lands on top of
  it — a systemic defect that hit 11 of 30 slides on first render (2026-07-10).
  On LAYOUT_WIDE at 26pt bold Avenir Next across a ~12in text box, keep titles
  to **~66 characters or fewer** to guarantee a single line (wrapping was
  observed from ~70 characters up). Either budget titles to that length during
  content writing, or anchor the lede to the title's rendered height.
