# presentations

Create portable PowerPoint source packages, inspect and edit existing decks/templates,
and verify them through rendered slides. Ships in `code-desk` as the replacement and
rename of `pptx-themes`. The authored palettes, typography, narrative guidance and
render entry point continue here; the Anthropic base and nested schemas do not.

Install the code-desk bundle, then read [SKILL.md](SKILL.md).

```sh
claude plugin install code-desk@dotfiles-agents
```

Python's stdlib handles package creation and ZIP/XML operations. XML content types
are validated whether declared by part override or default extension. Install PptxGenJS in each generated project
for authoring, and Poppler plus LibreOffice/PowerPoint for rendering. These tools are
runtime prerequisites; repository tests remain stdlib-only and need no install.

The generated `deck.js` is editable source with an illustrative native chart and
speaker notes. It imports local helper/theme files, so it builds outside the source
checkout and plugin cache. Existing theme keys and direct PptxGenJS workflows remain.

[Migration](references/migration.md) maps old entry points and dependency limitations.
[Editing](references/editing.md) defines exact text edits, selection/merge preservation,
unsupported features and structural validation's boundary. No full XSD conformance
claim is made. Template work requires source/output rendering and part comparisons.

## Provenance

The existing authored theme/narrative/typography resources are retained. The small
PptxGenJS layout helper is promoted from the owner's `spike-make-decks` experiment;
its source hash and promotion changes are recorded in the repository's replacement
record. The package writer follows that experiment's portable local-assets approach.
The ZIP/XML tool and render argument handling are independently authored against
public format documentation and stdlib APIs. No Anthropic implementation, instructions,
license text or nested schema is copied into the replacement.

[PptxGenJS](https://github.com/gitbrent/PptxGenJS) is a separately installed MIT runtime
dependency. This skill does not grant a blanket license over the marketplace's work.
