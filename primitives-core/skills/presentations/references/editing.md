# Existing decks and templates

The independent `scripts/pptx.py` works directly on ZIP parts with Python's stdlib.
It never extracts a package into a filesystem tree and never fetches external links.
Its format model follows the public [PresentationML structure documentation](https://learn.microsoft.com/en-us/office/open-xml/presentation/structure-of-a-presentationml-document).
No bundled third-party implementation or schema is required.

```sh
python3 scripts/pptx.py inspect source.pptx > inspection.json
python3 scripts/pptx.py edit source.pptx --edits edits.json --output revised.pptx
python3 scripts/pptx.py select source.pptx --slides 3,1 --output selected.pptx
python3 scripts/pptx.py merge first.pptx second.pptx --output combined.pptx
python3 scripts/pptx.py validate revised.pptx
```

`edits.json` is an array such as
`[{"slide": 1, "old": "Original title", "new": "Revised title"}]`.
Each edit matches exactly one complete paragraph on the numbered slide, including
text split across formatting runs. Replacement adopts the first run's formatting;
mixed formatting within that paragraph must be restored in the native application
if needed. Missing or ambiguous matches fail without writing output. Other slide
parts, masters, layouts, embedded chart workbooks, media and notes remain byte-identical.
This is suitable for filling text in an existing deck or `.potx` template. Saving
as `.pptx` changes the main content type to a presentation; `.potx` selects template.

Selection reorders/splits slides, removes discarded slide relationships and prunes
unreachable package parts. Review the result for retained shared/master content:
selection is not a confidential-data sanitization tool. To duplicate a slide, merge
the deck with itself and select the desired original/imported slide numbers.

Merge requires equal slide dimensions. It imports each input's parts under new
package names and rewrites relationships, preserving slide layouts, masters, notes,
charts and media. Original parts keep their bytes except package-level ordering,
relationships and content types. Deck-wide settings come from the first input.
Custom shows, sections/extensions, comments and cross-slide navigation require native
application review; do not claim they are preserved by merge. Selection refuses
custom shows/extensions rather than silently leaving their ordering metadata stale.
Signed/macro packages cannot be edited. Strict-namespace OOXML is unsupported.

## Validation boundary

Checks cover ZIP names, duplicate/encrypted/symlink entries, expanded size limits,
DTD/entity rejection, XML parsing, content-type coverage, relationship IDs/targets,
XML relationship references, slide order/IDs and required presentation roots.
Unused content-type declarations are allowed, as emitted by PptxGenJS.
Inputs are limited to 10,000 entries and 256 MiB expanded; use a native application
for larger decks. Outputs must be new `.pptx`/`.potx` files in an existing directory.

**Full ISO/ECMA XSD validation is not implemented.** This is an explicit capability
change from the retired base, pending the replacement's owner approval. No nested
schemas were copied. Rendering plus these checks provides package and visual evidence,
not a standards-conformance certificate. A workflow needing that certificate must
use an independently obtained/licensed validator and record its result separately.

Inspect lists slide text, notes, chart part names, relationships and declared fonts.
It does not infer the meaning of images or chart data. Read chart/workbook data with
appropriate spreadsheet tooling, and inspect rendered images for visual analysis.
For arbitrary object, chart-data or theme edits, use the source generator when present
or PowerPoint/LibreOffice on a copy. Re-run inspection and visual comparisons afterward.
