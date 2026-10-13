---
type: C4 Actor
title: Site reader
description: Reads the published documentation in a browser
status: stable
groma:
  id: site-reader
---

Opens the Pages site, follows its links between pages and out to GitHub, and sees Mermaid diagrams drawn by their browser.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [site-reader](site-reader.md) | [github-pages](../externals/github-pages.md) | Browses the site | HTTPS |
| [site-reader](site-reader.md) | [jsdelivr-cdn](../externals/jsdelivr-cdn.md) | Fetches Mermaid | HTTPS, ES module |
| [site-reader](site-reader.md) | [github-content-hosts](../externals/github-content-hosts.md) | Follows source and file links | HTTPS |
