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
| Carbon builder skill, IBM / Carbon contributors | [carbon-mcp, `3cbe743`](https://github.com/carbon-design-system/carbon-mcp/tree/3cbe743d8bc36d6dd3bcfea98ac3ac09bca71f9c/public/skills/carbon-builder) | Skill frontmatter declares Apache-2.0; [full text](../primitives-core/skills/carbon-builder/LICENSE) and [attribution](../primitives-core/skills/carbon-builder/README.md) accompany the 15 unchanged base files. Upstream has no root LICENSE or NOTICE at this pin. | The sibling index has a separate licensed source, documented below; the skill declaration is not its grant. |
| PocketBase best practices, Patrick | [pocketbase-skills, `c573263`](https://github.com/greendesertsnow/pocketbase-skills/tree/c573263e84a2066d0564f428dd8160e74fc54226/skills/pocketbase-best-practices) | [MIT text and copyright](../primitives-core/skills/pocketbase-best-practices/LICENSE) retained from upstream; base content unchanged, authored routing/field notes separate. | Historical copies and notices must also be checked; current notice preservation does not certify past packages. |
| Presentations authoring and package tools | [Authored replacement and provenance](presentations-replacement.md) | Existing authored palettes and workflow plus independently written ZIP/XML tools; no blanket original-work license is selected. PptxGenJS is a separately installed MIT runtime dependency. | Replacement retirement was approved; historical distribution treatment remains separate. Runtime dependency advisories and capability limits are recorded with the replacement proof. |
| LangChain and LangSmith skills references | [langchain-skills, `b7a2a8f`](https://github.com/langchain-ai/langchain-skills/tree/b7a2a8fc363d1711456f83d24230535c9fff93eb); [langsmith-skills, `e8f4120`](https://github.com/langchain-ai/langsmith-skills/tree/e8f4120a876b80ced98bce1bb21d6b9f4d62cdb8) | Current reference-only tracker entries: no upstream bytes are copied, installed, or projected into this marketplace. | These current bookmarks make no license conclusion. Historical LangChain and LangSmith copies remain unresolved as recorded below. |

The public-docs index is byte-identical to [carbon-website `static/llms.txt`](https://github.com/carbon-design-system/carbon-website/blob/996791935ba9edc7977fc12d7b16548181402c14/static/llms.txt)
at `996791935ba9edc7977fc12d7b16548181402c14`, a revision predating our import.
The same tree contains the [prompting guide](https://github.com/carbon-design-system/carbon-website/blob/996791935ba9edc7977fc12d7b16548181402c14/src/pages/developing/carbon-mcp/prompts.mdx)
condensed in `references/prompting.md`. Its root [Apache-2.0 license](https://github.com/carbon-design-system/carbon-website/blob/996791935ba9edc7977fc12d7b16548181402c14/LICENSE)
names **Copyright 2018 IBM Corp.**; no additional LICENSE/NOTICE exists in that
complete pinned tree. Carbon 0.2.1 retains this attribution in its skill README and
adds a prominent modification notice to the condensation. The existing full Apache
text travels with both references. This resolves the previously unlocated index
grant and current website attribution gap, without changing the index or capability.

The Apache/MIT/proprietary license files present before the PPTX replacement were
verified byte-identical in source, a dereferenced plugin assembly, published `main`
and installed Codex caches on 2026-09-09. The OpenCode generator preserved those
notices for its two included skills; Carbon was excluded by its target roster.
These historical checks prove notice preservation, not permission or full runtime
compatibility. They do not establish the state of later releases or caches.

The current source replaces `pptx-themes` with `presentations`; see the
[replacement proof and capability limits](presentations-replacement.md). The
retirement approval gate in
[decision-018](decisions/decisions-018-comm-skills-unify-on-one-engine-and-the-vendored-pptx-base-retires.md)
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
| LangChain / Deep Agents / LangGraph skills | [langchain-skills, `c88193a`](https://github.com/langchain-ai/langchain-skills/tree/c88193a48f387560697e1152e32dc5fd239c83e4) | Eleven sourced entries. No license grant located in this pinned tree, README or package metadata. Copies include whitespace changes, omitted sections and changed examples; framework-selection instead matches [revision `5d7402b`](https://github.com/langchain-ai/langchain-skills/blob/5d7402bafb41d4751b755f7848d412827187ce40/config/skills/framework-selection/SKILL.md) byte-for-byte. No grant was located at that matching revision either. Permission remains unresolved; the archive roster pin is not the exact source for that entry. |
| LangSmith dataset, evaluator and trace skills | [langsmith-skills, `68c8bb6`](https://github.com/langchain-ai/langsmith-skills/tree/68c8bb6b4b7cb5b20870b7b6afb340f6c958b0e6) | No license grant located at this pin. Historical bodies differ in authentication examples as well as formatting. |
| Trail of Bits devcontainer setup | [skills, `cfe5d7b`](https://github.com/trailofbits/skills/tree/cfe5d7b1619e47fb5b38b7e2561dad7e5f1e89af/plugins/devcontainer-setup) | Eight unchanged source files plus generated copies. Upstream [CC BY-SA 4.0](https://github.com/trailofbits/skills/blob/cfe5d7b1619e47fb5b38b7e2561dad7e5f1e89af/LICENSE) requires attribution/license information and applicable modification/ShareAlike terms; the archive omitted the license. |
| Vercel find-skills | [skills, `2adcfe5`](https://github.com/vercel-labs/skills/tree/2adcfe5a4cce0ce5f4d5547a997b2a161ec5d127) | Upstream declares MIT in README/package metadata but supplies no standalone license at this pin. Historical body changes search examples; complete notice/provenance remains unresolved. |
| OpenSpec generated workflow skills | [OpenSpec, `6a3a126`](https://github.com/Fission-AI/OpenSpec/tree/6a3a1263fe4d5994716841c46acdd3c3d799c042) | Four generated bodies declare MIT. Upstream license names OpenSpec Contributors (2024); the archive omitted the full notice. All four bodies match the decoded upstream TypeScript instruction templates. |
| shadcn skill and assets | [ui, `d0fae52`](https://github.com/shadcn-ui/ui/tree/d0fae528221011f75a8c64a917073904c2847493/skills/shadcn) | MIT, copyright shadcn (2023). Thirteen source files include two PNGs and modified guidance; historical full license notice absent. |
| Anthropic skill-creator | [skills, `9d2f1ae`](https://github.com/anthropics/skills/tree/9d2f1ae187231d8199c64b5b762e1bdf2244733d/skills/skill-creator) | At archive commit `a0dae18c72736e4207496477730aaadc4dd76146`, all 18 files, including `LICENSE.txt`, match byte-for-byte in source and all three generated targets. The upload manifest lists the license. Earlier packages and actual uploads remain unverified. |
| RunComfy nano-banana-2 and derived prompting guidance | [runcomfy-skills, `94bff26`](https://github.com/agentspace-so/runcomfy-skills/tree/94bff26ecaa69dd425c7dffbf6479498672a3894/nano-banana-2) | Historical nano-banana-2 body matches exactly; MIT copyright RunComfy / agentspace-so (2026). Prompting material was later folded into nanobanana; the full upstream notice was not carried with those copies. |
| React Doctor | [react-doctor, `13b40e3`](https://github.com/millionco/react-doctor/tree/13b40e37d4e1e06a27d22e90981272fae3dcabf5/skills/react-doctor) | Body matches exactly; version moved into metadata locally. MIT at this revision, copyright Aiden Bai (2026); historical full notice absent. Later upstream terms must not be substituted for the copied revision. |
| Older Carbon, PocketBase and PPTX copies | Current source pins above; multiple prior paths | Older Carbon references match upstream even where the roster says authored; historical license/change notices still need delivery remediation. The index now has an exact Apache-licensed website source, as recorded above. PocketBase also appeared under `.agents/`; PPTX appeared under several plugin and generated-output paths. |

[Historical third-party notices](historical-third-party-notices.md) now preserve the
exact OpenSpec, shadcn, RunComfy and React Doctor MIT texts, plus Trail of Bits creator,
source, license and disclaimer attribution. These accompany new source documentation;
**old archive downloads and generated packages remain unchanged**. The document is
not included by the current marketplace lift, which does not ship those components.

Historical files without a verified source remain outside this clearance.
Unknown provenance is not first-party authorship. A complete public-release decision
must account for all affected refs, tags, source archives and remaining PR/cache
copies, not only the current files in this table.

## Consumer release and historical visibility decisions

These verdicts address the identified third-party distribution findings, not general
runtime compatibility, first-party licensing or a categorical legal clearance. A
historical public-visibility hold does not automatically block every private
remediation release; evaluate the bytes actually redistributed. A full marketplace
publication also redistributes unchanged plugins; removing a plugin from current source does not settle retained historical copies.

| Current plugin / surface | Verdict and concrete remedy |
|---|---|
| Carbon 0.2.1 | Current base/index grants are evidenced and website attribution is repaired. Verify the new README, prompting notice and full license in the final published/installed version; old caches do not acquire them automatically. Historical modified Carbon copies still need their notices delivered with the retained distributions. |
| PocketBase | No current third-party notice defect found: all 77 base files match the pin and the full MIT notice is retained. Historical `.agents/` and generated copies need separate notice coverage; current proof is not retroactive. |
| code-desk 0.14.0, diagrams 0.3.1, solo-skills 0.16.1 | No identified blocker from the restricted PPTX base/schemas or the listed historical copied skills in the reviewed assemblies: code-desk now has 77 files after the board-triage move (87 at PR530), diagrams 18 and solo-skills 92. All 56 old base files, including 39 schemas, have no exact-byte match; presentations has no shared 20-token passage with the old base. PptxGenJS is installed separately, not bundled. Retained authored provenance and synthetic proof-image origins are documented by the replacement work, with the independent-verification limits below. Historical copies remain separate. |
| kenn-forge (retired) | The current skill, plugin assembly, install claims, and marketplace projection are retired. The reproduced overlap measurements remain historical audit evidence and do not establish independent authorship; retained historical copies remain unresolved below. |
| Other current plugins | No additional current copied component identified by this targeted follow-up; this is not a new exhaustive authorship audit or a first-party license grant. Development-only Anthropic copies and external runtime dependencies retain the scope described above. |

The three replacement assemblies were built from PR530 head `2308e8b`, merged as
`2311799fe5c762d5c3ff2cfc0b983d24666f8c7c`. The subsequent board-desk merge
`a5cebdc328a9e5209cc9764ec46a69300a62b8d9` removes ten board-triage files from
code-desk (now 0.14.0, 77 tracked assembled files) and changes its manifests/README;
its presentations bytes, diagrams and solo-skills remain unchanged. No XSD, PPTX/PDF/ZIP package or
`node_modules` is shipped in them. The theme tokens, narrative reference and sampler
match the prior layer outside `base/`; the promoted helper's original SHA-256 matches
the private spike's file and the [replacement record](presentations-replacement.md).
These comparisons cannot establish the origin of every line or exclude shorter
fragments/paraphrased derivatives. The spike has no committed provenance chain; the
two PNG proof-image origins rely on the replacement's recorded synthetic capture
procedure rather than a new independent capture in this audit.

For the retired kenn-forge skill, the reproducible comparison source is [kenn-io/forge
`306610c81a2e67ab16c42b683dfd29e91d4dd2c5`](https://github.com/kenn-io/forge/tree/306610c81a2e67ab16c42b683dfd29e91d4dd2c5):
`docs/kenn-forge-mcp.md` plus `internal/mcpserver/guidance.md`, compared with local
import `ee391d14bdbe3a82213af1b309015a575ae6867c`. Lowercasing and tokenizing with
Python `re.findall(r'\w+', text)` yields an eight-token longest match; splitting
sentences at `(?<=[.!?])\s+` yields no matching sentences of eight or more tokens.
Alphanumeric-only tokenization gives a nine-token match, so the count is
method-dependent. These are textual measurements, not a copyright test.
The upstream [NOTICE](https://github.com/kenn-io/forge/blob/306610c81a2e67ab16c42b683dfd29e91d4dd2c5/NOTICE)
explicitly retains MIT for contributions through `4b28941cbbc27b30747e39269ba86c0cb2a3e92c`;
later contributions use ELv2. A later license does not erase that earlier grant.
The two comparison documents entered after the cutoff; this does not identify the
origin of every sentence. Recommended remedy: establish independent authorship or
review the applicable upstream terms and accompany any retained adaptations with
those terms, copyright and prominent change notices. Do not simply label them MIT.

The remaining historical/public-visibility decisions are:

| Component and surface | Recommended concrete remedy / decision still required |
|---|---|
| LangChain / Deep Agents / LangGraph (11 skills), LangSmith (3 skills), including corrected framework-selection source; archived source and three generated targets | Locate an applicable grant or obtain permission; otherwise present exact ref/path history treatment for owner approval. Library licenses do not license these separate skill repositories. |
| Vercel find-skills; archived source and generated targets | Resolve complete copyright/permission notice at the copied revision or evidenced earlier source. README/package MIT declarations alone do not supply the missing holder/date; do not invent them. |
| Trail of Bits devcontainer setup; archived source and three generated targets | Deliver creator/source/license/disclaimer notices with retained copies and identify actual adaptations. Approve and apply permitted ShareAlike terms where required, scoped to that material. Current supplemental documentation does not settle old packages or adaptation grants. |
| OpenSpec (4 workflows), shadcn (13 files including 2 PNGs), RunComfy nano-banana-2 plus derived nanobanana prompting, React Doctor; archived source/generated copies | The exact MIT notices are prepared. Decide how every retained download receives them: a corrected distribution plus notices, or separately scoped history treatment. A new document cannot amend an old tarball. Preserve image attribution; copyright permission does not imply trademark endorsement. |
| Carbon historical resources, index and prompting condensations; prior source/plugin/generated paths | Use the evidenced skill and website Apache grants; deliver full license, copyright and prominent change notices for every retained modified copy. Exact current index provenance does not repair missing historical notices. |
| PocketBase historical source, `.agents/`, prior plugin/generated paths | Compare every retained distribution with the pinned MIT text and include it wherever missing. |
| Anthropic skill-creator before the verified archive snapshot, actual hosted uploads and caches | Preserve Apache terms and any change notices. The verified 18-file source/three-target snapshot needs no repair; it does not prove all earlier uploads. |
| PPTX base, wrapper and 39 nested schema files; historical source/plugin/generated paths, tags and PR refs | Current replacement does not clear retained copies. Approve exact history/distribution treatment separately. The schema groups are 27 under `ISO-IEC29500-4_2016` (including W3C `xml.xsd`), 4 under `ecma/fouth-edition`, 7 Microsoft extensions and `mce/mc.xsd`. The last explicitly derives from an unpinned docx4j schema. Identify original revisions and independently applicable terms for each group before any salvage; namespace names and the Anthropic pin are not grants. |
| kenn-forge prior skill copies | Resolve the authorship/terms decision above, then carry required notices through every retained distribution. Its current marketplace entry is retired; that does not resolve historical copies. |
| First-party source and unknown provenance | Owner chooses any original-work license separately. Unmatched text is not proof of authorship. Investigate identified provenance gaps before claiming public release readiness. |
| All affected refs, tags, releases, GitHub source archives and PR/cache copies | Refresh the scope map after final merges and before any approved history action. The earlier 139-ref rehearsal predates this wave, preserves archive refs and does not clear these findings. No shared rewrite, archive deletion, visibility change or credential action is authorized by this document. |

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
