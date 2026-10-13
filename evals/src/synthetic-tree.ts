// A synthetic dotfiles-agents checkout with every case the spec lists: one
// roster entry of each type, a skill with references/ and scripts/, an agent
// whose tools is a block sequence, a folded description, a hook with hook.py,
// config.json and a .sh file, an id in both roster and externals, a standalone
// and a bundle plugin whose assemblies include hooks/_lib, commands/ and
// .mcp.json links, and a workflows table with non-ASCII guidance.
import { mkdirSync, symlinkSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";

function put(root: string, rel: string, content: string | Uint8Array): void {
  const path = join(root, rel);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content);
}

function link(root: string, rel: string, target: string): void {
  const path = join(root, rel);
  mkdirSync(dirname(path), { recursive: true });
  symlinkSync(target, path);
}

export const ROSTER_YAML = `# roster
version: 1

primitives:
  - id: mermaid
    type: skill
    source: primitives-core/skills/mermaid
    origin: authored
    disposition: qualified
    targets: [claude-code, codex]
    shelf: core
  - id: pocketbase-best-practices
    type: skill
    source: primitives-core/skills/pocketbase-best-practices
    origin: vendored
    upstream: https://github.com/greendesertsnow/pocketbase-skills
    ref: c573263e84a2066d0564f428dd8160e74fc54226
    disposition: qualified
    targets: [claude-code]
  - id: builder
    type: agent
    source: primitives-core/agents/builder.md
    origin: authored
    disposition: grandfathered-pending-use
    targets: claude-code
    requires: [atelier]
    assumes: [path:_meta/plans, port:8737]
  - id: context-watermark
    type: hook
    source: primitives-core/hooks/context-watermark
    origin: authored
    disposition: qualified
    targets: [claude-code, codex]
    summary: Warns when the context window fills up.
  - id: prepare-compact
    type: command
    source: primitives-core/commands/prepare-compact.md
    origin: authored
    disposition: qualified
    targets: [claude-code]
  - id: carbon-design-server
    type: mcp
    source: primitives-core/mcp/carbon-design.json
    origin: authored
    disposition: qualified
    requires: hosted-mcp
    targets: [claude-code, codex]
  - id: missing-skill
    type: skill
    source: primitives-core/skills/missing-skill
    origin: sourced
    disposition: untriaged
    targets: null
other_key: ignored
`;

export const EXTERNALS_YAML = `externals:
  - id: kata
    kind: plugin
    upstream: https://github.com/hsb3/kata-oversight
    path: plugins/kata
    ref: fced756974bed7c7288276568d43e83759218e6b
    provides: "Archived reference only."
    targets: [claude-code, codex]
  - id: skill-creator
    kind: skill
    upstream: https://github.com/anthropics/skills
    path: skills/skill-creator
    ref: 0123456789abcdef0123456789abcdef01234567
    provides: "Anthropic's skill authoring skill."
    targets: [claude-code]
  - id: pocketbase-best-practices
    kind: skill
    upstream: https://github.com/greendesertsnow/pocketbase-skills
    ref: c573263e84a2066d0564f428dd8160e74fc54226
    provides: "Vendored too."
`;

export const MERMAID_SKILL = `---
name: mermaid
description: >-
  Draw diagrams with Mermaid
  when a picture helps.
allowed-tools: [Read, Write]
---

# Mermaid

Use mermaid fences.
`;

export const BUILDER_AGENT = `---
name: builder
description: Builds one slice.
tools:
  - Read
  - Edit
model: sonnet
color: green
---
You are the builder. Build carefully.
`;

export const HOOK_PY = `#!/usr/bin/env python3
import json, os.path as osp
import sys
from pathlib import Path
from . import helpers
from .lib import thing
import requests  # third party
from yaml.loader import SafeLoader
    import notatoplevel
`;

export const COMMAND_MD = `---
description: Update the handoff and prepare a compaction prompt that preserves live work.
---

Invoke the \`atelier:compact-handoff\` skill and follow it.
`;

export const MCP_JSON = `{"mcpServers": {"carbon-design": {"type": "http", "url": "https://mcp.carbondesignsystem.com/mcp"}}}\n`;

export const MARKETPLACE = {
  name: "dotfiles-agents",
  metadata: { version: "0.13.1", description: "Plugins for coding sessions" },
  plugins: [
    { name: "atelier", source: "./plugins/atelier", version: "0.39.0", description: "Delegate work to model-tiered agents", author: { name: "Owner" } },
    { name: "mermaid", source: "./plugins/mermaid", version: "1.0.0", description: "Diagrams" },
    { name: "empty", source: "./plugins/empty" },
  ],
};

export const WORKFLOWS_MD = `# Workflows

Intro text.

## Choose a workflow

| Stage | Current marketplace plugin(s) | Choose them when |
| --- | --- | --- |
| Start a project | [atelier](../plugins/atelier/README.md), [mermaid](../plugins/mermaid/README.md) | Use atelier to plan — then draw it → ship. |
| Release | [atelier](../plugins/atelier/README.md) | Use its contract before release. Ünïcödé ✓ |

## Practical starts

Text.
`;

// Writes the synthetic checkout under root (which must exist and be empty).
export function writeSyntheticTree(root: string): void {
  put(root, "primitives-core.yaml", ROSTER_YAML);
  put(root, "externals.yaml", EXTERNALS_YAML);
  put(root, ".claude-plugin/marketplace.json", JSON.stringify(MARKETPLACE, null, 2) + "\n");
  put(root, "docs/workflows.md", WORKFLOWS_MD);

  const skill = "primitives-core/skills/mermaid";
  put(root, `${skill}/SKILL.md`, MERMAID_SKILL);
  put(root, `${skill}/references/syntax.md`, "# Syntax\n");
  put(root, `${skill}/references/deep/flowchart.md`, "# Flowchart\n");
  put(root, `${skill}/scripts/render.py`, "print('render')\n");
  put(root, `${skill}/assets/logo.png`, new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0xff, 0xfe, 0x00, 0x01]));
  put(root, `${skill}/LICENSE`, "MIT\n");
  put(root, `${skill}/evals/cases.yaml`, "cases: []\n");
  put(root, `${skill}/notes.txt`, "notes\n");
  put(root, `${skill}/.hidden`, "skip me\n");
  put(root, `${skill}/.cache/x.md`, "skip me\n");
  put(root, `${skill}/__pycache__/render.cpython-314.pyc`, new Uint8Array([1, 2, 3]));
  put(root, "primitives-core/shared/linked.md", "linked file\n");
  link(root, `${skill}/linked.md`, "../../shared/linked.md");
  link(root, `${skill}/linked-dir`, "../../shared");

  put(root, "primitives-core/skills/pocketbase-best-practices/SKILL.md", "No frontmatter here.\n");

  put(root, "primitives-core/agents/builder.md", BUILDER_AGENT);

  const hook = "primitives-core/hooks/context-watermark";
  put(root, `${hook}/hook.py`, HOOK_PY);
  put(root, `${hook}/config.json`, '{"threshold": 0.8}\n');
  put(root, `${hook}/legacy.sh`, "#!/bin/sh\necho legacy\n");
  put(root, `${hook}/README.md`, "# Context watermark\n");
  put(root, "primitives-core/hooks/_lib/common.py", "X = 1\n");

  put(root, "primitives-core/commands/prepare-compact.md", COMMAND_MD);
  put(root, "primitives-core/mcp/carbon-design.json", MCP_JSON);

  link(root, "plugins/mermaid/skills/mermaid", "../../../primitives-core/skills/mermaid");
  put(root, "plugins/mermaid/README.md", "# mermaid\n");
  link(root, "plugins/atelier/agents/builder.md", "../../../primitives-core/agents/builder.md");
  link(root, "plugins/atelier/commands/prepare-compact.md", "../../../primitives-core/commands/prepare-compact.md");
  link(root, "plugins/atelier/hooks/context-watermark", "../../../primitives-core/hooks/context-watermark");
  link(root, "plugins/atelier/hooks/_lib", "../../../primitives-core/hooks/_lib");
  link(root, "plugins/atelier/.mcp.json", "../../primitives-core/mcp/carbon-design.json");
  put(root, "plugins/atelier/hooks/codex-hooks.json", "{}\n");
  put(root, "plugins/atelier/README.md", "# atelier\n");
}
