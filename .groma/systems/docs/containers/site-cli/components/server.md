---
type: C4 Component
title: Server
description: Serves the built site locally under its base path
status: stable
groma:
  id: server
  parent: site-cli
  technology: TypeScript, Bun.serve
  draft: v1
  code:
    - scanner: typescript
      file: src/server.ts
---

Serves the output folder for `site serve` on `127.0.0.1` (port 8000 by default, `0` for a free one) under the base path, as GitHub Pages would: `<base>/` and any path ending in `/` get that folder's `index.html`, any other path under the base gets the file. Everything else gets 404: paths outside the base, missing files, and paths that escape the folder through dot segments, encoded slashes or symlinks; only `GET` and `HEAD` are served. It never rebuilds, and reports a taken port so `serve` can exit 1.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [server](server.md) | [site-output](../../site-output/container.md) | Serves files from | filesystem |
