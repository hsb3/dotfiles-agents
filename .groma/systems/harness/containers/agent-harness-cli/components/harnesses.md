---
type: C4 Component
title: Harnesses
description: 'Knows the three harnesses: names, default models, preflight and adapters'
status: draft
groma:
  id: harnesses
  parent: agent-harness-cli
  technology: TypeScript
  draft: v1
---

Validates harness names (an unknown one exits 3), holds each harness's default model, runs preflight (CLI on `PATH`, and the credential variables opencode and codex need), reads `<exe> --version` with a 30 s limit, lists the auth variables that are set, builds the scrubbed child environment and hands out the adapter for a harness.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [harnesses](harnesses.md) | [subprocess](subprocess.md) | Reads the CLI version | function call |
