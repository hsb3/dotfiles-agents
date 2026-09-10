# Licenses and attribution

This repository has no blanket license for its original work. Public visibility is
not an open-source license. Individual grants, including existing first-party
license notices, keep their own scope; no component's terms license the entire
marketplace.

**Redistribution review is incomplete.** The tables distinguish verified notices
from unresolved rights. A provenance pin, attribution line or passing drift check
does not establish permission to distribute every file.

## Current marketplace components

| Material and holder | Source revision | License and evidence | Remaining scope |
|---|---|---|---|
| Carbon builder skill, IBM / Carbon contributors | [carbon-mcp, `3cbe743`](https://github.com/carbon-design-system/carbon-mcp/tree/3cbe743d8bc36d6dd3bcfea98ac3ac09bca71f9c/public/skills/carbon-builder) | Skill frontmatter declares Apache-2.0; [full text](../primitives-core/skills/carbon-builder/LICENSE) and [attribution](../primitives-core/skills/carbon-builder/README.md) accompany the 15 unchanged base files. Upstream has no root LICENSE or NOTICE at this pin. | The separately copied `public/llms.txt` is outside the skill subtree; the skill's declaration alone does not establish a grant for that file. |
| PocketBase best practices, Patrick | [pocketbase-skills, `c573263`](https://github.com/greendesertsnow/pocketbase-skills/tree/c573263e84a2066d0564f428dd8160e74fc54226/skills/pocketbase-best-practices) | [MIT text and copyright](../primitives-core/skills/pocketbase-best-practices/LICENSE) retained from upstream; base content unchanged, authored routing/field notes separate. | Historical copies and notices must also be checked; current notice preservation does not certify past packages. |
| Presentations authoring and package tools | [Authored replacement and provenance](presentations-replacement.md) | Existing authored palettes and workflow plus independently written ZIP/XML tools; no blanket original-work license is selected. PptxGenJS is a separately installed MIT runtime dependency. | Replacement retirement approval remains required; runtime dependency advisories and capability limits are recorded with the replacement proof. |

The Apache/MIT/proprietary license files present before the PPTX replacement were
verified byte-identical in source, a dereferenced plugin assembly, published `main`
and installed Codex caches on 2026-09-09. The OpenCode generator preserved those
notices for its two included skills; Carbon was excluded by its target roster.
These historical checks prove notice preservation, not permission or full runtime
compatibility. They do not establish the state of later releases or caches.

The current source replaces `pptx-themes` with `presentations`; see the
[replacement proof and capability limits](presentations-replacement.md). The
retirement approval gate in
[decision-018](decisions/decision-018%20-%20comm-skills-unify-on-one-engine-and-the-vendored-pptx-base-retires.md)
still applies. Current-file removal does not remove earlier copies from Git history,
published packages or installed caches.

The former Anthropic, PBC PPTX base came from
[skills/pptx, `fa0fa64`](https://github.com/anthropics/skills/tree/fa0fa64bdc967915dc8399e803be67759e1e62b8/skills/pptx).
Its [proprietary terms](https://github.com/anthropics/skills/blob/fa0fa64bdc967915dc8399e803be67759e1e62b8/skills/pptx/LICENSE.txt)
prohibit copying, derivative works and third-party distribution; attribution does
not resolve that blocker. The 56 base files and wrapper notice were removed from
current source. Embedded OOXML schemas have further upstream origins and were not
salvaged into the replacement. Historical redistribution remains unresolved.

## Development copies and site dependencies

The three [development plugins](../.claude/plugins/README.md) are complete, unchanged
Anthropic Apache-2.0 copies at the exact revisions recorded there. Their license
texts and author manifests are present. Exclusion from the marketplace does not
exclude them from a source clone. No additional upstream NOTICE file exists within
those three pinned plugin subtrees.

The site renders canonical repository Markdown with an authored template and CSS.
It does not bundle the vendored skill bodies, fonts, icon packs or a JavaScript
package tree. Diagrams load Mermaid 11.12.0 from jsDelivr at runtime; those external
bytes remain subject to Mermaid's own license and bundled notices. Pandoc is a
build tool, not a binary shipped by this repository. Likewise, CLI/SDK installation
commands and MCP connection specifications name dependencies; they do not by
themselves redistribute their implementations. Review any later bundled output
separately, including its transitive dependencies and assets.

## Historical source and generated copies

The pre-restructure archive and earlier commits contain third-party material beyond
the current roster. Retaining an archive does not waive its obligations. This is an
inventory of identified findings, **not permission to rewrite or delete history**.

| Historical component | Primary source / recorded pin | Finding |
|---|---|---|
| LangChain / Deep Agents / LangGraph skills | [langchain-skills, `c88193a`](https://github.com/langchain-ai/langchain-skills/tree/c88193a48f387560697e1152e32dc5fd239c83e4) | Eleven sourced entries. No license grant located in this pinned tree, README or package metadata. Copies include whitespace changes, omitted sections and changed examples; the framework-selection body does not match the renamed upstream entry. Permission/provenance remains unresolved. |
| LangSmith dataset, evaluator and trace skills | [langsmith-skills, `68c8bb6`](https://github.com/langchain-ai/langsmith-skills/tree/68c8bb6b4b7cb5b20870b7b6afb340f6c958b0e6) | No license grant located at this pin. Historical bodies differ in authentication examples as well as formatting. |
| Trail of Bits devcontainer setup | [skills, `cfe5d7b`](https://github.com/trailofbits/skills/tree/cfe5d7b1619e47fb5b38b7e2561dad7e5f1e89af/plugins/devcontainer-setup) | Eight unchanged source files plus generated copies. Upstream [CC BY-SA 4.0](https://github.com/trailofbits/skills/blob/cfe5d7b1619e47fb5b38b7e2561dad7e5f1e89af/LICENSE) requires attribution/license information and applicable modification/ShareAlike terms; the archive omitted the license. |
| Vercel find-skills | [skills, `2adcfe5`](https://github.com/vercel-labs/skills/tree/2adcfe5a4cce0ce5f4d5547a997b2a161ec5d127) | Upstream declares MIT in README/package metadata but supplies no standalone license at this pin. Historical body changes search examples; complete notice/provenance remains unresolved. |
| OpenSpec generated workflow skills | [OpenSpec, `6a3a126`](https://github.com/Fission-AI/OpenSpec/tree/6a3a1263fe4d5994716841c46acdd3c3d799c042) | Four generated bodies declare MIT. Upstream license names OpenSpec Contributors (2024); the archive omitted the full notice. A generated body still requires tracing its source template. |
| shadcn skill and assets | [ui, `d0fae52`](https://github.com/shadcn-ui/ui/tree/d0fae528221011f75a8c64a917073904c2847493/skills/shadcn) | MIT, copyright shadcn (2023). Thirteen source files include two PNGs and modified guidance; historical full license notice absent. |
| Anthropic skill-creator | [skills, `9d2f1ae`](https://github.com/anthropics/skills/tree/9d2f1ae187231d8199c64b5b762e1bdf2244733d/skills/skill-creator) | Skill body matches and Apache-2.0 license is retained. Generated copies and any modifications need their own preservation checks. |
| RunComfy nano-banana-2 and derived prompting guidance | [runcomfy-skills, `94bff26`](https://github.com/agentspace-so/runcomfy-skills/tree/94bff26ecaa69dd425c7dffbf6479498672a3894/nano-banana-2) | Historical nano-banana-2 body matches exactly; MIT copyright RunComfy / agentspace-so (2026). Prompting material was later folded into nanobanana; the full upstream notice was not carried with those copies. |
| React Doctor | [react-doctor, `13b40e3`](https://github.com/millionco/react-doctor/tree/13b40e37d4e1e06a27d22e90981272fae3dcabf5/skills/react-doctor) | Body matches exactly; version moved into metadata locally. MIT at this revision, copyright Aiden Bai (2026); historical full notice absent. Later upstream terms must not be substituted for the copied revision. |
| Older Carbon, PocketBase and PPTX copies | Current source pins above; multiple prior paths | Older Carbon references match upstream even where the roster says authored; license/change notices and the separately copied docs index need review. PocketBase also appeared under `.agents/`; PPTX appeared under several plugin and generated-output paths. |

Historical files without a verified source remain outside this clearance.
Unknown provenance is not first-party authorship. A complete public-release decision
must account for all affected refs, tags, source archives and remaining PR/cache
copies, not only the current files in this table.

## Applying the terms

[Apache-2.0 section 4](https://www.apache.org/licenses/LICENSE-2.0) requires a license
copy, retention of applicable notices, prominent change notices on modified files,
and relevant NOTICE contents when upstream supplies them. MIT requires the
copyright and permission notice in copies or substantial portions.
[CC BY-SA 4.0 section 3](https://creativecommons.org/licenses/by-sa/4.0/legalcode.en)
requires attribution, license information and modification indications, with
ShareAlike terms for adapted material. These grants do not imply trademark
endorsement or grant rights that the licensor does not own.

Preserve upstream notices when assembling packages or rendering copied documentation.
Resolve absent or incompatible rights through evidenced permission, compliant
notices, removal or independent replacement. A scanner and a manifest cannot choose
between those remedies. See the [provenance roster](../primitives-core.yaml) and
[external references](../externals.yaml) for current component intent.
