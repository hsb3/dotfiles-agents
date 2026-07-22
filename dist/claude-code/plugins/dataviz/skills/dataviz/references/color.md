# Color system

Color in a chart is an **encoding channel**, not decoration. Match the channel to the data
type, keep contrast legible, keep it colorblind-safe, and handle both light and dark backgrounds.

The default values live in [palette.json](palette.json) — a brand-neutral starting point you can
consume directly or rebrand (see "Swap for your brand" below).

## Match palette type to data type

| Data type | Palette type | Rule |
|---|---|---|
| Categorical / nominal (unordered groups) | **Categorical** — distinct hues | Distinguish by HUE. Cap at ~7 before the mapping becomes unreadable; beyond that, group into "Other", small-multiple, or direct-label. Assign in a fixed order and keep a series' color stable across every chart in the set. |
| Sequential / ordered magnitude (0 -> high) | **Sequential** — one hue, light-to-dark | Encode magnitude with LIGHTNESS, not hue. Light = low, dark = high (on a light page). Perceptually ordered so equal data steps look like equal visual steps. |
| Diverging (deviation from a meaningful midpoint) | **Diverging** — two hues around a neutral center | Anchor the neutral midpoint at the meaningful zero (not the data median). Two hues meet at a light neutral; darkness grows toward each extreme. |
| Meaning (good / bad / warn / info) | **Semantic** | Reserve for meaning; never decorate with red/green. Do not let a category accidentally inherit a semantic color unless the category IS that meaning. |

**The cardinal mismatch to avoid:** a rainbow/spectral ramp on quantitative data (hue is not
ordered — see the anti-pattern table in `chart-selection.md`), or unordered categorical hues on
ordered data.

## The default palette

`palette.json` ships these groups, all six-digit hex:

- `categorical.light` / `categorical.dark` — up to 8 series colors, one set per background.
- `sequential.blue` / `sequential.teal` — 7-step light-to-dark ramps.
- `diverging.blueOrange` — 9-step ramp; blue-orange is colorblind-safer than red-green.
- `semantic.light` / `semantic.dark` — positive / negative / caution / informational / neutral.
- `theme.light` / `theme.dark` — background, panel, gridline, axis, textPrimary, textSecondary.

### Categorical ordering and the thin-mark caveat

`categorical.light` is ordered so the highest-contrast, most-distinct hues come first — assign in
order and stop when you run out of series. The order is deliberate: on a **white** background the
first four (blue `#0072B2`, vermillion `#D55E00`, bluish-green `#009E73`, purple `#CC79A7`) each
clear the 3:1 non-text-contrast bar for thin marks; the later light hues (orange `#E69F00`, sky
blue `#56B4E9`, yellow `#F0E442`) do **not** — they are legible as large fills (bars, areas,
filled points) but a 1px line or a small dot in those hues washes out on white. When you need
those later hues for thin marks, thicken the stroke, add a darker outline, or switch to the dark
theme. Every color in `categorical.dark` clears 3:1 against the dark background.

## Contrast and colorblind-safety requirements

These are requirements, not suggestions:

1. **Text on its background >= 4.5:1** (WCAG AA for normal text): axis tick labels, data labels,
   legends, tooltip text, KPI numbers. Large display numbers (>=24px bold) may use 3:1.
2. **Meaningful non-text marks >= 3:1** against their background: a line, a bar edge, a small
   point, a focus outline. A hairline that only clears 1.5:1 is decoration, not data.
3. **Gridlines stay BELOW the data** — deliberately low contrast (roughly 1.2-1.5:1 on the
   background) so they guide without competing. This is the one place low contrast is correct.
4. **Never encode by hue alone.** ~8% of men have a color vision deficiency. Pair color with a
   second channel: direct labels, distinct dash patterns or markers for lines, position/order,
   or text. A red/green "up/down" must also differ in shape or sign.
5. **Prefer blue-orange over red-green** for any two-way distinction (diverging ramps, gain/loss)
   — it survives the common deuteranopia/protanopia far better.
6. **Sanity-check, don't assume.** Verify contrast with the WCAG relative-luminance formula and
   preview a CVD simulation before shipping.

### How the shipped values were checked

The default palette's contrast claims were computed with the **WCAG 2.x relative-luminance +
contrast-ratio formula** (linearized sRGB channels; `L = 0.2126R + 0.7152G + 0.0722B`;
`ratio = (L_light + 0.05) / (L_dark + 0.05)`). Verified results:

- Both themes: `textPrimary` and `textSecondary` clear 4.5:1 on both `background` and `panel`;
  `axis` clears the 3:1 UI bar; `gridline` sits intentionally low (~1.2-1.4:1).
- `semantic.light` all clear 4.5:1 as text on white; `semantic.dark` all clear 4.5:1 as text on
  the dark background.
- Sequential ramps are strictly monotonic in luminance; each diverging half is monotonic away
  from the neutral midpoint.
- Categorical thin-mark caveat above is the measured exception, not an oversight.

If you change any value, re-run the same computation — a rebrand invalidates every number here.

## Light and dark themes

Do not just invert. A chart must be authored for the surface it lands on:

- **Pick the theme block that matches the destination.** Light page -> `theme.light` +
  `categorical.light` + `semantic.light`. Dark page/app -> the `dark` variants.
- **Backgrounds are near-neutral, never pure-saturated.** `theme.light.background` is white;
  `theme.dark.background` is a very dark desaturated navy, not pure black (pure black + bright
  marks vibrate).
- **Dark theme lightens marks and semantics.** Series and semantic colors are lifted so they
  clear contrast on the dark background; that is why `categorical.dark` and `semantic.dark` exist
  as separate sets rather than reusing the light values.
- **Sequential/diverging direction is unchanged, but "dark = high" reads inverted on a dark
  page** — state the legend explicitly, or use a ramp that runs from the background color outward
  so "more ink" still means "more".
- **If the chart must work on an unknown background** (embedded, exported, printed): give it its
  OWN opaque panel (`theme.*.panel`) with a border, rather than betting on the host background.
  This is the safest default for exported images.

## Swap for your brand

The palette is intentionally brand-neutral. To rebrand:

1. **Replace the accent/categorical hues** with your brand colors. Keep the SAME structure and
   the same array lengths in `palette.json`; only the values change.
2. **Keep the neutral scaffold** (`theme.*` background / panel / gridline / axis / text) unless
   your brand system mandates specific surface colors — neutral scaffolds keep the data, not the
   chrome, dominant.
3. **Re-verify every contrast and ordering claim** (contrast >= the bars in this doc; sequential
   ramps still monotonic in luminance; still distinct under CVD simulation). Brand palettes are
   rarely colorblind-safe by default — most brand red/green pairs fail. When a brand color fails,
   use it for chrome/accents and derive a compliant data ramp from it rather than forcing it onto
   series.
4. **Do not scatter raw hex through chart code.** Load the palette once (import the JSON, or copy
   it into the project as a single theme module) and reference roles — never paste `#0072B2` into
   twelve call sites. This mirrors the deck-theming discipline in the `pptx-themes` skill.
