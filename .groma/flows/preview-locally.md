---
type: Groma Flow
title: Preview locally
groma:
  id: preview-locally
---

The maintainer runs `site serve` from the unit folder. It builds the site exactly as `site build` would (exiting 1 without serving when the build fails), then serves the output folder on `127.0.0.1` under the base path, and the maintainer opens `http://127.0.0.1:8000/dotfiles-agents/` in a browser. It never rebuilds; rerun it after editing.

## Steps

| From | To | Action |
| --- | --- | --- |
| [Maintainer](../actors/maintainer.md) | [site CLI](../systems/docs/containers/site-cli/container.md) | Run `site serve` |
| [CLI entry point](../systems/docs/containers/site-cli/components/cli.md) | [Commands](../systems/docs/containers/site-cli/components/commands.md) | Pass `serve` and its options |
| [Commands](../systems/docs/containers/site-cli/components/commands.md) | [Build](../systems/docs/containers/site-cli/components/build.md) | Run the build |
| [Build](../systems/docs/containers/site-cli/components/build.md) | [Site output](../systems/docs/containers/site-output/container.md) | Write every page and `assets/site.css` |
| [Commands](../systems/docs/containers/site-cli/components/commands.md) | [Server](../systems/docs/containers/site-cli/components/server.md) | Start the preview on port 8000 |
| [Maintainer](../actors/maintainer.md) | [Server](../systems/docs/containers/site-cli/components/server.md) | Open `http://127.0.0.1:8000/dotfiles-agents/` in a browser |
| [Server](../systems/docs/containers/site-cli/components/server.md) | [Site output](../systems/docs/containers/site-output/container.md) | Serve the requested page under the base path |
