---
name: drawio
description: Read, convert, and export draw.io / diagrams.net files. Use when the user has legacy .drawio or .drawio.png/.drawio.svg files to inspect, extract content from, convert to Mermaid or another format, or export headlessly to PNG/SVG from the command line - or asks about drawio, diagrams.net, or mxGraph XML. Covers the compressed and uncompressed XML formats, a Python decompression recipe, and the desktop app's CLI export flags.
---

# draw.io Files

draw.io (diagrams.net) files turn up in archives as unconverted `.drawio` sources. This skill covers reading them without the GUI, migrating their content to maintainable formats (usually Mermaid), and headless PNG/SVG export.

Scope: this skill owns the draw.io format and export mechanics. Which tool a *new* diagram should use → the selection guide in the `diagrams` skill; new repo-doc diagrams are usually Mermaid, not draw.io.

## The file format

A `.drawio` file is XML: an `<mxfile>` root with one `<diagram>` element per page. Two variants:

1. **Uncompressed** — the `<diagram>` contains a readable `<mxGraphModel>` with `<mxCell>` nodes. Newer draw.io versions default to this.
2. **Compressed (legacy)** — the `<diagram>` body is a base64 string of a **raw-deflate, URL-encoded** payload. Most archived files are this kind.

Also common: `.drawio.png` / `.drawio.svg` — normal images with the diagram XML embedded (PNG `tEXt` chunk / SVG `content` attribute), re-editable by draw.io.

### Decompress a legacy diagram (Python, stdlib only)

```python
import base64, zlib, urllib.parse, xml.etree.ElementTree as ET

def drawio_pages(path):
    """Yield (page_name, mxGraphModel_xml) per page, handling both variants."""
    for diagram in ET.parse(path).getroot().iter("diagram"):
        inner = list(diagram)
        if inner:                       # uncompressed: child element present
            xml_text = ET.tostring(inner[0], encoding="unicode")
        else:                           # compressed: text is b64(raw-deflate(urlencoded))
            raw = base64.b64decode(diagram.text.strip())
            xml_text = urllib.parse.unquote(
                zlib.decompress(raw, wbits=-15).decode("utf-8")
            )
        yield diagram.get("name", "Page"), xml_text
```

`wbits=-15` (raw deflate, no zlib header) is the detail everyone gets wrong.

### Reading the model

Inside `<mxGraphModel><root>`:

- `<mxCell vertex="1">` = node; label in `value` (may be HTML), position/size in child `<mxGeometry>`; `style` holds `shape=...;fillColor=...`.
- `<mxCell edge="1">` = connection; `source`/`target` reference vertex `id`s.
- Cells with `parent` pointing at a group/container cell are nested inside it.

To extract structure: collect vertices (id → stripped label), then edges (source label → target label). That node/edge list is exactly the input a Mermaid flowchart needs.

## Converting legacy diagrams

Preferred target is **Mermaid** (see the `mermaid` skill — house rule: strip parentheses/special characters from labels during conversion, legacy labels are full of them). Workflow:

1. Extract nodes + edges with the recipe above.
2. Emit `flowchart TD` with sanitized labels; map containers to `subgraph`.
3. Render and eyeball against a PNG export of the original (below) — draw.io layouts are freeform, so expect to re-group, not pixel-match.

Keep the original `.drawio` beside the conversion until the new source is reviewed; archive rather than delete.

## Headless export to PNG/SVG

The draw.io **desktop app** ships the exporter. macOS binary lives inside the app bundle; alias it once:

```bash
alias drawio="/Applications/draw.io.app/Contents/MacOS/draw.io"

drawio --export --format png --scale 2 --output out.png legacy.drawio
drawio --export --format svg --output out.svg legacy.drawio
drawio --export --format png --all-pages --output pages.png legacy.drawio   # pages-1.png, pages-2.png…
drawio --export --format png --page-index 1 --output page2.png legacy.drawio
```

Useful flags: `--scale 2` (crisp PNG for decks), `--border 10` (padding), `--transparent` (PNG only — mind the dark-mode caveat in the `diagrams` skill), `--crop` (trim to content).

- Install: `brew install --cask drawio` (macOS). Linux CI: the AppImage/deb works headlessly under `xvfb-run`.
- Exported pairs follow the SVG+PNG output-pipeline conventions in the `diagrams` skill (numbered files in the artifact's `diagrams/` folder).

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `zlib.error: invalid header` | Used default `wbits` | `zlib.decompress(raw, wbits=-15)` |
| Garbled `%3CmxGraphModel...` text | Skipped URL-decode step | `urllib.parse.unquote` after decompress |
| Empty export | Multi-page file, wrong page | `--all-pages` or `--page-index N` |
| Labels full of `<br>`/`<b>` | draw.io labels are HTML | Strip tags when extracting text |
| Export hangs in CI | No display server | Wrap in `xvfb-run` on Linux |
| Blurry PNG in a deck | Default 1x scale | `--scale 2` or higher |
