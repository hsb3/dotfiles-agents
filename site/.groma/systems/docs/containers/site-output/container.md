---
type: C4 Container
title: Site output
description: The rendered site folder, the Pages artifact
status: stable
groma:
  id: site-output
  parent: docs
  technology: HTML file tree
---

The folder `site build` writes (`--output`, by default `/tmp/dotfiles-agents-site/dotfiles-agents`): one HTML file per page plus `assets/site.css`. It must lie outside the checkout. A build overwrites files of the same name and leaves others alone; `site serve` serves it and the Pages CI job uploads it.
