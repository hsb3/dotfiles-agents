# Composition — dashboards and multi-chart layouts

When more than one number shares a surface, layout IS the design. Compose for a reading order,
not a collage.

## Hierarchy and alignment

- **One primary message per view.** Lead with the headline number or the takeaway chart; make it
  the largest, top-left-most element (for left-to-right readers). Everything else supports it.
- **Reading order = importance order.** Top-left to bottom-right, most-to-least important. Don't
  make the eye hunt.
- **Align to a grid.** Shared column edges, consistent gutters, a common baseline. Ragged edges
  read as careless and slow comprehension. Pick a column count and hold it.
- **Group related tiles** with proximity and whitespace, not boxes and borders. Whitespace is the
  cheapest and strongest grouping device; reach for a divider only when spacing can't carry it.
- **Consistency across tiles:** same number format, same date range, same color meaning
  everywhere. A series' color must mean the same thing in every panel.
- **Whitespace is not wasted.** Dense-to-the-edges dashboards read as noise; breathing room is
  what makes the hierarchy legible.

## KPI / stat tiles

A stat tile answers "what is this number and is it good?" at a glance.

- **Value dominant, label quiet.** Big number, small caption above or below. The number is the
  hero; the label is context.
- **Show the comparison, not just the value.** A bare "482" is inert. Add the delta vs prior
  period (`+12% vs last month`) and color the delta with the semantic set (positive/negative) —
  plus a sign or arrow so it doesn't rely on color alone.
- **Right-size the precision.** Humanize (`$1.2M`, `48.3k`); don't show `1,204,882.14` in a tile.
- **Pair with a sparkline** when the trend matters as much as the level (below).
- **Keep tiles uniform** — same footprint, same internal layout — so a row of them scans as a row.

## Sparklines

Word-sized trend lines for inline context — in a tile, a table row, or prose.

- **No axes, no gridlines, minimal or no labels** — a sparkline shows SHAPE, not exact values.
- **Mark the endpoint** (a dot) and often the last value as text; optionally min/max points.
- **Keep a consistent y-range** across a column of sparklines so their slopes are comparable —
  auto-ranging each one independently makes flat things look dramatic.
- Use them to add trend to a number, never as the primary chart when precise reading is needed.

## Heatmaps

A matrix of a quantitative value across two categorical (or binned) axes, encoded by color.

- **Use a sequential ramp** (or diverging around a meaningful midpoint) from `color.md` — never a
  rainbow. Color = the value; that is the whole encoding.
- **Order rows/columns meaningfully** — sort by total, or cluster similar rows adjacent. Arbitrary
  (alphabetical/input) order hides the pattern the heatmap exists to reveal.
- **Include a legend/color scale** with real values; heatmap color is unreadable without one.
- **Label cells with the value** when the grid is small enough — belt-and-suspenders for readers
  who can't discriminate close shades (and for colorblind readers).
- **Mind cell count** — beyond a few hundred cells, aggregate or bin; a 2,000-cell heatmap is a
  texture, not a chart.

## Small multiples

The same chart repeated once per category — the honest answer to "too many series on one plot".

- **Shared, identical scales across every panel.** Same x-range, same y-range, same color meaning.
  This is the entire point: differences between panels are real, not a scaling artifact. A panel
  with its own axis range is a bug.
- **A tidy grid**, sorted by a meaningful order (value, geography, time) so scanning the grid is
  itself informative.
- **Label each panel** with its category; share ONE set of axis labels around the grid rather than
  repeating ticks on every panel.
- **Highlight in context:** to show one series against the rest, small-multiple with the focus
  series drawn dark and the shared background series greyed in every panel.
- Prefer small multiples over: dual axes, spaghetti line charts, and stacked areas where inner
  segments need comparing (all called out in `chart-selection.md`).

## Dashboard assembly checklist

- Is there a single obvious entry point (the headline)?
- Does reading order match importance (top-left first)?
- Do all tiles share number format, date range, and color meaning?
- Is everything on a common grid with consistent gutters?
- Could any tile be a sparkline-augmented stat instead of a full chart?
- Does every chart still pass the per-chart checklist in `../SKILL.md`?
