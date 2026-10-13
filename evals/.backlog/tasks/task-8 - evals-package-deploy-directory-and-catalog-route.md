---
id: TASK-8
title: 'evals package: deploy directory and catalog route'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:09'
updated_date: '2026-10-13 03:57'
labels: []
milestone: m-0
dependencies:
  - TASK-2
references:
  - packager
  - pocketbase-service
  - package-and-deploy
modified_files:
  - .groma/flows/package-and-deploy.md
  - .groma/systems/evals/containers/evals-cli/components/commands.md
  - .groma/systems/evals/containers/evals-cli/components/packager.md
  - pb_hooks/toolbox_catalog.pb.js
  - src/commands.ts
  - src/packager.ts
  - test/packager.test.ts
priority: high
type: feature
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The PocketBase service is deployed to Railway from a package directory the CLI builds deterministically: Dockerfile, start.sh, railway.toml, migrations, the catalog hook serving GET /api/toolbox/catalog, the catalog and its receipt, and the UI build. Builds the packager component and the catalog hook of the PocketBase service.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A package of the same inputs is byte-identical across runs and contains exactly the documented files, with Dockerfile, start.sh (executable) and railway.toml exactly as specified
- [x] #2 toolbox-catalog.json and toolbox-package.json match the documented shape, sort order and snapshots
- [x] #3 UI builds and catalog inputs that break any documented rule are refused with an error naming it, an existing --out or one inside --source-root is refused, and nothing is left behind on failure
- [x] #4 GET /api/toolbox/catalog answers 200 with the catalog for an authenticated user or superuser and 401 anonymously, against a real server
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun run build:ui && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. pb_hooks/toolbox_catalog.pb.js: GET /api/toolbox/catalog behind requireAuth, serving the packaged toolbox-catalog.json.
2. src/packager.ts: --out checks (absent, not inside --source-root), UI build validation, catalog inputs (regular files, no symlinks, manifest plugins, workflow table rules), catalog and receipt with sorted keys and snapshots, exact Dockerfile/start.sh/railway.toml, copies of hooks, migrations and UI build; build in a staging directory and rename, removing everything on failure.
3. Wire the package command.
4. Tests: byte-identical repeated packages and exact file list, catalog/receipt contents, each refusal, nothing left behind, catalog route 200/401 against a server built from the package, and start.sh bootstrapping a real PocketBase twice. Gate, groma accept packager and relations, flow package-and-deploy, lint, finish.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Evidence: gate passes (112 tests). test/packager.test.ts: two packages of the synthetic checkout are byte-identical (paths, modes, content hashes) and hold exactly Dockerfile, start.sh, railway.toml, the hook, catalog, receipt, every migration and pb_public; Dockerfile, start.sh and railway.toml equal the blocks extracted from SPEC.md, start.sh is executable; toolbox-catalog.json and toolbox-package.json equal the expected objects serialised with sorted keys, 2-space indent and final newline, with source/migrations/ui snapshots recomputed in the test; refusals each exit 1 and leave no --out and no created parents: existing --out, --out inside --source-root, missing UI build (`no UI build at <dir>; run bun run build:ui`), source map, .env file, node_modules, private* path, symlink, external/protocol-relative/parent asset refs, missing asset, wrong header, bad separator, short row, empty cell, mislabelled link, unknown plugin, no link, empty workflow id, disagreeing rows, no table, symlinked docs/, duplicate manifest names; the repository ui/dist packages too. Against PocketBase 0.40.5 run from the package migrations and hooks: GET /api/toolbox/catalog is 401 anonymous and 200 with the packaged catalog for a user and a superuser, and the catalog is not served as a file; the packaged start.sh with POCKETBASE_BIN, PB_DATA_DIR, PB_BIND and PORT bootstraps the superuser, serves, and on a second start keeps the existing superuser; without PB_SUPERUSER_EMAIL it exits non-zero naming it. groma: accepted packager and its five planned relations, authored the store/canonical file relations, added flow package-and-deploy; scan created 0, lint clean.
Product calls: the workflow table may sit under a deeper heading and ends at the first non-table line; identical repeated rows of one workflow are merged, differing ones refused; a stage that is only punctuation is refused as an empty id; the package is assembled in `<out>.partial-<pid>` and renamed, so a failure removes it and any parents it created; only `*.js` files of pb_migrations are copied as migrations.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Built `evals package` (src/packager.ts) and the catalog route hook (pb_hooks/toolbox_catalog.pb.js): validated UI build and catalog inputs, deterministic catalog and receipt, exact Dockerfile/start.sh/railway.toml, copied migrations, hook and UI, built atomically. Verified by byte-identity, exact-content and refusal tests, the route against a server run from the package, and start.sh bootstrapping a real PocketBase twice.
<!-- SECTION:FINAL_SUMMARY:END -->
