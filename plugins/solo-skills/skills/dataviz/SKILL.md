---
name: dataviz
description: Design data visualizations - charts, graphs, plots, and dashboards - that are correct, legible, and honest, in any medium. Consult this BEFORE writing any chart, graph, plot, or dashboard code, whatever the library (matplotlib, plotly, d3, Recharts, inline SVG) or output (static image, notebook, web app, deck). Use whenever a task involves picking a chart type, a color palette for data, dashboard or KPI-tile layout, axis and label formatting, or making a visualization colorblind-safe and light/dark-ready. Covers the data-shape to mark-type heuristic, chart anti-patterns to refuse (pie overuse, dual axes, truncated bar axes, rainbow scales, 3D), a brand-neutral colorblind-safe palette you can rebrand, composition, interaction and static degradation, and a final validation checklist. Data charts only - structural diagrams and deck theming are out of scope.
---

# Data visualization

Design charts, graphs, plots, and dashboards that are **correct, legible, and honest** — in any
medium and any library. This skill is consulted **before** any visualization is coded: the choice
of mark, scale, color, and layout is decided here, then the drawing library just executes it.

**Read this hub, then pull the reference that matches the decision you're on.** The rules are
library-agnostic; `references/libraries.md` has the per-tool reminders.

## Scope and boundaries

One owner per fact — these boundaries keep skills from fighting over triggers:

- **This skill owns anything that encodes a dataset** — bar/line/scatter/area, distributions,
  part-of-whole, relationship, geospatial, dashboards, KPI/stat tiles, sparklines, heatmaps,
  small multiples. If the visual carries numbers, it is this skill's job.
- **Structural diagrams** (boxes, arrows, flow, containment, architecture, sequence, ER, org,
  process) → the `diagrams` and `mermaid` skills. Do not use a chart library for structure, and
  do not use diagram tools (or Mermaid `pie`/`xychart`) for real data.
- **Deck/slide theming and PowerPoint charts** → `presentations`. A chart on a slide inherits the
  deck's theme tokens; don't bake a chart palette into a slide.

## Workflow — before you draw

1. **State the takeaway in one sentence.** That sentence is the chart title. If you can't write
   it, the chart isn't ready.
2. **Name the data shape** — number of series, number of categories, whether x is time / ordinal /
   quantitative, whether the measure is a count / rate / share.
3. **Pick the mark** from the data-shape heuristic (`references/chart-selection.md`). Prefer the
   plainer, position-based form.
4. **Check it against the anti-patterns** below. Refuse and substitute — don't ship a known-
   misleading default.
5. **Choose the color encoding** to match the data type and the destination theme
   (`references/color.md`, `references/palette.json`).
6. **Set axes, scales, labels, and formatting** (`references/marks-and-axes.md`) — this is where
   honesty lives.
7. **Compose** if there's more than one chart (`references/composition.md`).
8. **Layer interaction** only after the static view stands alone (`references/interaction.md`).
9. **Run the validation checklist** at the bottom of this file before delivering.

## Data-shape to mark-type — quick heuristic

Full table, second-order forms, and per-family notes: `references/chart-selection.md`.

| The question is about... | Family | Default mark |
|---|---|---|
| Ranking / comparing across categories | Comparison | Horizontal bar (sorted by value) |
| A value moving over time | Trend | Line |
| Spread and shape of one variable | Distribution | Histogram / box plot |
| How a whole splits into parts | Part-of-whole | Single stacked bar |
| Whether two variables move together | Relationship | Scatter |
| A value that varies by place | Geospatial | Choropleth (rate) or symbol map (count) |

Prefer position-on-a-common-scale encodings (bar length, point position) — they are read most
accurately. Angle and area (pie, bubble) are read least accurately; use them only when the family
truly calls for it.

## Anti-patterns — refuse these

These are common library defaults that mislead. Detail and fixes in `references/chart-selection.md`.

- **Pie charts** for anything past a rough 2-3 slice share → single stacked bar or sorted bars.
- **Dual y-axes** → two small multiples sharing x, or index both series to a common base.
- **Truncated bar axis** (baseline not at zero) → bars ALWAYS start at zero; use a dot/line plot
  if a non-zero range is genuinely needed.
- **Rainbow / spectral scales** on quantitative data → a perceptually-ordered sequential ramp.
- **3D bars / pies / perspective** → flat 2D; there is no honest 3D bar.
- **Too many categorical colors** (>7-8) → group the tail into "Other", small-multiple, or direct-
  label.
- **Stacking to compare inner segments** → group (dodge) or small-multiple.
- **Sorting bars alphabetically** when a ranking is the point → sort by value.
- **Spaghetti line charts** → highlight one or two, grey the rest, or small multiples.

## Color — quick rules

Full system, contrast/colorblind requirements, light/dark handling, and brand-swap procedure:
`references/color.md`. Default values: `references/palette.json`.

- **Match palette type to data type:** categorical → distinct **hues** (cap ~7); sequential →
  one hue, **lightness** ramp; diverging → two hues around a **meaningful midpoint**; semantic →
  reserved for good/bad/warn/info, never decoration.
- **Never encode by hue alone** — pair with labels, markers, dash patterns, or position (~8% of
  men have a color-vision deficiency). Prefer **blue-orange over red-green** for two-way splits.
- **Contrast bars:** text on its background ≥ 4.5:1; meaningful non-text marks ≥ 3:1; gridlines
  deliberately low (~1.2-1.5:1) so they sit behind the data.
- **Author for the surface:** pick the `light` or `dark` theme block to match the destination;
  give exported images their own opaque panel when the host background is unknown.
- **`references/palette.json` is brand-neutral and swappable** — replace the categorical/accent
  hues with brand colors, keep the neutral scaffold, and RE-VERIFY contrast and colorblind
  separation (most brand red/green pairs fail). Its shipped contrast claims were checked with the
  WCAG relative-luminance formula.

## Composition — quick rules

Full guidance (dashboards, KPI tiles, sparklines, heatmaps, small multiples): `references/composition.md`.

- **One primary message per view**, largest and top-left; reading order = importance order.
- **Align to a grid**; group with whitespace, not boxes. Same number format, date range, and color
  meaning across every tile.
- **Stat tiles:** big value, quiet label, and a signed/colored delta vs a comparison period — never
  a bare number.
- **Small multiples share identical scales** across panels — that is the whole point; a per-panel
  axis range is a bug.
- **Heatmaps** use a sequential/diverging ramp with a real value legend, meaningfully ordered rows.

## Marks and axes — quick rules

Full spec (axes, gridlines, legends, tooltips, number/date/unit formatting): `references/marks-and-axes.md`.

- **Bars/areas start at zero; lines/dots may use a non-zero range** made obviously bounded. Log
  scales are opt-in and labeled.
- **Label both axes with quantity AND unit.** Direct-label marks instead of a far-off legend when
  you can; order any legend to match the data.
- **Gridlines subtle and behind the data**, one direction usually enough.
- **Humanize numbers** (`1.2M`, `48.3k`, thousands separators), round to the precision the decision
  needs, use unambiguous dates (`YYYY-MM-DD` or explicit month), keep formatting consistent.

## Interaction and static degradation — quick rules

Full patterns and hygiene: `references/interaction.md`.

- **Static-first:** every essential fact must be legible with zero interaction (print, screenshot,
  screen reader). Interaction reveals detail; it never hides the headline.
- Hover/tooltip carries the precision the axis rounds off; filter/zoom always show state and a
  reset; highlight-on-hover fades rather than removes context.
- **Degrading to a static image:** bake in what hover would show (direct labels, annotations),
  freeze a sensible default view, drop live-only chrome, add a caption + source line, export crisp.

## Libraries

Library-agnostic by design; pick by destination, then apply the rules above. Per-tool reminders
(matplotlib, plotly, d3, Recharts, inline SVG) and a tool-selection table: `references/libraries.md`.
The one invariant everywhere: **load the palette once and reference it by role — never paste raw
hex across many call sites.**

## Final validation checklist

Run this before delivering ANY visualization. Every item is a "yes" or you fix it first.

**Message**
- [ ] The title states the ONE takeaway, and the chart supports it.
- [ ] Nothing on the chart is there without a job (no chartjunk, redundant legend, or decorative 3D).

**Mark and scale**
- [ ] The mark matches the data shape (comparison / trend / distribution / part-of-whole /
  relationship / geospatial).
- [ ] Not on the anti-pattern list — or, if borderline, the honest substitute was used.
- [ ] Bars/areas start at zero; any non-zero line/dot range is obviously bounded; log scales are
  labeled.

**Axes and labels**
- [ ] Both axes labeled with quantity AND unit; ticks are round and readable.
- [ ] Numbers humanized and consistently formatted; dates unambiguous; categories sorted meaningfully.
- [ ] Legend ordered to match the data, or marks are direct-labeled.

**Color**
- [ ] Palette type matches data type (categorical / sequential / diverging / semantic).
- [ ] Not encoded by hue alone; two-way splits use blue-orange, not red-green.
- [ ] Text ≥ 4.5:1, meaningful marks ≥ 3:1 on their background; gridlines sit behind the data.
- [ ] Authored for the destination surface (light/dark); exported images carry their own panel.

**Composition** (if more than one chart)
- [ ] One clear entry point; reading order matches importance; tiles aligned on a grid.
- [ ] Number format, date range, and color meaning consistent across every panel.
- [ ] Small multiples share identical scales.

**Interaction / delivery**
- [ ] The static view stands alone — a screenshot of the default state explains itself.
- [ ] Any interaction has visible state and a reset; keyboard/screen-reader path exists.
- [ ] Exported at the right resolution/format for the destination, with a caption and source line.

## References

- `references/chart-selection.md` — data-shape → mark heuristic, families, full anti-pattern table.
- `references/color.md` — categorical/sequential/diverging/semantic rules, contrast + colorblind
  requirements, light/dark themes, brand-swap procedure.
- `references/palette.json` — the brand-neutral, colorblind-safe default palette (six-digit hex).
- `references/composition.md` — dashboards, KPI/stat tiles, sparklines, heatmaps, small multiples,
  hierarchy and alignment.
- `references/marks-and-axes.md` — axes, gridlines, legends, tooltips, zero baseline, number/date/
  unit formatting.
- `references/interaction.md` — hover/filter/zoom patterns and how to degrade to static output.
- `references/libraries.md` — tool selection and per-library house-rule reminders.
