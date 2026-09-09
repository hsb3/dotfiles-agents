---
name: presentations
description: >-
  Create, inspect, edit and review PowerPoint decks and templates (.pptx/.potx).
  Use semantic palettes, deliberate typography, portable PptxGenJS source packages
  and rendered visual verification. Recurring briefing content goes through comms,
  which calls this skill for external decks.
---

# Presentations

Read [narrative](references/narrative.md), [palettes](references/color-palettes.md)
and [typography](references/typography.md) before choosing content or layout.
Use the user's design when following a supplied template. Otherwise choose a theme
by subject, state the choice, and verify the chosen font is installed.

## Create

Resolve paths beside this file, independent of the harness or installation directory.
Create a portable source package in a new directory whose parent exists:

```sh
python3 scripts/create-deck.py --type advisor --slug board-readout --out /tmp/board-readout
cd /tmp/board-readout
npm install --ignore-scripts
node deck.js
```

The package includes editable illustrative slides, native chart data and notes.
Replace example claims and sources before delivery. `status`, `advisor` and `client`
select audience-specific starting text. They impose no layout or content schema.
Direct PptxGenJS remains available through `deck.pptx` and the returned slides.
Copy `assets/theme-tokens.js` into older generators and change only their import;
all existing theme keys and exports remain. See [migration](references/migration.md).

Consume semantic tokens, never palette-specific hex in layout code. Set the same
fontFace on every text/table/chart call. Default to Avenir Next when installed;
use Arial/Calibri or supply the rendered PDF for recipients without that font.
Light themes use `canvas` for title and main slides; reserve `surfaceInverse` for
explicit dividers/panels. `midnight` stays on its dark canvas even for dividers.
Use ordered data-series tokens for charts and preserve editable chart data/notes.

## Inspect, edit and use templates

Read [editing and validation](references/editing.md) before editing an existing file.
Inspect its text, notes, dimensions, layouts, fonts and charts, then render the source.
Use `scripts/pptx.py inspect|edit|select|merge|validate --help` for the command contract.
Work to a new output file. Preserve supplied masters/layouts and edit the smallest
necessary part; keep a byte comparison of untouched parts and compare rendered slides.
For unsupported package features, retain the original and use its native application;
report the limitation before claiming preservation. Never rebuild a supplied template
from an image and describe it as the same editable structure.

## Render and verify

```sh
bash scripts/render-pptx.sh output.pptx /tmp/deck-review-new
python3 scripts/pptx.py validate output.pptx
```

Rendering needs Poppler (`pdftoppm`) plus LibreOffice or Microsoft PowerPoint on macOS.
The output directory must be new. It contains PDF, JPEG slides and a labeled HTML
contact sheet. Inspect every distinct layout, dense slide, title and closing slide.
Check text completeness, wrapping, clipping, alignment, contrast, font substitution
and footer collisions. Fix discovered problems and rerender to a fresh directory.
Structural validation does not prove layout quality or full ISO/ECMA XSD conformance.
Deliver source, PPTX, rendered PDF and the verification/limitations that matter.
