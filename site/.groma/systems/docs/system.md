---
type: C4 System
title: site
status: stable
groma:
  id: docs
description: Static documentation site renderer and link checker for dotfiles-agents
---
Turns the canonical Markdown of the dotfiles-agents repository into the static site GitHub Pages serves at `/dotfiles-agents/`, and fails when any link in those pages is broken. CI runs it twice: as the repo-wide link check on every pull request, and as the build step of the Pages deploy. Maintainers run it locally to build and preview. It has no content of its own, no server beyond the local preview, and no client-side app.
