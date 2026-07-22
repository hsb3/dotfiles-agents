---
name: excalidraw
description: Create sketch-style, hand-drawn-look architecture diagrams as Excalidraw files. Use when the user asks for an excalidraw diagram, a whiteboard-style or sketchy diagram, or wants a .excalidraw file created or edited. Works with or without the Excalidraw MCP tools - when the MCP tools are unavailable, author the .excalidraw JSON scene directly. Covers the scene JSON schema, element and arrow-binding essentials, and export to SVG/PNG.
---

# Excalidraw Diagrams

Excalidraw produces sketch-style diagrams — the hand-drawn look that reads as "proposal, not blueprint". Good for early architecture sketches and workshop-style visuals; for precise or GitHub-rendered diagrams use the siblings (`mermaid`, `diagrams` — see the selection guide in the `diagrams` skill).

## Tooling availability — check first

Some sessions expose Excalidraw MCP tools (`mcp__claude_ai_Excalidraw__*` — create_view, export_to_excalidraw, checkpoints). **They are NOT always available.**

1. **MCP tools present** → use them: create the view, iterate visually, and export/checkpoint through the tools.
2. **MCP tools absent** (the common case in terminal sessions) → **author the `.excalidraw` JSON directly** with the schema below. Do not stall or tell the user it can't be done — the file format is plain JSON and fully authorable.

The user opens the result at excalidraw.com (File → Open), in the VS Code Excalidraw extension, or in Obsidian's Excalidraw plugin.

## The .excalidraw file format

A scene file is JSON:

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [],
  "appState": { "viewBackgroundColor": "#ffffff", "gridSize": null },
  "files": {}
}
```

### Elements

Every element needs: unique `id`, `type`, `x`, `y`, `width`, `height`, plus boilerplate the app expects. Safe defaults:

```json
{
  "id": "api-box", "type": "rectangle",
  "x": 100, "y": 100, "width": 180, "height": 70,
  "angle": 0, "strokeColor": "#1e1e1e", "backgroundColor": "#a5d8ff",
  "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
  "roughness": 1, "opacity": 100, "roundness": { "type": 3 },
  "seed": 1, "version": 1, "versionNonce": 1, "isDeleted": false,
  "groupIds": [], "frameId": null, "boundElements": [], "updated": 1,
  "link": null, "locked": false
}
```

- Types: `rectangle`, `ellipse`, `diamond`, `arrow`, `line`, `text`, `frame`, `image`.
- `roughness` 0–2 controls sketchiness (1 = classic look); `fillStyle` can be `hachure` for the scribbled fill.
- `seed` randomizes the wobble; any integer works.

### Text and labels

Standalone text element: `type: "text"` with `text`, `fontSize` (16/20/28), `fontFamily: 1` (the hand-drawn Virgil font), `textAlign`, `verticalAlign`, and `containerId: null`.

**Label inside a shape** = a text element whose `containerId` is the shape's id, plus a back-reference in the shape's `boundElements`:

```json
"boundElements": [{ "id": "api-label", "type": "text" }]
```

### Arrows and binding

An arrow is `type: "arrow"` with `points` (relative to its `x`,`y`): `"points": [[0, 0], [220, 0]]`, and `endArrowhead: "arrow"` (`startArrowhead: null`). To make it stick to shapes, bind both ends and back-reference from each shape:

```json
"startBinding": { "elementId": "api-box", "focus": 0, "gap": 4 },
"endBinding":   { "elementId": "db-box",  "focus": 0, "gap": 4 }
```

and on each bound shape: `"boundElements": [{ "id": "arrow-1", "type": "arrow" }]`. Unbound arrows also render fine — binding just survives dragging.

### Layout tips for authored scenes

- Excalidraw has no auto-layout: compute coordinates yourself. Grid of ~220x120 cells with 60–80 px gaps reads well.
- Palette that keeps the sketch feel: pastel fills (`#a5d8ff` blue, `#b2f2bb` green, `#ffec99` yellow, `#ffc9c9` red) with `#1e1e1e` strokes — readable on light and dark canvases.
- Group related shapes via a shared id in `groupIds`, or use a `frame` element as a titled container.

## Export to SVG/PNG

No official headless CLI. Options, in order of preference:

1. **Excalidraw MCP tools** (when available) — export directly.
2. **App export** — user opens the file at excalidraw.com and exports PNG/SVG (2x for decks).
3. **Scripted** — the `@excalidraw/utils` npm package exposes `exportToSvg(scene)` for a Node one-off when automation matters.

Exported pairs follow the SVG+PNG output-pipeline conventions in the `diagrams` skill (numbered files in the artifact's `diagrams/` folder). The `.excalidraw` JSON is the source of truth — commit it next to the exports.

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| File won't open / blank canvas | Missing boilerplate keys on an element | Include the full safe-default key set above |
| Label floats outside its shape | `containerId` set but no `boundElements` back-reference | Add both directions of the link |
| Arrow detaches when user drags a box | No `startBinding`/`endBinding` | Bind both ends + back-reference |
| Everything renders identical-wobble | Same `seed` on all elements | Vary seeds per element |
| Text renders in wrong font | `fontFamily` omitted | `"fontFamily": 1` for the sketch font |
