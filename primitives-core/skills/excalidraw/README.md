# excalidraw

Create sketch-style, hand-drawn-look architecture diagrams as `.excalidraw` scene files —
useful for early proposals and workshop-style visuals where a rough look signals "not final"
on purpose. Works with or without Excalidraw MCP tools; when they are absent, it authors the
`.excalidraw` JSON scene directly rather than stalling.

## When it triggers

Use it when the user asks for an Excalidraw diagram, a whiteboard-style or sketchy diagram, or
wants a `.excalidraw` file created or edited. For precise or GitHub-rendered diagrams, reach
for the siblings instead — the selection guide lives in the `diagrams` skill.

## Install

```
claude plugin install diagrams@dotfiles-agents
claude plugin install solo-skills@dotfiles-agents
```

Ships in the `diagrams` and `solo-skills` bundles.
