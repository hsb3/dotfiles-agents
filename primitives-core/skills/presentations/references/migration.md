# Migrating from pptx-themes

`pptx-themes` is renamed to `presentations` in code-desk. The separate vendored
Anthropic `pptx` base is removed; its scripts and nested schemas have no new alias.

| Previous entry point | Replacement |
|---|---|
| `pptx-themes` skill | `presentations` |
| `pptx-themes/assets/theme-tokens.js` | `presentations/assets/theme-tokens.js`, identical theme keys/export contract |
| Absolute plugin-cache imports in `deck.js` | Copy theme tokens into the deck project and use a relative import, or create a portable package |
| Existing hand-laid `deck.js` | Keep PptxGenJS authoring; `assets/deck-kit.js` optionally supplies repeated layout helpers |
| Comms `slides.json` / spec input | Existing `comms/scripts/deliver.py`, unchanged |
| Read text, notes, package contents | `pptx.py inspect` plus rendered slide review |
| Fill template text / edit existing deck | `pptx.py edit`, preserving untouched parts; arbitrary object edits use the native application |
| Duplicate, reorder, split, merge | `pptx.py select` / `merge`; see supported feature boundaries in editing.md |
| Thumbnail grid / PDF conversion | `render-pptx.sh`, PDF + slide JPEGs + labeled HTML contact sheet |
| OOXML validation | `pptx.py validate` structural checks plus native render; full XSD conformance requires a separate validator |

No schema/deck/package output is tracked or regenerated during repository CI. The
spike's declarative YAML compiler remains a separate experiment: only the useful
layout helpers and portable-package approach are promoted here. Existing consumers
do not require new recipes or a new dependency for their JSON path.

Runtime dependencies are installed into the generated deck project, not a global
plugin cache. Packages declare PptxGenJS 4.0.1 (MIT, Brent Ely), obtained from npm with
its notices/transitive licenses. The source package contains authored helpers only.

### Unused image parser removal

PptxGenJS 4.0.1 declares `image-size` but does not import it in its published runtime.
That unused dependency has ICNS/JXL/HEIF denial-of-service advisories
([ICNS](https://github.com/advisories/GHSA-w3rx-r6r6-pgpr),
[JXL/HEIF](https://github.com/advisories/GHSA-5p2g-fcmc-qvqq)). The upstream
[removal PR](https://github.com/gitbrent/PptxGenJS/pull/1529) is still unmerged.

Generated packages keep official PptxGenJS 4.0.1 unchanged and use npm's scoped
override to replace its unused parser with the local `deck-kit/unused-image-size`
package. This authored module only throws an explanatory error: no image parser
implementation is installed or invoked. The direct local dependency plus `$image-size`
override keeps npm's resolution relative to the generated project, including after
moving it. This is dependency removal, not an advisory suppression or parser patch.

For a legacy `deck.js`, start with a generated source package and replace its example
`deck.js` with your source, retaining `package.json` and the local helper directory.
Keep this dependency graph in the dedicated deck project; do not transplant it into
an application that uses `image-size` itself. Images, notes and native charts still
work in PptxGenJS. An unexpected parser import fails visibly rather than inventing
image dimensions. Remove this workaround when a verified upstream release omits
the dependency; review and test the package graph whenever changing the pin.

Use `npm audit` and `npm ls image-size --all` in the generated project to inspect
the installed graph. A clean audit is time-specific evidence, not a security guarantee
for PowerPoint/LibreOffice or unrelated dependencies. Repository CI stays offline;
from the repository root, the installed-consumer check runs explicitly with
`PRESENTATIONS_PACKAGE=/path/to/installed/deck python3 -m unittest tests.test_presentations`.
