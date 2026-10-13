---
type: C4 System
title: dotfiles-agents checkout
status: stable
groma:
  id: dotfiles-agents-checkout
  technology: Git working tree
---

The repository checkout being rendered (`--root`, by default the folder that contains the unit). `site` reads its Markdown pages and checks that local link targets exist in it; it never writes there and does not own it. Two of its pages are symlinked READMEs under `plugins/`.
