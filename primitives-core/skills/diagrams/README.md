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
(`presentations`).

## Install

```
claude plugin install diagrams@dotfiles-agents
```

Ships in the `diagrams` bundle.

## Consumer memory and installed paths

Run helpers by their absolute installed skill path from the consumer project. Bundled
`memory/MEMORY.md` is read-only seed guidance; new learnings go to existing project
`.claude/memory/diagrams.md`, otherwise `.claude/diagrams-memory.md`. Override with
`memory-path:` in `.claude/diagrams.local.md`; `memory_manager.py path` prints the resolved
file. This project convention works in Claude Code and Codex and survives cache updates.
