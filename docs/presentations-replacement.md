# Authored presentations replacement

`pptx-themes` is renamed to `presentations` in code-desk. The replacement removes
Anthropic's vendored `pptx` base, its wrapper license copy, evaluation artifact and
nested schemas. The owner approved this focused retirement and authorized lead-owned
merge/publication coordination on 2026-09-10, subject to verified green checks.
It does not retire owner-signoff, consolidate comms or alter Git history. Historical licensing findings remain
with t80e/gek8 and [licenses.md](licenses.md).

## Source provenance

The retained authored layer comes from source dev `84101f6`: semantic theme tokens,
color/typography references, narrative guidance and the theme sampler. These existed
outside the restrictive base. Their content is retained, with route/name corrections.
The misleading wrapper-level Anthropic license is removed with the base rather than
applied to new first-party work. No new blanket first-party license is selected.

The owner directed promotion from `/Users/henry/Developer/LEARNING/spike-make-decks`.
That local private experiment has no commits or remote. Its README/HANDOFF and source
identify it as the owner's portable-deck laboratory, derived from existing authored
consumers. The promoted `src/deck-kit.js` SHA-256 before changes is
`3059d595111a60bcaf64ab292abd705d16ccf337de82a50f15dd3e8f26b70904`.
Changes use the existing full theme source, reject unknown themes, and write generated
PPTX through a temporary file. The portable package approach is retained with an
independent stdlib writer. The spike's competing two-theme file, YAML compiler,
AJV/YAML dependencies and generated schemas are not promoted.

The ZIP/XML editor and renderer argument handling were written independently against
Python's ZIP/XML APIs and Microsoft's public PresentationML structure documentation.
No restrictive base implementation, prose, eval or nested schema was consulted as an
implementation template or copied into presentations. PptxGenJS is an external runtime
dependency, pinned to npm 4.0.1, MIT (Brent Ely); no dependency bytes are tracked.

## Capability and migration map

The [shipped migration reference](../primitives-core/skills/presentations/references/migration.md)
maps every old entry point. Direct hand-laid `deck.js` and comms `slides.json` remain.
Comms, dataviz and diagrams now route to `presentations`; old absolute theme imports
become relative copies of the unchanged theme module. Generated source packages work
outside the checkout/cache and include illustrative chart data and speaker notes.

Independent package operations provide ordered text/notes/font/chart inspection,
exact paragraph edits across formatting runs, template-to-deck output, selection,
reordering, splitting, merging and duplication by merge/select. The authored render
entry point produces PDF, slide JPEGs and a labeled HTML contact sheet. Raw slide
objects are still editable in the native application or their PptxGenJS source.

## Retirement review decisions

- Full ISO/ECMA XSD conformance is replaced by structural validation plus application
  rendering. The old nested schema rights are unresolved. No schema bytes are salvaged.
- Exact paragraph replacement adopts the first run's formatting. Arbitrary rich-text,
  object/chart edits and unsupported package features use a native application on a copy.
  Merge preserves slide-level part graphs; deck-wide settings come from the first deck.
  The editing reference names unsupported comments/custom shows/extensions and strict OOXML.

The owner approved the replacement/rename, editing boundaries and structural-validation
change on 2026-09-09 after reviewing PR #530. These are explicit limits, not an assertion
of unrestricted feature parity. The owner requested a remedy for the remaining
dependency advisories instead of accepting that exposure.

PptxGenJS 4.0.1 declares but never imports `image-size`. Its official release remains
unchanged; generated packages substitute a local module that throws if imported for
that exact version's unused dependency. No vulnerable parser bytes are installed.
The [migration reference](../primitives-core/skills/presentations/references/migration.md)
explains the native npm override, legacy-package migration and upstream removal trigger.
The source package remains portable, with no global configuration changes or vendored
runtime dependency. Fresh installation/audit and image/chart/notes consumer checks
verify the remedy independently of the zero-install repository checks.

Alternatives investigated: `image-size-next` 1.2.2 is an MIT community fork retaining
the 1.x API; direct tests reproduce the original ICNS/JXL failures and confirm that
fork completes. It is unnecessary when the caller uses no parser. Switching to
`pptxgenjs-plus` would change the authoring engine and dependency tree. The upstream
manifest-only removal PR remains unmerged, and this environment disables Git dependency
installs. None of those alternatives is shipped or silently substituted for PptxGenJS.

The owner reviewed the dependency remedy/examples and approved them on 2026-09-09.
The lead owns the final PR #530 checks, merge and publication; historical rights and
public visibility remain separate from this replacement's retirement clearance.

## Roadmap

[The replacement review](https://github.com/hsb3/dotfiles-agents/pull/530) tracks the rollout;
implementation decisions and evidence live on kata `dotfiles-agents#rqen`. These are the
live records, rather than a second task list in the skill. The next dependency milestone
is a verified upstream release that removes the unused parser declaration.
