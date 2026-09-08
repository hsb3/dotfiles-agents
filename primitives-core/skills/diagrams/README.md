# diagrams

Create technical architecture diagrams with Python's `diagrams` library (provider icons for
Azure, GCP, AWS, Kubernetes, on-prem) or raw Graphviz dot for icon-free graphs. It is also the
**hub** of the diagrams bundle: it owns tool selection across the sibling renderers and the
shared SVG+PNG output pipeline that feeds GitHub markdown, slide decks, and standalone docs.
`scripts/diagram_helper.py validate` checks that Graphviz and the `diagrams` library are both
installed before the first render; its `boilerplate` subcommand scaffolds a starter script.

## When it triggers

Use it for cloud architecture diagrams with provider iconography, system design and
infrastructure visuals, data flow diagrams, dependency graphs, and org or process trees — any
structural diagram of components and relationships. It also decides *which* renderer fits a
request: Mermaid for GitHub-rendered docs, this skill for provider-icon or icon-free graph
diagrams, `drawio` for legacy `.drawio` files, `excalidraw` for sketch-style visuals. Data
charts and plots are out of scope (the `dataviz` skill owns those), as is deck palette styling
(`pptx-themes`).

## Install

```
claude plugin install diagrams@dotfiles-agents
claude plugin install solo-skills@dotfiles-agents
```

Ships in the `diagrams` and `solo-skills` bundles.
