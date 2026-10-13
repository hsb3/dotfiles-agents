---
type: C4 Container
title: site CLI
status: stable
groma:
  id: site-cli
  parent: docs
  technology: TypeScript on Bun
description: Renders a checkout's Markdown into the Pages site and checks every link
---
The `site` command-line application. `site build` renders every page the config lists from a checkout it does not own into a self-contained HTML tree outside that checkout, rewriting each local link to a site URL or a GitHub URL and failing with one line per broken link or missing heading; nothing is written unless the whole build succeeds. `site serve` runs the same build, then previews the tree on `127.0.0.1` under the site base path. It never touches the network.
