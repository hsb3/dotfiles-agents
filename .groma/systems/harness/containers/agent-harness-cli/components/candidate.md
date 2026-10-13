---
type: C4 Component
title: Candidate
description: Recognizes the candidate's kind and parses its agent files
status: stable
groma:
  id: candidate
  parent: agent-harness-cli
  technology: TypeScript
  draft: v1
  code:
    - scanner: typescript
      file: src/candidate.ts
---

Resolves `--candidate-dir` to a skill (`SKILL.md`, named after its directory), a plugin (`.claude-plugin/plugin.json`, with its name and version or their defaults) or a set of agents (top-level `.md` files other than `README.md`, sorted by filename), checked in that order. A flat agent `.md` file is copied into a temp directory that is removed when the command exits. Parses each agent file's frontmatter into name, description, body, model and tools. A missing path, a non-`.md` file, an unrecognizable kind and duplicate agent names fail with the spec's messages, which the caller turns into exit 2.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [candidate](candidate.md) | [candidate-extender](../../../../../externals/candidate-extender.md) | Reads the candidate | filesystem |
