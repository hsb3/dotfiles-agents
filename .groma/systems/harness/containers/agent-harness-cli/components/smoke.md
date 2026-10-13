---
type: C4 Component
title: Smoke
description: Checks that a candidate loads under each harness
status: draft
groma:
  id: smoke
  parent: agent-harness-cli
  technology: TypeScript
  draft: v1
---

For each cell, injects the candidate into an empty workspace exactly as a `with` trial would, sends `Reply with exactly: OK`, writes a raw-stdout smoke log and prints the smoke block: kind, plugins loaded, plugin errors, a non-zero exit and the loadability verdict. Writes no ledger row.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [smoke](smoke.md) | [candidate](candidate.md) | Loads the candidate | function call |
| [smoke](smoke.md) | [harnesses](harnesses.md) | Preflights each cell | function call |
| [smoke](smoke.md) | [trial](trial.md) | Runs the agent like a with trial | function call |
