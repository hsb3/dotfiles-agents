---
id: DRAFT-004
title: >-
  Extender-component information architecture: scannable dependencies,
  assumptions, defaults
status: Draft
assignee: []
created_date: '2026-08-06 15:01'
labels:
  - decision
  - skills
  - extender-db
dependencies: []
type: spike
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Owner ask (2026-08-06): develop an information architecture that lets us scan and understand our extender components so we can manage them better: dependencies, assumptions, default settings.

Today, answering a management question about a primitive requires reading its body. Nothing scannable records what it depends on (CLI tools, MCP servers, env vars, other primitives), what it assumes about the host repo (a `_meta/` layout, a TTY, network, ports), or what its default settings are (thresholds, paths, ports) and which of those are overridable. Recent motivating examples: the context-watermark thresholds were hard-coded until 2026-08-06; owner-signoff assumes a `_meta/signoff/` batch dir and port 8737; the comms skill assumes `_meta/briefings/`. Discovering each meant reading the body.

This is a scoping task. It must resolve:

1. Storage: where the metadata lives (new roster fields, per-item frontmatter, or a separate manifest). Note `primitives-core.yaml` is deliberately provenance-only today, though it already has a `requires` field.
2. Vocabulary: dependencies / assumptions / defaults / override-mechanism, kept closed and machine-checkable.
3. Drift guard: how a `make ci`-style gate keeps the metadata honest against the bodies.
4. Query surface: make target, script, or an extension of the evals extender-db projection (which stays a projection, never a source of truth).
5. Migration cost across all 41 primitives (33 skills, 4 hooks, 4 agents).

Related: decision-8 (repo structure future-state); plugin membership stays in the symlink assemblies (`make members`), not in any new metadata.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A decision-ready proposal (ADR/decision draft) names the chosen storage location, schema, drift guard, and query surface
- [ ] #2 3-5 concrete management questions the architecture must answer are listed, each paired with the query that answers it
- [ ] #3 A migration estimate covers all 41 primitives
<!-- AC:END -->
