---
id: TASK-7
title: site serve preview
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:07'
updated_date: '2026-10-13 03:24'
labels: []
milestone: m-0
dependencies:
  - TASK-6
references:
  - server
  - maintainer
  - preview-locally
  - commands
modified_files:
  - .groma/actors/maintainer.md
  - .groma/systems/docs/containers/site-cli/components/commands.md
  - .groma/systems/docs/containers/site-cli/components/server.md
  - README.md
  - src/commands.ts
  - test/cli.test.ts
  - .groma/flows/preview-locally.md
  - src/server.ts
  - test/server.test.ts
priority: medium
type: feature
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Maintainers need to see the built site as Pages will serve it, under the base path, before pushing. Builds the groma ghost `server` (src/server.ts) and the `serve` command.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `site serve [build options] [--port N]` builds, prints the build line and `Serving http://127.0.0.1:<port><base>/ (Ctrl-C to stop)`; port 8000 by default, `0` picks a free one
- [x] #2 `<base>/` and paths ending in `/` get that folder's `index.html`; other paths under the base get the file
- [x] #3 Paths outside the base, missing files and paths escaping the output folder get 404
- [x] #4 A failed build or a taken port exits 1; serve never rebuilds
- [x] #5 README.md documents the serve command
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. src/server.ts: startServer({output, base, port}) runs Bun.serve on 127.0.0.1; resolveRequest maps <base>/ and paths ending in / to index.html, other paths under <base>/ to the file; outside the base, missing files, non-files, encoded slashes, dot segments and anything whose realpath leaves the output folder get 404; only GET and HEAD.
2. src/commands.ts: 'serve' takes the build options plus --port N (0-65535, default 8000), runs the build (exit 1 on failure), prints the build line and 'Serving http://127.0.0.1:<port><base>/ (Ctrl-C to stop)', and exits 1 with 'serve: port <N> is taken' when the port is in use. Never rebuilds.
3. Tests: test/server.test.ts (routing and 404s against a built fixture on port 0) and serve cases in test/cli.test.ts (spawned process, port 0, taken port, failed build).
4. README serve section.
5. Gate, scan, accept server + relations (commands->server, server->site-output, maintainer->server), flow 'Preview locally', lint, finish.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Product calls: `<base>` without the trailing slash is 404 (the spec says everything outside `<base>/` is); encoded slashes, empty and dot segments, malformed escapes and symlinks leading out of the output folder are 404; methods other than GET/HEAD get 405; a bad --port prints usage (exit 1); a taken port prints `serve: port <N> is taken` after the build line and exits 1; the address line uses the real port when --port 0.
Evidence: `bunx tsc --noEmit && bun test` -> 119 pass, 0 fail (test/server.test.ts: index routing, files with percent-decoding and content type, HEAD, 12 404 cases incl. escapes and a symlink leak, 405, taken port; test/cli.test.ts serve: spawned process prints the build and Serving lines, serves the home page on port 0, does not rebuild, taken port exit 1, failed build exit 1, usage cases). Manual run against the fixture: `/dotfiles-agents/` 200, `/dotfiles-agents` 404, `%2e%2e` and `..%2f` 404, CSS served as text/css. `groma scan` matched 1; accepted server, commands -> server, server -> site-output, maintainer -> server; flow preview-locally added; `groma lint` -> No findings.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added src/server.ts (Bun.serve preview under the base path with folder index, 404 for anything outside or escaping, port-taken error) and the `serve` command in src/commands.ts, plus the README serve section and the Preview locally flow. Verified by 12 new tests, a manual run, and a clean scan/lint.
<!-- SECTION:FINAL_SUMMARY:END -->
