---
name: excalidraw
description: Create sketch-style, hand-drawn-look architecture diagrams as Excalidraw files. Use when the user asks for an excalidraw diagram, a whiteboard-style or sketchy diagram, or wants a .excalidraw file created or edited. Works with or without the Excalidraw MCP tools - when the MCP tools are unavailable, author the .excalidraw JSON scene directly. Covers the scene JSON schema, element and arrow-binding essentials, an offline headless render-and-lint loop that screenshots a scene and names its defects, and export to SVG/PNG.
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

## Render it and check it — the headless loop

Upstream ships no headless CLI, so this skill carries its own renderer. `scripts/render_check.py` draws the scene to SVG, screenshots it through headless Chromium (Playwright), and lints the scene as data. **Run it before handing any scene to the user** — you author blind otherwise.

```
python3 scripts/render_check.py path/to/scene.excalidraw --out "$(mktemp -d)"
```

Writes `<stem>.svg` and `<stem>.png` to the out dir, prints both paths, and exits 1 when the lint finds defects (it still renders — you read the finding and look at the picture together). Default scene is the bundled `examples/request-path.excalidraw`.

- Playwright must be resolvable by node. The script uses `$EXCALIDRAW_NODE_PATH`, else `npm root -g`; `--node-path DIR` overrides both. A global install is enough — nothing is installed into the project.
- `--no-screenshot` writes SVG only (no node needed); `--lint-only` skips rendering; `--defect <kind>` injects a known defect into a copy to exercise the loop; `--self-test` runs the built-in checks.
- **Fidelity:** first-party renderer. Position, size and rotation are exact; the hand-drawn wobble and hachure texture are not reproduced, and the `overlap` rule compares axis-aligned boxes, so it does not see a collision that only rotation creates. It answers "is this laid out right", not "is this pretty".
- **Offline and deterministic.** Nothing is fetched at any point: the page is a local file, and every colour a scene supplies is checked against a hex/keyword allowlist before it reaches an attribute. A scene from someone else cannot make the render call out — treat that as the reason to run this on a file you were sent, not a reason to skip it.

What the lint catches:

| Code | Meaning |
|---|---|
| `overlap` | two shapes partly cover each other. Full containment is composition (a zone background, a badge) and is not flagged |
| `dangling-arrow` | a binding names an element id that is not in the scene |
| `dangling-ref` | a `boundElements` entry names an id that is not in the scene — the app drops the link on load |
| `orphan-label` | a `containerId` with no `boundElements` back-reference (or no container at all) |
| `frame-escape` | a shape sits outside the frame it claims, or its `frameId` is not a frame. Arrows are exempt — crossing frames is the Layers pattern |
| `text-overflow` | a label is wider than its container. Uses the app's measured `width` when the element has one, a character estimate otherwise |

**Export for delivery** is a separate step: Excalidraw MCP tools when available, otherwise the user opens the file at excalidraw.com and exports PNG/SVG (2x for decks); the `@excalidraw/utils` npm package exposes `exportToSvg(scene)` for a Node one-off with the real renderer. Exported pairs follow the SVG+PNG output-pipeline conventions in the `diagrams` skill (numbered files in the artifact's `diagrams/` folder). The `.excalidraw` JSON is the source of truth — commit it next to the exports.

## Methodology

**Evidence artifacts.** A scene you hand over comes with three things: the `.excalidraw` source (committed), the PNG you actually looked at, and the lint output. "It should render fine" is not evidence. Renders are derived — write them to a scratch dir and keep them out of the repo unless the user asks for a committed export.

**Depth assessment** — pick the level *before* placing anything, and say which you picked:

| Depth | Elements | Shows | Use for |
|---|---|---|---|
| Sketch | < 15 | one idea, no internals | a proposal, a whiteboard photo replacement |
| Working | 15–40 | components, their links, one frame per zone | design review, onboarding |
| Detailed | 40+ | protocols, data shapes, failure paths | a spec appendix — split it before it grows past this |

Depth creep is the usual defect: a sketch that grew internals reads as a blueprint and invites blueprint-level argument about a thing you have not designed yet.

**Visual pattern library** — reach for a known shape instead of inventing a layout:

| Pattern | Layout | Reads as |
|---|---|---|
| Pipeline | left-to-right row, bound arrows between | a request or data path |
| Layers | stacked frames, one per tier, arrows crossing down | an architecture stack |
| Hub | one centre shape, radial arrows out | a broker, a bus, one service everything calls |
| Swimlane | one frame per actor, time flowing right | a sequence with owners |
| Cluster | grouped shapes in a frame with a title | a bounded context or deployment unit |

Encode meaning in the palette, not just prettiness: one fill per role (blue = client, green = service, yellow = store, red = external), and keep it the same across every diagram in the set.

**Section by section for large diagrams.** Past ~25 elements, never author the whole scene and render once. Draw one section (a frame and its contents), run the loop, fix, then add the next section and re-run. Coordinates are computed by hand here — an early off-by-100 propagates into every later element, and one render at the end makes you unpick all of them at once. Keep a section's origin as a variable in your head (`frame x + 40`), not an absolute number you re-derive per shape.

**Quality checklist** — before handing over:

- [ ] `render_check.py` ran on the final scene, and every finding it printed is either fixed or one you looked at in the PNG and accepted on purpose (say which, and why, when you hand over)
- [ ] you looked at the PNG, not just the exit code
- [ ] every arrow is bound at both ends, with back-references
- [ ] every label sits inside its container and fits
- [ ] the depth level matches what was asked for
- [ ] palette roles are consistent, and readable on a light background
- [ ] seeds vary per element (the wobble is not identical everywhere)
- [ ] the `.excalidraw` source is what you commit; renders are not

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| File won't open / blank canvas | Missing boilerplate keys on an element | Include the full safe-default key set above |
| Label floats outside its shape | `containerId` set but no `boundElements` back-reference | Add both directions of the link |
| Arrow detaches when user drags a box | No `startBinding`/`endBinding` | Bind both ends + back-reference |
| Everything renders identical-wobble | Same `seed` on all elements | Vary seeds per element |
| Text renders in wrong font | `fontFamily` omitted | `"fontFamily": 1` for the sketch font |
