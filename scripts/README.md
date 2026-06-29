# scripts/ — the translation service

_Placeholder. The service is built in **Phase 3** (technical-plan §2.1, §9)._

Status: planned

## What goes here

The build-at-merge translation service and its drift guards. Inputs are the roster
([`../primitives-core.yaml`](../primitives-core.yaml)) and the config
([`../primitives-core-translation-config.yaml`](../primitives-core-translation-config.yaml));
outputs are the static bundles under [`../targets/`](../targets/) and the lock
([`../primitives-core-translation-results.json`](../primitives-core-translation-results.json)).

Planned entry points:

- **`translate`** — read roster + config, render each (primitive × target) per its capability cell,
  write `targets/` + `results.json`. Deterministic (stable ordering, no clocks in output).
- **`translate --check`** — CI mode: regenerate into a temp dir, diff against committed `targets/` +
  `results.json`, exit non-zero on drift. Generated artifacts are never hand-edited.
- **roster ↔ disk drift test** — every primitive on disk is registered; every roster entry exists.

## Conventions

- **stdlib-only** (python stdlib + `pyyaml`), mirroring `ant-update-openapi.py` (the reference drift-guard
  shape: `--check` CI mode, content-hash lock, weekly cron / auto-PR).
- `unsupported` cells **skip and record** in the lock — never emit a broken bundle.
- MVP first: skills (native) + agents (transform) + CC marketplace assembly. Defer mcp render + the
  CMA adapter; hooks ship CC-only.
