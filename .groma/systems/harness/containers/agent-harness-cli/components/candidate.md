---
type: C4 Component
title: Candidate
description: Recognizes the candidate's kind and parses its agent files
status: draft
groma:
  id: candidate
  parent: agent-harness-cli
  technology: TypeScript
  draft: v1
---

Resolves `--candidate-dir` to a skill (`SKILL.md`), a plugin (`.claude-plugin/plugin.json`, with name and version) or a set of agents (top-level `.md` files other than `README.md`). A flat agent `.md` file is copied into a temp directory that is removed on exit. Parses each agent file's frontmatter into name, description, body, model and tools, and rejects a missing path, an unrecognizable kind and duplicate agent names with exit 2.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [candidate](candidate.md) | [candidate-extender](../../../../../externals/candidate-extender.md) | Reads the candidate | filesystem |
