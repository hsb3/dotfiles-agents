# Chart-form selection

Pick the mark from the **question and the data shape**, not from what looks impressive.
State the question in one sentence first, then match it to a family below. If two forms fit,
choose the plainer one.

## Data-shape to mark-type heuristic

| The question is about... | Family | Default mark | Reach for instead when |
|---|---|---|---|
| Ranking or comparing values across categories | **Comparison** | Horizontal bar | Many categories (>7) or long labels: horizontal bar. Few categories, one metric: vertical bar/column. |
| How a value moves over time | **Trend** | Line | Few points or discrete periods: column. Cumulative-to-total over time: stacked area (sparingly). |
| The spread and shape of one variable | **Distribution** | Histogram | Comparing distributions across groups: box plot or overlaid density. Every raw point matters: strip/beeswarm. |
| How a whole splits into parts | **Part-of-whole** | Stacked bar (one bar) | Parts over time: stacked area. Nested hierarchy: treemap. **Rarely** a single pie (see anti-patterns). |
| Whether two variables move together | **Relationship** | Scatter | Add a third variable: size (bubble) or color. Dense overplotting: 2D density/hexbin. |
| A value that varies by place | **Geospatial** | Choropleth (rate) or symbol map (count) | Never choropleth a raw count — normalize to a rate or use graduated symbols. |

Second-order forms built from these primitives (sparklines, heatmaps, small multiples, KPI
tiles) are covered in `composition.md`.

## Decision order

1. **What is the ONE takeaway?** Write the chart title as that takeaway sentence. If you can't,
   the chart isn't ready.
2. **What is the data shape?** Number of series, number of categories, is x time / ordinal /
   quantitative, is the measure a count / rate / share.
3. **Match the family** from the table. Prefer position-on-a-common-scale encodings (bar length,
   point position) — they are read most accurately. Angle and area (pie, bubble) are read least
   accurately; use them only when the family genuinely calls for it.
4. **Reduce**. Drop chartjunk, redundant legends, gridline clutter, and any series that doesn't
   serve the takeaway.

## Anti-patterns — do not ship these

Each of these is a common default that misleads. Refuse it and substitute the fix.

| Anti-pattern | Why it misleads | Do this instead |
|---|---|---|
| **Pie chart** for anything but a rough 2-3 slice share | Humans compare angles poorly; slices near-equal are indistinguishable and labels crowd the rim | A single stacked bar, or a sorted horizontal bar of the shares. Reserve pie for a 2-3 slice "this vs the rest" glance only. |
| **Dual y-axes** (two scales on one plot) | The crossover point and relative magnitude are an artifact of arbitrary scale choices; readers infer correlation that isn't there | Two small multiples sharing the x-axis, or index both series to a common base (=100 at t0) and plot on one axis. |
| **Truncated bar axis** (bar baseline not at zero) | Bar length IS the value; a non-zero base exaggerates differences | Bars ALWAYS start at zero. If small differences matter, use a line/dot plot (position, not length, encodes value) where a non-zero range is honest. |
| **Rainbow / spectral scale** for a quantitative field | Hue is not perceptually ordered; the rainbow invents false boundaries (the yellow band) and fails colorblind readers | A perceptually-ordered sequential ramp (see `color.md`). Reserve hue for categories, lightness for magnitude. |
| **3D bars / pies / perspective** | Perspective distorts length and area; occlusion hides data | Flat 2D. There is no honest 3D bar chart. |
| **Too many categorical colors** (>7-8 distinct hues) | Beyond ~7 hues nobody can hold the legend↔mark mapping | Group the long tail into "Other", use small multiples, or direct-label instead of a legend. |
| **Stacked bars/areas for precise comparison of inner segments** | Only the bottom segment and the total share a baseline; middle segments float | Group (dodge) the bars, or small-multiple one panel per segment. Stacking is for part-of-whole totals, not inner comparison. |
| **Sorting bars alphabetically or by input order** | Buries the ranking the chart exists to show | Sort by value (desc) unless the category has an inherent order (age bands, weekdays, Likert). |
| **Encoding a category with a sequential ramp** (or a quantity with unordered hues) | Mismatched channel to data type | Categorical -> distinct hues; ordered/quantitative -> lightness ramp; diverging -> two-hue ramp around a midpoint. |
| **Spaghetti line chart** (10+ overlapping lines) | No line is followable | Highlight one or two, grey the rest; or small multiples, one line per panel. |

## Notes on specific families

- **Comparison — horizontal over vertical** when labels are long or categories exceed ~7:
  horizontal bars give labels room and sort top-to-bottom naturally. Column (vertical) bars are
  fine for a handful of short labels or a time-as-category axis.
- **Trend — connect only continuous series.** Lines imply interpolation; do not connect
  categorical x. For irregular sampling, keep the markers visible so gaps aren't hidden by
  straight interpolation.
- **Distribution — a bar of a mean hides the spread.** If the point is variability, show it
  (box, violin, jitter), not a single averaged bar with error whiskers alone.
- **Relationship — correlation is not the takeaway unless you say so.** Add a trend line only
  when you mean to assert a relationship, and never imply causation from a scatter.
- **Geospatial — a map is only the right call when place itself is the variable.** If the
  reader's real question is ranking, a sorted bar of regions beats a choropleth they must squint
  at. Always normalize choropleth values to a rate/density; area already varies by region.
