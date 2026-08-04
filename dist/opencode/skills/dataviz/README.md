# dataviz

Design data visualizations — charts, plots, dashboards — that are correct, legible, and
honest. Consulted BEFORE writing chart code in any library or medium: it supplies a
data-shape → mark-type selection heuristic, a table of anti-patterns to refuse (pie-chart
overuse, dual axes, truncated bar axes, rainbow scales, 3D), a brand-neutral
colorblind-safe palette with light/dark themes and a brand-swap procedure, plus
composition, axis/legend/tooltip, and interaction rules with static degradation.

## When it triggers

Use it whenever a chart, graph, dashboard, KPI tile, sparkline, or heatmap is about to be
produced — HTML, inline SVG, matplotlib, plotly, d3, Recharts, or a rendered image. A
final validation checklist runs before any visualization is delivered. Data charts only:
structural diagrams belong to a diagramming skill, deck theming to a presentation skill.

## Install

```
claude plugin install dataviz@dotfiles-agents
```

Standalone-only — it does not ship inside any bundle. No dependencies; the palette ships
as a reference file with WCAG-verified contrast in both themes.
