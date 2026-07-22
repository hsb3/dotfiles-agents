# Interaction and graceful degradation

Interactivity is an enhancement layer, never the thing that makes a chart readable. Author the
static view first; add interaction on top; make sure the static view still stands alone.

## The static-first rule

**Every essential fact must be legible without a single interaction.** A reader on paper, in a
screenshot, in an email, or with a screen reader gets zero hovers, zero clicks, zero zoom. If the
only way to learn the value is to hover, the chart has failed for half its audience.

- The default rendering shows the takeaway, the axes, the units, and the key values.
- Interaction reveals DETAIL and lets a reader EXPLORE — it never hides the headline.
- Build the static image, confirm it carries the message, then layer interaction.

## Interaction patterns (for interactive media only)

| Pattern | Good for | Rules |
|---|---|---|
| **Hover / focus tooltip** | Exact values, full dates, the fields the axis rounds off | Also expose on keyboard focus, not just mouse. Anchor to the mark, stay in the viewport, format like the labels. See `marks-and-axes.md`. |
| **Filter / toggle** | Slicing a dense dataset, showing/hiding series | Show current filter state in plain text; make "reset to all" obvious; never let a filtered view masquerade as the whole. |
| **Zoom / pan / brush** | Long time series, dense scatters | Provide a visible "reset zoom"; keep an overview+detail (a small context strip showing where you are); don't trap the reader in a sub-range with no way out. |
| **Highlight on hover** (fade the rest) | Spaghetti line charts, crowded categories | Emphasis only — the un-highlighted series stay faintly visible, never removed, so context survives. |
| **Cross-filter / linked views** | Dashboards where selecting in one panel filters others | Make the linkage discoverable and reversible; show what's selected. |
| **Drill-down** | Hierarchical data (region -> country -> city) | Always show a breadcrumb and a way back up; never a one-way trip. |

## Interaction hygiene

- **Discoverability:** if a control isn't visible, most readers never find it. Prefer visible
  affordances (a legend you can click that looks clickable, a labeled filter) over hidden gestures.
- **Reversibility:** every interaction has an obvious undo/reset. No dead ends.
- **State visibility:** the current filter/zoom/selection is stated in text, so a screenshot of an
  interacted state is still self-explaining.
- **Keyboard + screen-reader:** interactive charts need focusable marks, ARIA/alt text, and a data
  table fallback. Mouse-only interaction excludes real users.
- **Performance:** debounce hover, throttle redraws, and downsample dense series so interaction is
  smooth — a janky tooltip is worse than none.

## Degrading to static output

When the same chart must ship as a static image (print, PDF, deck slide, exported PNG, an email,
a markdown embed):

1. **Bake in what hover would have revealed.** Direct-label the lines/bars, put key values on the
   marks, and annotate the takeaway on the chart — the static reader has no tooltip.
2. **Freeze a sensible default view.** No filter engaged, full range shown, or the specific slice
   the narrative needs — and say which in the caption.
3. **Drop the chrome that only makes sense live.** Zoom handles, "click to filter" hints, and
   reset buttons are noise in an image; remove them.
4. **Give it an opaque panel and border** if the destination background is unknown (see the
   light/dark guidance in `color.md`) so it survives on any page.
5. **Add a caption and a source line.** The static artifact travels without its page; the caption
   states the takeaway, the source line states provenance and date.
6. **Export at print resolution** (2x scale / >=150 DPI for raster) so it stays crisp when
   projected or printed; ship SVG when the destination accepts it.

The test: screenshot the interactive chart in its default state. If that image doesn't stand on
its own, the static path isn't done.
