# Typography

## Preferred Families

1. `Avenir Next` — the default for all decks. Understated, geometric,
   professional; reads as designed rather than typed.
2. `Helvetica Neue` — neutral Swiss alternative when Avenir Next is
   unavailable or the material wants something even quieter.
3. `JetBrainsMono Nerd Font` — opt-in only, when the user asks for it or the
   deck is deliberately technical (engineering readouts, code-heavy material).
   Not the default: monospaced faces read blocky in executive decks.
4. `Calibri`, then `Arial` — portability fallbacks when the deck must open
   with correct metrics on machines you don't control.

Use one primary family throughout a deck. Build hierarchy from size, weight,
and color — not from mixing families.

## Portability Warning

Avenir Next and Helvetica Neue are macOS system fonts and are NOT on Windows.
PptxGenJS cannot embed fonts, so a .pptx that leaves this machine gets
silently substituted. For decks shared externally: deliver the PDF render
alongside the .pptx, or build with `Calibri`/`Arial` from the start.

## Verifying a Font Is Installed

Check before generating, not after — presentation applications substitute
missing fonts silently.

```bash
# macOS (system .ttc families + user-installed)
ls /System/Library/Fonts/ | grep -i "avenir next\|helveticaneue"
find ~/Library/Fonts /Library/Fonts -iname "*jetbrainsmono*nerd*" | head -3

# Linux
fc-list | grep -i "avenir\|helvetica\|jetbrainsmono nerd"
```

If the first-choice family returns nothing, move down the preference list and
note the substitution when reporting back.

## Generator Configuration

For PptxGenJS, set the theme once and pass the same face to every text call —
PptxGenJS does not inherit the theme font into `addText`/`addTable` reliably:

```js
const FONT_FACE = "Avenir Next";
pptx.theme = { headFontFace: FONT_FACE, bodyFontFace: FONT_FACE, lang: "en-US" };
// then: slide.addText(..., { fontFace: FONT_FACE, ... })
```

Use the exact installed family name. If using the monospaced option,
`JetBrainsMono Nerd Font` is the proportional-metrics variant and
`JetBrainsMono Nerd Font Mono` is strictly monospaced — prefer the former.

## Type Scale

Use one modular ratio so every tier is a visible step from the next, and make
hierarchy out of size AND weight AND color together — never size alone.
Recommended scale for a 13.33×7.5 in widescreen deck (Major Third, ~1.25,
ported from mcp-deck's scale):

| Tier | Size | Notes |
|---|---|---|
| Kicker / eyebrow | 10–11pt | Bold caps, letter-spaced, `accentPrimary` |
| Source / footer | 8.5–10pt | `textSecondary` |
| Body | 14–18pt | `textPrimary`; bullets ≤ ~10 words |
| Subtitle / section header | 20–24pt | Semibold |
| Slide title | 28–32pt | Bold |
| Hero stat / lead | 44–60pt | One per slide at most |

## Validation

- Render through the target presentation application.
- Check for missing-font warnings, changed line breaks, clipped text, and
  unexpected font substitution.
- If using the monospaced option, recheck dense slides — monospaced text needs
  roughly 20% more box width than a proportional face.

## LibreOffice font discovery

An installed font can still be substituted by LibreOffice's Fontconfig. The renderer
uses the configuration next to a detected `fc-match` installation on macOS when
`FONTCONFIG_FILE` is unset. An explicit environment value wins. Inspect `fonts.txt`
in the render output (when `pdffonts` is installed); it records the actual PDF fonts.
Do not claim font preservation from the PPTX's font names alone.
