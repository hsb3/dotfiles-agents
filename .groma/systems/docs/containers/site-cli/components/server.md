---
type: C4 Component
title: Server
description: Serves the built site locally under its base path
status: draft
groma:
  id: server
  parent: site-cli
  technology: TypeScript, Bun.serve
  draft: v1
---

Serves the output folder on `127.0.0.1` (port 8000 by default, `0` for a free one) under the base path: a path ending in `/` gets that folder's `index.html`, any other path under the base gets the file, and everything else, including paths that escape the folder, gets 404. Never rebuilds; fails with exit 1 when the port is taken.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [server](server.md) | [site-output](../../site-output/container.md) | Serves files from | filesystem |
