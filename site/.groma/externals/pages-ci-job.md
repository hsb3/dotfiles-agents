---
type: C4 System
title: Pages CI job
status: stable
groma:
  id: pages-ci-job
  technology: GitHub Actions
---

The publish workflow's `pages` job. It runs `site build --ref <sha>` with the exact commit SHA, uploads the output folder as the Pages artifact and deploys it to GitHub Pages.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [pages-ci-job](pages-ci-job.md) | [site-cli](../systems/docs/containers/site-cli/container.md) | Builds the site at a commit | shell |
| [pages-ci-job](pages-ci-job.md) | [site-output](../systems/docs/containers/site-output/container.md) | Uploads the Pages artifact | actions/upload-pages-artifact |
| [pages-ci-job](pages-ci-job.md) | [github-pages](github-pages.md) | Deploys the site | actions/deploy-pages |
