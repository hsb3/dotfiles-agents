# Carbon Charts

## Hard Rules

- All data visualization goes through Carbon Charts — `@carbon/charts-react`
  for React, the matching wrapper (`@carbon/charts-angular`, `-vue`,
  `-svelte`) or core `@carbon/charts` for vanilla JS elsewhere. **Never**
  hand-roll SVG/D3 and never add a second chart library — it breaks theme
  coherence instantly.
- Chart styles are imported **once, at the top of the app entry module**
  (`main.jsx` / `index.jsx`) — **never** in an SCSS file, never via
  `@use`/`@import`.
- Install and confirm the chart packages **before** writing imports; verify
  the exact styles path from the installed package rather than from memory
  (`ls node_modules/@carbon/charts*/` and check the package's `exports` /
  README — the path has changed across major versions).

## Typical React setup

```bash
npm install @carbon/charts-react
# npm will tell you if your version needs peer deps (e.g. d3) — install what it asks for
```

```js
// app entry module (main.jsx) — top-level, not SCSS
import '@carbon/charts-react/styles.css'; // verify path against installed version
```

```jsx
import { SimpleBarChart } from '@carbon/charts-react';

const data = [
  { group: 'Qty', value: 65000 },
  { group: 'More', value: 29123 },
];

const options = {
  title: 'Simple bar',
  axes: {
    left: { mapsTo: 'value' },
    bottom: { mapsTo: 'group', scaleType: 'labels' },
  },
  height: '400px',
};

<SimpleBarChart data={data} options={options} />;
```

Every chart takes the same shape: a `data` array of flat objects and an
`options` object (`title`, `axes` with `mapsTo`/`scaleType`, `height`).

## Available chart components

`SimpleBarChart`, `GroupedBarChart`, `StackedBarChart`, `LineChart`,
`AreaChart`, `StackedAreaChart`, `ScatterChart`, `BubbleChart`, `DonutChart`,
`PieChart`, `GaugeChart`, `MeterChart`, `HeatmapChart`, `TreemapChart`,
`HistogramChart`, `BoxplotChart`, `ComboChart`, `ChoroplethChart` — plus a
tabular `Table` from the same package. (Use a bar chart for "column" charts;
`DonutChart` for "doughnut".)

Confirm the export exists in the installed version before importing:

```bash
node -e "console.log(Object.keys(require('@carbon/charts-react')).filter(n => /chart/i.test(n)))"
```

## Verifying data/options shapes

The original skill fetched chart source and options schemas from an MCP
server. Without it:

1. **Charts Storybook** — `https://charts.carbondesignsystem.com/` has every
   chart type with live, copyable `data` and `options` for each variant
   (grouped, stacked, time-series, ...). This is the authoritative example set.
2. **Options typings** — the installed `@carbon/charts` package ships
   TypeScript interfaces (`BarChartOptions`, `AxesOptions`, `LegendOptions`,
   ...); grep them under `node_modules/@carbon/charts/dist/` when the user
   asks about a specific option (legend, toolbar, axis truncation).
3. **Design guidance** — chart-type selection and dataviz color palettes:
   `https://carbondesignsystem.com/data-visualization/` (see [llms.txt](llms.txt)).

## Theming gap (known)

Carbon Charts has its **own** theming layer that does not auto-follow the page
theme/layer model. Matching chart palette and background to the active Carbon
theme is a known gap — treat it as its own scoped task, not a default
expectation.
