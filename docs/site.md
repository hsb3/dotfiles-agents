# Documentation site

The documentation site reuses the root README, `docs/**/*.md`, the contributor guide and
each `plugins/*/README.md`. Edit those canonical files. The renderer in [`site/`](../site/README.md)
turns them into HTML; no second documentation tree or generated output is committed. The page
list, navigation and repository identity live in `site/site.config.json`.

## Build and preview

Install [Bun](https://bun.sh) 1.4 (`brew install oven-sh/bun/bun`, or mise).

```sh
make docs-build
make docs-serve
```

Open <http://127.0.0.1:8000/dotfiles-agents/>. Build output goes to
`/tmp/dotfiles-agents-site/dotfiles-agents`, outside the checkout. Stop the preview with
Ctrl-C. `bun src/cli.ts build --output /tmp/another-preview/dotfiles-agents`, run in `site/`,
chooses another output directory. Use a fresh directory when checking deleted pages: a build
never deletes stale files, and files left by an earlier build never satisfy a link.

The build validates every local link and image (Markdown and raw HTML), every heading
fragment, and the navigation and stylesheet paths beneath `/dotfiles-agents/`; it reports
every problem in one run and writes nothing when any exists. Heading IDs match GitHub's. Links to source files outside the site
point at the corresponding GitHub source ref; published builds use the exact source SHA.
The layout has keyboard focus, a skip link, semantic navigation, a mobile layout and
scrollable wide tables/code. Mermaid diagrams render with pinned Mermaid 11.12.0 from
jsDelivr; readable diagram source remains when JavaScript or the CDN is unavailable.

`make ci` remains stdlib-only and zero-install. The renderer's own tests run in its
`site-test` lane (`make site-test`); the full build of this repository runs in the existing
required `drift guards` CI job.

## Release policy

The site is live at the free project URL <https://hsb3.github.io/dotfiles-agents/>.
No custom domain or paid hosting is needed:
[GitHub permits Pages on public repositories on its Free plan](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages).

The Pages job runs only after the [sanctioned publish workflow](../.github/workflows/publish.yml)
succeeds, and only for a public repository. It checks out the exact source SHA captured
by that run, builds an artifact, and deploys through GitHub Pages Actions. It neither adds
docs to `main` nor writes a branch. A docs-only publication may leave the plugin surface
unchanged and still deploy the documentation. Do not start a competing dev merge during
publication. See the [publish runbook](../.agents/skills/publish-to-main/SKILL.md).

Repository Pages uses **GitHub Actions** as its source, and the `github-pages` environment
permits the `dev` branch (both set 2026-09-14). To redeploy, dispatch the sanctioned
workflow from `dev`, watch all jobs pass, and verify the actual project URL anonymously.
A successful local build is not a successful deployment.

GitHub currently limits published sites to 1 GB, deployments to 10 minutes and soft
bandwidth to 100 GB/month; custom Actions builds are exempt from the soft 10-build/hour
limit. This text-only documentation site is far smaller than the size limit.
See [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).
