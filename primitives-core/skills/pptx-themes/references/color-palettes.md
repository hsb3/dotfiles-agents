# Semantic Color Palettes

Use semantic roles in slide code. Palette implementations may change without
requiring layout changes.

The executable source of truth is [../assets/theme-tokens.js](../assets/theme-tokens.js).
It exports `THEMES` (every palette, fully validated), `REQUIRED_SEMANTIC_TOKENS`,
and `validateTheme`. Require it from a deck generator, or copy it into the
project when the deck must be self-contained:

```js
const { THEMES } = require("/path/to/pptx-themes/assets/theme-tokens.js");
const C = THEMES["actuarial-signal"];
slide.background = { color: C.canvas };
```

List themes or dump one palette from the command line:

```bash
node assets/theme-tokens.js
node assets/theme-tokens.js clinical-intelligence
```

## Required Tokens

### Surfaces

- `canvas`: default light page background
- `surface`: cards and primary panels
- `surfaceElevated`: secondary or emphasized light panels
- `surfaceInverse`: dark section dividers and inverse panels

### Text

- `textPrimary`: primary text on light surfaces
- `textSecondary`: supporting text on light surfaces
- `textInverse`: text on inverse or strongly colored surfaces
- `textAccent`: emphasized or linked text

### Structure

- `border`: standard borders
- `borderStrong`: emphasized borders and inverse-panel outlines
- `gridline`: chart grids and low-emphasis separators

### Brand

- `accentPrimary`: dominant accent
- `accentSecondary`: secondary accent
- `accentTertiary`: tertiary accent
- `accentSoft`: low-emphasis accent background

### Data

- `dataPrimary`, `dataSecondary`, `dataTertiary`, `dataQuaternary`: series order
- `dataPositive`, `dataNegative`: directional values
- `dataNeutral`: de-emphasized series
- `dataTrack`: bar/progress track backgrounds

### Status

- `positive`, `caution`, `negative`, `informational`

### Effects

- `shadow`

## Rules

1. Supply every required token as a six-digit hexadecimal color.
2. Keep raw palette values in the theme module, never inline in layout code.
3. Do not use hue names such as `orange`, `teal`, or `blue` in slide layouts.
4. Reserve `surfaceInverse` as a page background for explicit section dividers.
5. Use light `canvas` for title and main pages.
6. Use data-series tokens in declared order so series colors stay consistent
   across every chart in a deck.
7. Test all text, chart, and status combinations in rendered output.

## Choosing a Palette

| Theme key | Feel | Use for |
|---|---|---|
| `carbon-white` | Neutral, systems-grade (IBM Carbon) | Engineering readouts, platform briefings, technical documentation decks |
| `clinical-intelligence` | Disciplined blue + healthcare teal + restrained violet | Analytics, technology-enabled services, clinical performance |
| `human-outcomes` | Institutional green + warm coral + muted indigo | Operating-model transformation, patient experience, facilitation, human-centered strategy |
| `actuarial-signal` | Slate blue + controlled bronze + technical teal | Pricing, reserving, forecasting, financial risk, executive actuarial communication |
| `boardroom` | Crisp white + deep navy (McKinsey/BCG look) | General executive and consulting decks; the default when no domain palette fits better |
| `ivory` | Warm paper + consulting blue | Print-friendly readouts meant to be read on paper or shared as PDF |
| `midnight` | Deep navy + warm gold — premium dark | Deliberately dark, high-stakes decks. The only approved dark theme |

`boardroom`, `ivory`, and `midnight` are ported from a curated HTML deck server
(its three curated HTML themes); core values are verbatim from its `deck.css`,
data-series ramps and soft tones were derived to fill the token contract.

When the user names no theme, pick by subject matter using the table and state
the choice when reporting back. These seven are the approved set — do not fall
back to the palettes packaged with the base pptx skill.

### Dark-theme exception

A theme with `dark: true` (currently only `midnight`) uses its dark `canvas`
on every page, including the title — the light-title-page rule applies only to
light themes. In a dark theme `surfaceInverse` is a *light* contrast surface
and `textInverse` is dark text for use on it and on strong accent fills.
Two consequences, verified by sampler render:

- **Never use `surfaceInverse` as a page background in a dark theme** — a full
  light page mid-deck reads as a flash-bang. Mark section dividers with an
  oversized `accentPrimary` numeral and a `surfaceElevated` band instead;
  reserve `surfaceInverse` for small high-contrast panels and chips.
- Choose a dark theme only when the user asks for one or the occasion clearly
  calls for premium-dark styling.

## Adding a Palette

Add a new entry to `assets/theme-tokens.js` with every required token plus
`name`, `source`, and `useFor`. The module self-validates on load, so a missing
or malformed token fails immediately. Then add a row to the table above.

Vet the result before using it in a real deck: `NODE_PATH=<dir-with-node_modules>
node scripts/build-theme-sampler.js <theme> [outdir]` builds a 3-slide sampler that
exercises every semantic token, and `scripts/render-pptx.sh` turns it into images to
look at.
