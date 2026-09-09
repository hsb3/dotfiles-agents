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
The upstream release still depends on image-size with known denial-of-service
advisories (GHSA-w3rx-r6r6-pgpr, GHSA-5p2g-fcmc-qvqq). Do not feed untrusted images
to this authoring dependency. No forced downgrade or unsupported dependency override
is applied; review upstream fixes before changing the pin. This limitation is part
of the replacement review evidence, not a claim of an audit-clean dependency tree.
