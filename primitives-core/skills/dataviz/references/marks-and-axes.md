# Marks, axes, and encoding

The chart's credibility lives in its axes and labels. Get these right before styling anything.

## The zero-baseline rule

- **Bar / column / area charts: the value axis MUST start at zero.** Length and area encode the
  value; a clipped baseline lies. No exceptions.
- **Line and dot (point-position) charts: a non-zero range is honest** — position, not length,
  carries the value, so zooming to the data range to reveal a real change is fine. When you do,
  make the truncation obvious (clear axis bounds, no implication the baseline is zero).
- **Never fake a zero.** No broken-axis "//" jumps on a bar chart to squeeze in an outlier — split
  it out or use a log scale with the scale clearly labeled.
- **Log scales are opt-in and labeled.** Use for data spanning orders of magnitude; say "log
  scale" on the axis so nobody reads it as linear.

## Axes

- **Label both axes** with the quantity AND its unit ("Revenue (USD, millions)", "Latency (ms)").
  An unlabeled axis is a bug.
- **Tick density:** enough to read values, few enough to breathe. Prefer "nice" round intervals
  (1/2/5 x 10^n). Don't label every pixel; 4-7 ticks per axis is a good target.
- **Direct-label when you can.** For a handful of lines or bars, a label at the end of the line or
  on the bar beats a separate legend the eye has to ping-pong to.
- **Time axes:** order left-to-right, oldest-to-newest; label at a sensible granularity (don't
  print every day for a two-year series); keep intervals even.
- **Categorical axes:** sort by value unless the category has an inherent order (weekdays, age
  bands, Likert). Never alphabetical-by-accident.

## Gridlines

- **Subtle and behind the data.** Low-contrast (see `color.md`), thin, and never on top of marks.
- **One direction is usually enough** — horizontal gridlines for a bar/line chart whose values
  read off the y-axis. Drop the axis most readers won't measure against.
- **No gridlines on a scatter** unless reference values matter; they add noise.
- Kill the chart border/frame unless it separates the plot from a busy background.

## Legends

- **Prefer no legend** — direct labels remove the lookup step. Use a legend only when marks can't
  be labeled in place.
- **Order the legend to match the data** (top line first, stacking order top-to-bottom). A legend
  whose order fights the chart forces a re-scan.
- Put the legend where the eye already is (near the marks), not marooned in a far corner.

## Labels and number formatting

- **Round to the precision that matters.** "42%" not "41.7834%". Show decimals only when the
  decision needs them. Keep decimal places consistent within a series.
- **Humanize large numbers:** `1.2M`, `48.3k`, `$3.1B`. Keep the unit adjacent. Use the same
  abbreviation scheme across the whole figure.
- **Thousands separators** on any number with >=4 digits shown in full (`12,480`).
- **Percentages:** show the base when it's small ("3 of 12"), and never let rounded shares imply a
  false 100% total.
- **Align numbers right / on the decimal** in tables and data labels; right-aligned digits compare
  at a glance.
- **Units once, not on every value** — put the unit in the axis or column header, not repeated on
  each tick, unless mixing units.

## Dates

- **Unambiguous format.** Prefer ISO-style `YYYY-MM-DD` for data and axis ticks; if using a
  localized format, make month names explicit ("Mar 2026") so `03/04` is never ambiguous.
- **Consistent granularity** across the axis; don't mix "Q1" and "March".
- **Label the timezone** when it changes interpretation (intraday series, cross-region data).

## Tooltips (interactive media)

- **The tooltip carries the precision the axis rounds off** — full value, exact date, and the
  category name, formatted the same way as the labels.
- **Show all encoded dimensions** for the hovered mark (x, y, series, and any size/color field),
  each with its unit.
- **Anchor to the mark**, don't cover it; keep the tooltip inside the viewport.
- **A tooltip is an enhancement, not the only path to a number.** Anything essential must also be
  visible without hovering — a static reader (print, export, screenshot) never sees a tooltip.
  See `interaction.md`.

## Annotation

- **Call out the takeaway on the chart itself** — a short text note or a reference line at the
  threshold that matters ("target", "launch", "SLA") turns a chart into an argument.
- Keep annotations sparse and high-contrast; one or two, not a scrapbook.
