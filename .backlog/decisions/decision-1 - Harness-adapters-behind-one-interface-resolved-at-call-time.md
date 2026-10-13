---
id: decision-1
title: Harness adapters behind one interface resolved at call time
date: '2026-10-13 03:15'
status: accepted
---
## Context

The spec describes claude, opencode and codex with the same shape (argv, environment scrub and per-run homes, injection per kind, a stdout fold, a success test) but different details, and the trial, the smoke check and the grid must treat them alike. The adapters also share helpers (the trial record, JSONL parsing, number coercion) that live with the registry, so adapters and registry import each other.

## Decision

`src/harnesses.ts` defines one `Adapter` interface (exe, default model, scrub prefix, whether plugins are reported, whether duration is wall-clock, `canHost`, `runEnv`, `inject`, `argv`, `fold`, `succeeded`) and the `TrialRecord` a fold returns. Each harness is one module exporting an `Adapter` object (`claude.ts`, `opencode.ts`, `codex.ts`). `adapterFor` resolves the adapter with a `switch` at call time rather than a table built at module load, because the adapter modules import the registry's helpers and a load-time table could read an adapter binding before its module has initialised (an ES module cycle).

## Consequences

Trial and smoke code has no per-harness branches; adding a harness means one module and one `switch` arm. The cycle between the registry and the adapters is safe only while neither module touches the other's exports at load time. An adapter property that needs a registry value (codex's withheld provider keys, added in v1.1) is a getter for that reason; a plain property broke every CLI start with a TDZ error. The map shows the registry and each adapter linked both ways (helpers one way, adapter lookup the other).
