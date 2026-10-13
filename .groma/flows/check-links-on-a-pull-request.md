---
type: Groma Flow
title: Check links on a pull request
groma:
  id: check-links-on-a-pull-request
---

On every pull request the `drift guards (roster · marketplace · catalog)` job runs `site build` over the checkout as the repo-wide link check. Every page is rendered and every link and image checked; the job's outcome is the exit code (0, or 1 with one stderr line per broken link, missing heading or bad frontmatter), and nothing is written when it fails.

## Steps

| From | To | Action |
| --- | --- | --- |
| [Drift guards CI job](../externals/drift-guards-ci-job.md) | [site CLI](../systems/docs/containers/site-cli/container.md) | Run `site build` |
| [CLI entry point](../systems/docs/containers/site-cli/components/cli.md) | [Commands](../systems/docs/containers/site-cli/components/commands.md) | Pass `build` and its options |
| [Commands](../systems/docs/containers/site-cli/components/commands.md) | [Build](../systems/docs/containers/site-cli/components/build.md) | Run the build with the default config and ref |
| [Build](../systems/docs/containers/site-cli/components/build.md) | [Pages](../systems/docs/containers/site-cli/components/pages.md) | Select the configured pages |
| [Pages](../systems/docs/containers/site-cli/components/pages.md) | [dotfiles-agents checkout](../externals/dotfiles-agents-checkout.md) | List and read the Markdown pages |
| [Build](../systems/docs/containers/site-cli/components/build.md) | [Links](../systems/docs/containers/site-cli/components/links.md) | Rewrite and check every link and image |
| [Links](../systems/docs/containers/site-cli/components/links.md) | [dotfiles-agents checkout](../externals/dotfiles-agents-checkout.md) | Check that each local target exists inside the checkout |
