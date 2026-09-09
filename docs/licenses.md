# Licenses and attribution

This repository currently has no blanket license for its original work. Public visibility
by itself is not an open-source license. Preserve each component's existing notice; do
not apply one component's license to the whole marketplace.

| Material | Upstream and pin | License in this tree |
|---|---|---|
| Carbon builder | [carbon-design-system/carbon-mcp](https://github.com/carbon-design-system/carbon-mcp), `3cbe743d8bc36d6dd3bcfea98ac3ac09bca71f9c` | [Apache-2.0](../primitives-core/skills/carbon-builder/LICENSE) |
| PocketBase best practices | [greendesertsnow/pocketbase-skills](https://github.com/greendesertsnow/pocketbase-skills), `c573263e84a2066d0564f428dd8160e74fc54226` | [MIT](../primitives-core/skills/pocketbase-best-practices/LICENSE) |
| PPTX base, under the authored theme layer | [anthropics/skills](https://github.com/anthropics/skills), `fa0fa64bdc967915dc8399e803be67759e1e62b8`, `skills/pptx` | [Anthropic proprietary terms](../primitives-core/skills/pptx-themes/base/LICENSE.txt) |

The PPTX license explicitly restricts copying, derivative works and third-party
distribution. Keeping its notice does not resolve those restrictions. Public redistribution requires resolving both current and historical copies.
[Decision-018](decisions/decision-018%20-%20comm-skills-unify-on-one-engine-and-the-vendored-pptx-base-retires.md)
records the retirement direction and its capability-preservation requirements. This page
records the license finding; it does not retire the tool or grant a license.

The development-only plugins under `.claude/plugins/` retain their own Apache-2.0 notices
and attribution. They do not ship in the marketplace publication. Consult the
[provenance roster](../primitives-core.yaml), [external references](../externals.yaml)
and each plugin README for component scope. Historical versions retain their historical
license obligations.
