---
type: C4 Component
title: Checkout
description: Reads a dotfiles-agents checkout without changing it
status: stable
groma:
  id: checkout
  parent: evals-cli
  technology: TypeScript
  draft: v1
  code:
    - scanner: typescript
      file: src/checkout.ts
---

Reads `--source-root`: the roster `primitives-core.yaml` and `externals.yaml` (parsed with `Bun.YAML.parse`, scalar list keys as one-item lists), each unit source with its YAML frontmatter and body, the files of a unit (skipping dot names and `__pycache__`, reading symlinked files through, sha256, language and role), `.claude-plugin/marketplace.json`, and plugin assemblies of symlinks under `plugins/<id>/`.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [checkout](checkout.md) | [dotfiles-agents-checkout](../../../../../externals/dotfiles-agents-checkout.md) | Reads roster, units, assemblies | filesystem, read-only |
