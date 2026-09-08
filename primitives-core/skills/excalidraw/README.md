# excalidraw

Create sketch-style, hand-drawn-look architecture diagrams as `.excalidraw` scene files —
useful for early proposals and workshop-style visuals where a rough look signals "not final"
on purpose. Works with or without Excalidraw MCP tools; when they are absent, it authors the
`.excalidraw` JSON scene directly rather than stalling.

## What it carries

Beyond the scene format itself: a headless render loop (`scripts/render_check.py`) that draws
a scene to SVG, screenshots it through Playwright's Chromium, and lints it for the defects an
author cannot see in JSON — overlapping shapes, a binding naming a missing element, a label
with no back-reference, an element outside its frame, text too wide for its container. Fully
offline, nothing installed into the project, renders written to a scratch dir rather than the
repo. Scenes are treated as untrusted input — every value that reaches the SVG is a checked
number or an allowlisted colour, because the render page has a file:// origin. A sample scene
ships in `examples/`, `--self-test` checks the loop against five injected defects, and
`tests/test_excalidraw_render.py` covers the lint boundaries, the SVG geometry and the
screenshot wiring without launching a browser. Alongside it, the methodology in `SKILL.md`: evidence artifacts, depth
assessment, a visual pattern library, a section-by-section workflow for large diagrams, and a
handover checklist.

## When it triggers

Use it when the user asks for an Excalidraw diagram, a whiteboard-style or sketchy diagram, or
wants a `.excalidraw` file created or edited. For precise or GitHub-rendered diagrams, reach
for the siblings instead — the selection guide lives in the `diagrams` skill.

## Install

```
claude plugin install diagrams@dotfiles-agents
```

Ships in the `diagrams` bundle.
