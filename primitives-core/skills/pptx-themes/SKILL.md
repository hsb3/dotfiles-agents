---
name: pptx-themes
description: >-
  Create, edit, and review PowerPoint presentations using a curated set of approved color
  palettes, semantic theme tokens, monospaced typography, and a render/visual-QA workflow. Use
  for one-off or external decks, slides, presentations, and .pptx tasks, and whenever colors,
  fonts, or a theme must be chosen - it overrides the generic pptx skill's palette and font
  suggestions. Not for the recurring communication deliverables (morning briefing, end-of-day
  wrap-up, weekly planning briefing, board readout, client overview): those go to the comms
  skill, which calls this one for the deck itself.
---

# PPTX Themes

Create presentation files using the standard PPTX production workflow plus the
rules in this skill. Where this skill and the base skill disagree on colors or
fonts, this skill wins.

## Prerequisites

The render/QA script needs, per platform:

- `pdftoppm` (poppler) — macOS: `brew install poppler`; Debian/Ubuntu: `apt-get install poppler-utils`
- LibreOffice (`soffice`) or Microsoft PowerPoint (macOS) for PDF conversion —
  `scripts/render-pptx.sh` probes for whichever is present and says what is missing.

## Workflow

1. Read the base PPTX skill if present — check `~/.claude/skills/pptx/SKILL.md`,
   then `~/.agents/skills/pptx/SKILL.md` — and its relevant creation
   (`pptxgenjs.md`) or editing (`editing.md`) guide. Ignore its "Color
   Palettes" and "Typography" font-pairing tables — those are replaced by this
   skill's resources. If the base skill is absent, proceed with this skill's
   resources alone: build with PptxGenJS and QA with the bundled render
   script.
2. Read [references/narrative.md](references/narrative.md) before outlining
   slide content — action titles, one message per slide, deck recipes.
3. Read [references/color-palettes.md](references/color-palettes.md) before
   choosing or assigning colors.
4. Read [references/typography.md](references/typography.md) before configuring
   presentation fonts, and verify the chosen font is installed.
5. Inspect any existing deck, generator, template, and theme definitions before
   editing.
6. Build the deck consuming themes from
   [assets/theme-tokens.js](assets/theme-tokens.js) — semantic roles only,
   never raw hex in layout code. Token values are bare six-digit hex
   (no `#` prefix), exactly what PptxGenJS expects.
7. Render with [scripts/render-pptx.sh](scripts/render-pptx.sh) and inspect the
   affected slides as images.
8. Fix discovered issues and render again before reporting completion.

When the deliverable is an HTML or PDF briefing rather than a .pptx file,
prefer a dedicated deck-builder MCP server over this skill.

## Themes

Palettes live in `assets/theme-tokens.js` (run `node assets/theme-tokens.js`
to list them). Pick by subject matter — the selection table is in
[references/color-palettes.md](references/color-palettes.md). When the user
names no theme, choose one and say which you chose. Do not use the palettes
packaged with the base pptx skill.

```js
const { THEMES } = require("/path/to/pptx-themes/assets/theme-tokens.js");
const C = THEMES["clinical-intelligence"];
```

## Page Backgrounds

- Use a light `canvas` background for title, agenda, content, data,
  recommendation, and conclusion pages.
- Use a dark `surfaceInverse` page background only for an explicit section
  divider.
- Never use a dark page background for the opening title or main page.
- Exception: a theme flagged `dark: true` (currently `midnight`) uses its dark
  canvas on every page by design; the light-title rule applies to light themes
  only. In dark themes, dividers also stay on the dark canvas (accent numeral +
  `surfaceElevated` band) — never a full light `surfaceInverse` page.
- Dark panels and cards may appear on light pages when they improve hierarchy.
- Make section-divider status explicit in code instead of inferring it from
  slide position.

## Color Usage

- Consume semantic roles rather than palette-specific names or raw hex values.
- Keep palette definitions separate from slide layout code.
- Use data-series tokens in declared order so colors stay consistent across
  every chart in a deck.
- Check text and icon contrast after rendering, particularly on inverse panels
  and colored callouts.

## Typography

- Default to `Avenir Next`; fall back per
  [references/typography.md](references/typography.md). Monospaced faces are
  opt-in for deliberately technical decks only.
- Pass the same `fontFace` to every text call — PptxGenJS does not reliably
  inherit the theme font.
- One family per deck; hierarchy comes from size, weight, and color together.
- For decks shared beyond this machine, deliver the PDF render alongside the
  .pptx or build with `Calibri`/`Arial` — PptxGenJS cannot embed fonts.

## Rendering and QA

Render with the bundled script — it prefers headless LibreOffice and falls
back to driving Microsoft PowerPoint on macOS:

```bash
scripts/render-pptx.sh output.pptx /tmp/deck-qa
```

- Treat rendering as required, not optional. The first render is almost never
  correct; QA is a bug hunt, not a confirmation step.
- Inspect the title, every distinct layout, dense data slides, and the final
  page.
- Check overflow, clipping, wrapping, alignment, margins, contrast, and
  accidental dark page backgrounds.
- Check for visible font substitution (a proportional face where a monospaced
  one was requested is the telltale).
- Confirm that title and main pages use light backgrounds.
- Perform at least one fix-and-verify cycle before reporting completion.

## Resources

- `assets/theme-tokens.js`: executable palette source — themes, token
  contract, validation, CLI listing.
- `references/narrative.md`: action titles, slide vocabulary, deck recipes,
  composition pitfalls.
- `references/color-palettes.md`: semantic token contract, palette selection
  table, rules for adding palettes.
- `references/typography.md`: font preferences, install checks, generator
  configuration.
- `scripts/render-pptx.sh`: .pptx → PDF → per-slide JPEGs for visual QA.
- `scripts/build-theme-sampler.js`: 3-slide sampler deck exercising every token
  of one theme — vet a new or tuned palette with
  `NODE_PATH=<dir-with-node_modules> node scripts/build-theme-sampler.js <theme> [outdir]`,
  then render it with `scripts/render-pptx.sh`.

## Found an error?

`base/` is vendored verbatim and must never be hand-edited — an edit there registers as
upstream drift and fails the vendored-drift gate. Corrections go here in the authored
layer, with evidence; upstream-worthy ones belong on
<https://github.com/anthropics/skills/issues>.
