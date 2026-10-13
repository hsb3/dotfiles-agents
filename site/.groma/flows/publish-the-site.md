---
type: Groma Flow
title: Publish the site
groma:
  id: publish-the-site
---

The publish workflow's `pages` job runs `site build --ref <sha>` with the exact commit SHA, so every GitHub link points at that commit. The build writes the output folder, which the job uploads as the Pages artifact and deploys to GitHub Pages; the reader opens the site there, and their browser fetches Mermaid 11.12.0 from jsDelivr for pages with diagrams.

## Steps

| From | To | Action |
| --- | --- | --- |
| [Pages CI job](../externals/pages-ci-job.md) | [site CLI](../systems/docs/containers/site-cli/container.md) | Run `site build --ref <sha>` |
| [CLI entry point](../systems/docs/containers/site-cli/components/cli.md) | [Commands](../systems/docs/containers/site-cli/components/commands.md) | Pass `build` and its options |
| [Commands](../systems/docs/containers/site-cli/components/commands.md) | [Build](../systems/docs/containers/site-cli/components/build.md) | Run the build at the given ref |
| [Build](../systems/docs/containers/site-cli/components/build.md) | [Site output](../systems/docs/containers/site-output/container.md) | Write every page and `assets/site.css` |
| [Pages CI job](../externals/pages-ci-job.md) | [Site output](../systems/docs/containers/site-output/container.md) | Upload the output folder as the Pages artifact |
| [Pages CI job](../externals/pages-ci-job.md) | [GitHub Pages](../externals/github-pages.md) | Deploy the artifact |
| [Site reader](../actors/site-reader.md) | [GitHub Pages](../externals/github-pages.md) | Open the published pages |
| [Site reader](../actors/site-reader.md) | [jsDelivr CDN](../externals/jsdelivr-cdn.md) | Fetch Mermaid for pages with diagrams |
