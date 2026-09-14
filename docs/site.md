# Documentation site

The documentation site reuses the root README, `docs/**/*.md`, the contributor guide and
each `plugins/*/README.md`. Edit those canonical files. Pandoc renders them into HTML;
no second documentation tree or generated output is committed.

## Build and preview

Install [Pandoc](https://pandoc.org/installing.html) and Python 3.10 or newer. On macOS,
`brew install pandoc`; on Ubuntu, `sudo apt-get install pandoc`.

```sh
make docs-build
make docs-serve
```

Open <http://localhost:8000/dotfiles-agents/>. Build output goes to
`/tmp/dotfiles-agents-site/dotfiles-agents`, outside the checkout. Stop the preview with
Ctrl-C. `python3 scripts/build_docs.py --output /tmp/another-preview/dotfiles-agents`
chooses another output directory. Use a fresh directory when checking deleted pages.

The build validates local Markdown destinations and rendered heading links, navigation
and stylesheet paths beneath `/dotfiles-agents/`. Links to source files outside the site
point at the corresponding GitHub source ref; published builds use the exact source SHA.
The layout has keyboard focus, a skip link, semantic navigation, a mobile layout and
scrollable wide tables/code. Mermaid diagrams render with pinned Mermaid 11.12.0 from
jsDelivr; readable diagram source remains when JavaScript or the CDN is unavailable.

`make ci` remains stdlib-only and zero-install. The small routing regression runs there;
the full Pandoc build runs in the existing required `drift guards` CI job.

## Release policy

The intended free project URL is <https://hsb3.github.io/dotfiles-agents/>. It remains
undeployed until public readiness is verified. No custom domain or paid hosting is needed.
[GitHub permits Pages on public repositories on its Free plan](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages).
The account API did not return a plan name; enabling Pages after the visibility change
and verifying deployment will establish this repository's actual eligibility.

The Pages job runs only after the [sanctioned publish workflow](../.github/workflows/publish.yml)
succeeds, and only for a public repository. It checks out the exact source SHA captured
by that run, builds an artifact, and deploys through GitHub Pages Actions. It neither adds
docs to `main` nor writes a branch. A docs-only publication may leave the plugin surface
unchanged and still deploy the documentation. Do not start a competing dev merge during
publication. See the [publish runbook](../.agents/skills/publish-to-main/SKILL.md).

After public readiness, configure repository Pages with **GitHub Actions** as its source
and permit the `dev` branch in the `github-pages` environment. Dispatch the sanctioned
workflow from `dev`, watch all jobs pass, and verify the actual project URL anonymously.
A successful local build is not a successful deployment.

GitHub currently limits published sites to 1 GB, deployments to 10 minutes and soft
bandwidth to 100 GB/month; custom Actions builds are exempt from the soft 10-build/hour
limit. This text-only documentation site is far smaller than the size limit.
See [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).
