# Library notes

This skill is **library-agnostic**: the chart-form, color, composition, and axis rules apply no
matter what draws the pixels. Choose the tool by the destination, then apply the rules. These are
orientation notes and the house-rule gotchas for each — not tutorials.

## Choosing a tool by destination

| Destination | Reach for | Why |
|---|---|---|
| Python analysis, notebooks, static exports (PNG/SVG/PDF) | **matplotlib** (+ its higher-level wrappers) | Ubiquitous, precise, great static output. Verbose for interactivity. |
| Quick interactive exploration, HTML embeds, dashboards | **plotly** | Interactivity (hover/zoom/filter) nearly for free; exports static too. |
| Bespoke, pixel-exact, novel web visualizations | **d3** | Total control; high effort. Use when a standard chart won't do the job. |
| React web apps, product dashboards | **Recharts** (or a peer React chart lib) | Declarative charts inside a component tree. |
| Tiny, dependency-free, embeddable marks (sparklines, inline bars, emails) | **inline SVG** | No runtime, renders anywhere, diffable. Ideal for word-sized graphics. |
| A deck or .pptx | see the `presentations` skill | Deck charts inherit the deck's theme tokens; don't bake a chart palette into a slide. |
| A structural diagram (boxes/arrows, not data) | see the `diagrams` / `mermaid` skills | Not this skill's job — that's the boundary. |

## Per-library house-rule reminders

Whatever you pick, do these — they are where library defaults fight the rules in this skill.

### matplotlib
- **Override the defaults.** Turn off the top/right spines, lighten the grid, drop the default
  tab10 cycle in favor of the palette from `color.md`. Set the color cycle once via rcParams / a
  style, not per call.
- **Bars start at zero** — matplotlib does by default; don't set a non-zero `ylim` on a bar chart.
- **Humanize ticks** with a formatter (thousands separators, `k`/`M`); the default scientific
  notation on large numbers is unreadable.
- **Export both:** SVG for docs, PNG at `dpi>=150` for slides. Set an explicit `figsize` and
  `bbox_inches="tight"`.

### plotly
- **Kill the chartjunk template.** Start from a clean template, set the categorical color sequence
  and continuous colorscale to the palette, and thin the gridlines.
- **Tooltips (`hovertemplate`) carry full precision** and units — this is where interactive detail
  lives (see `interaction.md`).
- **Static export needs a helper** (an image backend); confirm it's installed before promising a
  PNG. The static export must still read on its own (direct labels, no reliance on hover).
- Set an explicit legend order matching the data.

### d3
- **You own every rule manually** — d3 gives you scales and marks, not defaults. Explicitly: bar
  scales from zero (`domain([0, max])`), a perceptual color scale (not `interpolateRainbow`),
  labeled axes, and accessible focus states.
- Use ordinal scales for categories, sequential for magnitude, diverging for signed deviation —
  mirror the palette structure.
- Add ARIA roles / a `<title>`+`<desc>` and a data-table fallback; d3 output is inaccessible by
  default.

### Recharts
- **Pass the palette explicitly** — set each series/`Cell` color from the theme; don't rely on the
  library's default hues.
- Bar charts: keep the `YAxis` domain starting at zero (`domain={[0, 'auto']}`); don't set a
  floor that clips the baseline.
- Style the `CartesianGrid` low-contrast, order the `Legend`/`Tooltip` to match series, and format
  tick/tooltip values (thousands, units) rather than shipping raw numbers.

### inline SVG
- **Best for sparklines, inline bars, and email-safe marks** — no runtime, renders everywhere.
- Encode data as geometry, keep it small, and use palette hex directly (six-digit). Label the
  endpoint for a sparkline; no axes for word-sized marks.
- Set `role="img"` and a `<title>` for accessibility; static by nature, so bake in any value the
  reader needs.

A minimal sparkline as reference (endpoint dot marked, no axes, palette hex):

```svg
<svg width="120" height="28" viewBox="0 0 120 28" role="img"
     aria-label="Weekly signups trending up">
  <title>Weekly signups trending up</title>
  <polyline fill="none" stroke="#0072B2" stroke-width="1.5"
            points="0,22 20,20 40,23 60,15 80,16 100,9 118,5" />
  <circle cx="118" cy="5" r="2.5" fill="#0072B2" />
</svg>
```

## The one invariant across all libraries

Load the palette once and reference it by role; never paste raw hex across many call sites (see
the swap-for-your-brand rule in `color.md`). The library changes; the rules don't.
