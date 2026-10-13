# site — product spec (v1)

A command-line renderer that turns a repository's canonical Markdown into the static documentation site GitHub Pages serves at a project subpath, and fails when any link in those pages is broken. It reads a checkout it does not own, writes a self-contained HTML tree outside that checkout, and can preview the tree locally. It lands as the top-level `site/` folder of `hsb3/dotfiles-agents`, whose CI runs it twice: as the repo-wide link check on every pull request, and as the build step of the Pages deploy. It has no content of its own, no server beyond the local preview, and no client-side app.

## Stack

TypeScript on Bun 1.4 (1.4.3 locally). Markdown is rendered by Bun's built-in `Bun.markdown.html`, which is md4c: CommonMark plus GFM tables, strikethrough, task lists and autolinks, with raw HTML passed through. Its `headings` option stays off, because its IDs are not GitHub's: it renders `Hooks as script + config` as `hooks-as-script-config`, where GitHub gives `hooks-as-script--config`. Heading IDs come from `github-slugger` 2.0.0, the only runtime npm dependency (exact pin). The other built-ins available are `Bun.YAML` (frontmatter), `Bun.Glob` (page list), `HTMLRewriter` and `Bun.serve`. Dev dependencies stay as provisioned: `@types/bun` 1.4.2 and `typescript` 7.0.2. The binary is `site` (`package.json` `"bin": {"site": "src/cli.ts"}`), run as `bun src/cli.ts <command>` from the unit folder. Gates: `bunx tsc --noEmit && bun test`. Tests build synthetic checkouts in temporary folders. Nothing in the test suite reaches the network or needs any other repository.

## Behaviour

| Command | Does | Output | Exit |
|---|---|---|---|
| `site build [--root DIR] [--config FILE] [--output DIR] [--ref REF]` | Renders every page in the config's page list from the checkout at `--root` into `--output`, rewriting and checking every link (see Links). Defaults: `--root` is the folder that contains the unit folder (the dotfiles-agents checkout when the unit sits at `site/`); `--config` is the unit's own `site.config.json`; `--output` is `/tmp/<name>-site/<name>`, where `<name>` is the base path without its `/` (`/tmp/dotfiles-agents-site/dotfiles-agents`); `--ref`, the Git ref that GitHub links point at, is the config's `ref` (the Pages deploy passes the exact commit SHA). Refuses an output folder that is the checkout or lies inside it, after resolving symlinks. Renders and checks everything before writing, so a failed build writes nothing. A successful build writes each page and `assets/site.css`, overwrites files of the same name, and leaves other files in the output folder alone. | stdout `<N> pages built, links verified: <output>`. On failure, stderr gets one line per problem, then `build: <K> problems; nothing written` | 0; 1 on any problem |
| `site serve [build options] [--port N]` | Runs `build` with the same options, then serves the output folder on `127.0.0.1` (port 8000 by default; `0` picks a free one) under the base path. A request for `<base>/`, or any path ending in `/`, gets that folder's `index.html`. Any other path under `<base>/` gets the file. Everything else gets 404: paths outside the base, missing files, and paths escaping the output folder. Runs until interrupted. Never rebuilds. | the build line, then `Serving http://127.0.0.1:<port><base>/ (Ctrl-C to stop)` | 1 if the build fails or the port is taken |

## Config

`site.config.json` in the unit folder. It ships with dotfiles-agents' values:

```json
{
  "repo": "hsb3/dotfiles-agents",
  "ref": "dev",
  "pages": ["README.md", ".github/CONTRIBUTING.md", "docs/**/*.md", "plugins/*/README.md"],
  "exclude": ["docs/decisions/0000-template.md"],
  "rename": { "docs/README.md": "index.html", ".github/CONTRIBUTING.md": "contributing.html" },
  "nav": [
    { "label": "Documentation", "page": "docs/README.md" },
    { "label": "Install & catalog", "page": "README.md" },
    { "label": "Codex support", "page": "docs/codex-compatibility.md" },
    { "label": "Atelier setup", "page": "plugins/atelier/README.md" },
    { "label": "Contribute", "page": ".github/CONTRIBUTING.md" },
    { "label": "Decision history", "page": "docs/decisions/README.md" }
  ],
  "footer": [{ "label": "Licenses", "page": "docs/licenses.md" }]
}
```

- `repo` (`<owner>/<name>`) and `ref` are required. `base` is optional and defaults to `/<name>` (`/dotfiles-agents`). It must be `/` followed by one segment of `A–Z a–z 0–9 _ -`. The **site name** shown in titles and the header is the base without its `/`.
- `pages` lists repo-relative paths and globs of `.md` files: `*` matches within one path segment and `**` across segments. Wildcards do not match names that start with `.`, but an explicit name does (`.github/CONTRIBUTING.md`). A symlinked file matches like any other file. `exclude` removes paths using the same syntax. An entry in either list that matches nothing is an error.
- `rename` gives a page an output path other than the default.
- `nav` and `footer` are rendered in order. Each `page` must be in the page list.
- Config problems print as `<config path>: <problem>` and exit 1. They are: an unknown or missing key; a bad `base`; a `nav`, `footer` or `rename` page that is not in the page list; no page publishing at `index.html` (the header links there); two pages with the same output path; an output path with a segment starting with `.`, because the Pages artifact drops hidden paths (`site.config.json: .github/SECURITY.md would publish at hidden path .github/SECURITY.html`).

Against dotfiles-agents today, this config selects 59 pages. Two of them are symlinks: `plugins/bun/README.md` points to `../../primitives-core/skills/bun/README.md`, and `plugins/carbon/README.md` points to `../../primitives-core/skills/carbon-builder/README.md`.

## Pages and URLs

- A page's **output path** is its `rename` entry. Otherwise it is its repo path with `.md` replaced by `.html`:
  - `README.md` becomes `README.html`;
  - `docs/decisions/README.md` becomes `docs/decisions/README.html`;
  - `plugins/atelier/README.md` becomes `plugins/atelier/README.html`;
  - `docs/README.md` becomes `index.html`;
  - `.github/CONTRIBUTING.md` becomes `contributing.html`.
- Its **site URL** is `<base>/<output path>`, with each path segment percent-encoded except `A–Z a–z 0–9 - . _ ~`. For example, `docs/My Notes.md` becomes `/dotfiles-agents/docs/My%20Notes.html`.
- A page is known by its listed path, even when that path is a symlink. So `plugins/bun/README.md` publishes at `plugins/bun/README.html`, its links resolve from `plugins/bun/` (not from the target's folder), and its source link points at `plugins/bun/README.md`.

## Frontmatter and titles

- **Frontmatter** is a YAML mapping that starts on the file's first line with `---` and ends at the next line that is `---` or `...`. It is only recognised at the very top of the file. It is removed and never rendered. Invalid YAML, or YAML that is not a mapping, fails the page: `<page>: bad frontmatter: <reason>`.
- Decision records come in two shapes, and both must work. 21 have `id, title, date, status` and no H1. 8 have `title, id, type, status, created, summary` followed by an H1. For example:

  ```markdown
  ---
  id: "decision-021"
  title: retired primitives are sunset by decision record, tag, and deletion (applied to kaneo)
  date: '2026-09-08'
  status: accepted
  ---
  **Amended 2026-09-08:** After the Kaneo retirement, …
  ```

- A page with no level-1 heading gets one inserted at the top. ATX and Setext headings both count; a `# ` line inside a code block does not. The inserted heading's text is the frontmatter `title` when that is a non-empty string, otherwise the file name without `.md`. The text is plain and HTML-escaped. The heading gets an ID like any other. The example above becomes `<h1 id="retired-primitives-are-sunset-by-decision-record-tag-and-deletion-applied-to-kaneo">retired primitives are sunset by decision record, tag, and deletion (applied to kaneo)</h1>`.
- `<title>` is `<text of the page's first H1> · <site name>`. The text is the H1's rendered text content, with markup dropped, runs of whitespace collapsed and the ends trimmed. Today a page without an H1 gets its file name as `<title>`. That is a bug, and this rule fixes it.

## Markdown

Pages render the way GitHub renders `.md` files, but without GitHub's sanitising:

- GFM tables with column alignment, strikethrough, task lists (disabled checkboxes), autolinked bare URLs and `www.` links, and hard line breaks.
- Raw HTML blocks and inline HTML pass through unchanged, with no tag filter. An unknown tag such as `<id>` in prose stays a tag.
- A fenced code block whose info string is `mermaid` becomes `<pre class="mermaid">`. The element contains only the HTML-escaped diagram source: no `<code>` and no other element. Mermaid reads the element's HTML, and today's `<code>` wrapper makes every diagram render as Mermaid's "Syntax error".
- Every other code block becomes `<pre><code class="language-<info>">` (no class when there is no info string), escaped and without highlighting.
- Every `<pre>` and `<table>` in the body gets `tabindex="0"`, so overflowing content can be scrolled from the keyboard.

## Heading IDs

Every heading, levels 1 to 6, gets the ID GitHub gives it, because the anchors in the content were written against GitHub's rendering. The ID is computed as follows:

1. Take the heading's rendered text content. Code-span text is kept; markup and raw HTML tags are dropped.
2. Lowercase it.
3. Delete every character that is not a letter, digit, `_`, `-` or space. Unicode letters and digits count.
4. Turn each space into `-`.
5. If the ID is already used on the page, add `-1`, `-2` and so on.

`github-slugger` 2.0.0 does steps 2 to 5. Each row below was checked against GitHub's own rendering of dotfiles-agents:

| Heading as written | ID |
|---|---|
| `# atelier parity — the Claude Code side` | `atelier-parity--the-claude-code-side` |
| `## Amendment — 2026-08-06 (owner sign-off, item C)` | `amendment--2026-08-06-owner-sign-off-item-c` |
| ``# Decision 007 · Distribution restructure: `dev` integrates, `main` publishes`` | `decision-007--distribution-restructure-dev-integrates-main-publishes` |
| `# Decision 025 · Hooks as script + config, never inline` | `decision-025--hooks-as-script--config-never-inline` |
| ``# Decision 031 · `_meta/` is tracked by default; targeted ignores only`` | `decision-031--_meta-is-tracked-by-default-targeted-ignores-only` |
| `` ## Worked example 1 — hooks: `CONTEXT_WATERMARK_SOFT` / `_HARD` `` | `worked-example-1--hooks-context_watermark_soft--_hard` |
| `` ### Per-project settings — `atelier.local.md` `` | `per-project-settings--atelierlocalmd` |
| `# Decision NNN · <decision title>` | `decision-nnn--` (the raw tag contributes no text) |
| `## Install`, then `## Install` again | `install`, then `install-1` |

## Links

These rules cover every `href` of an `<a>` and every `src` of an `<img>` in a page's body, whether it comes from Markdown syntax or from raw HTML:

1. A destination with a scheme (`https:`, `mailto:`) or one starting with `//` is left alone. A destination that is only a `#fragment`, or is empty, points at the page itself.
2. Otherwise its path, percent-decoded, is a repo path. It is relative to the page's folder, or to the checkout root when it starts with `/` (as on GitHub). It must name an existing file or folder inside the checkout; a path that leaves the checkout through `..` or a symlink counts as missing. Otherwise the build reports `<page>: broken local link: <destination>`.
3. A folder whose `README.md` is a page stands for that page.
4. A page becomes its site URL. Anything else becomes `https://github.com/<repo>/blob/<ref>/<path>` (`tree` instead of `blob` for a folder). An `<img>` instead becomes `https://raw.githubusercontent.com/<repo>/<ref>/<path>`. Paths are percent-encoded as for site URLs.
5. The query and fragment are kept as written.
6. A fragment on a link to a page, including the page itself, must equal an `id` in that page's final HTML after percent-decoding. That can be a heading, a raw-HTML `id`, or `content`. Otherwise the build reports `<page>: missing heading: <destination>`. Fragments on GitHub links are not checked.

Examples from page `docs/README.md`, ref `dev`:

| Written | Becomes |
|---|---|
| `../README.md#install` | `/dotfiles-agents/README.html#install` |
| `../.github/CONTRIBUTING.md` | `/dotfiles-agents/contributing.html` |
| `../plugins/atelier/` | `/dotfiles-agents/plugins/atelier/README.html` |
| `atelier-parity.md` | `/dotfiles-agents/docs/atelier-parity.html` |
| `#documentation` | unchanged; checked against this page |
| `../LICENSE` | `https://github.com/hsb3/dotfiles-agents/blob/dev/LICENSE` |
| `../primitives-core` | `https://github.com/hsb3/dotfiles-agents/tree/dev/primitives-core` |
| `decisions/0000-template.md` (excluded) | `https://github.com/hsb3/dotfiles-agents/blob/dev/docs/decisions/0000-template.md` |
| `![flow](img/flow.png)` (when `docs/img/flow.png` exists) | `https://raw.githubusercontent.com/hsb3/dotfiles-agents/dev/docs/img/flow.png` |
| `https://hsb3.github.io/dotfiles-agents/` | unchanged |
| `../scripts/gone.py` | `docs/README.md: broken local link: ../scripts/gone.py` |
| `../README.md#instal` | `docs/README.md: missing heading: ../README.md#instal` |

`<page>` is always the listed Markdown path. One run reports every problem, sorted by page and then by order within the page. In the finished output, no `href` or `src` is a relative path. That covers the header, nav, footer and stylesheet links too. Every root-relative URL starts with `<base>/` and names a file that this build produced. Files left in the output folder by earlier builds never satisfy a link.

## Page HTML

Every page is this document. The example is `docs/codex-compatibility.md` at ref `dev`. Elements, attributes and their order are the contract; whitespace between tags is free.

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Codex distribution and runtime contract · dotfiles-agents</title>
<link rel="stylesheet" href="/dotfiles-agents/assets/site.css">
</head>
<body>
<a class="skip" href="#content">Skip to content</a>
<header><a class="brand" href="/dotfiles-agents/index.html">dotfiles-agents</a><a href="https://github.com/hsb3/dotfiles-agents">Repository</a></header>
<div class="layout">
<nav aria-label="Documentation">
<a href="/dotfiles-agents/index.html">Documentation</a>
<a href="/dotfiles-agents/README.html">Install &amp; catalog</a>
<a href="/dotfiles-agents/docs/codex-compatibility.html" aria-current="page">Codex support</a>
<a href="/dotfiles-agents/plugins/atelier/README.html">Atelier setup</a>
<a href="/dotfiles-agents/contributing.html">Contribute</a>
<a href="/dotfiles-agents/docs/decisions/README.html">Decision history</a>
</nav>
<main id="content" tabindex="-1">
<details class="contents"><summary>On this page</summary><ul>
<li><a href="#codex-distribution-and-runtime-contract">Codex distribution and runtime contract</a><ul>
<li><a href="#distribution-and-setup">Distribution and setup</a></li>
<li><a href="#worker-isolation">Worker isolation</a></li>
<li><a href="#atelier-member-verdicts">Atelier member verdicts</a></li>
<li><a href="#other-bundles-and-prerequisites">Other bundles and prerequisites</a></li>
<li><a href="#repeatable-local-checks">Repeatable local checks</a></li>
</ul></li>
</ul></details>
<h1 id="codex-distribution-and-runtime-contract">Codex distribution and runtime contract</h1>
…the rest of the rendered body…
<footer><a href="https://github.com/hsb3/dotfiles-agents/blob/dev/docs/codex-compatibility.md">View canonical Markdown</a> · <a href="/dotfiles-agents/docs/licenses.html">Licenses</a></footer>
</main>
</div>
</body>
</html>
```

- **Nav:** the config's `nav` entries in order, with labels HTML-escaped. The entry for the current page carries `aria-current="page"`, set at build time.
- **Contents:** lists the page's H1 and H2 headings in order. Each H2 sits in a nested `<ul>` under the H1 before it; an H2 that comes before any H1 sits at the top level. Each entry links to `#<id>` and shows the heading's inline content with links unwrapped and code spans kept. The block is left out when the page has no H2.
- **Footer:** `View canonical Markdown` links to `https://github.com/<repo>/blob/<ref>/<listed path>`. The config's `footer` links follow, each preceded by ` · `.
- **Mermaid:** a page with at least one Mermaid diagram gets this script, verbatim, after `</div>`. Other pages have no script.

  ```html
  <script type="module">
  const diagrams = document.querySelectorAll('pre.mermaid');
  try {
    const {default: mermaid} = await import('https://cdn.jsdelivr.net/npm/mermaid@11.12.0/dist/mermaid.esm.min.mjs');
    mermaid.initialize({startOnLoad: false, securityLevel: 'strict', theme: 'neutral'});
    await mermaid.run({nodes: diagrams});
  } catch { /* The readable diagram source stays when JavaScript or the CDN is unavailable. */ }
  </script>
  ```

## Provided assets

- `assets/site.css` is the site's stylesheet, committed at init. Every build copies it byte for byte to `<output>/assets/site.css`. Its selectors are part of the contract above: `.skip`, `header`, `.brand`, `.layout`, `nav a[aria-current]`, `main`, `.contents`, `pre`, `table` and `footer`.

## Non-functional

- `site` with no subcommand, or an unknown subcommand or option, prints usage to stderr and exits 1.
- `build` and `serve` never touch the network. They read only the config, the stylesheet and files under `--root`, and write only under `--output`.
- The same checkout, config and ref produce byte-identical output: no timestamps, and a stable order.
- Tests build their own fixture checkouts. Between them, the fixtures cover:
  - a symlinked `plugins/<id>/README.md` whose relative links resolve from `plugins/<id>/`;
  - both frontmatter shapes;
  - `.github/CONTRIBUTING.md` renamed out of the hidden folder;
  - an excluded page linked from another page;
  - a Mermaid block;
  - a folder link;
  - an image;
  - every error message in this spec.
- `bunx tsc --noEmit` is clean under the scaffold's `tsconfig.json`. `bun.lock` is committed, and `bun install --frozen-lockfile` reproduces the install.
- `README.md` documents the two commands, the config keys and the link rules.

## Architecture expectations

The architecture must show these people:

- the maintainer or contributor, who builds and previews locally;
- the site reader, in a browser.

It must show these systems outside this one:

- the dotfiles-agents checkout being rendered (read, never owned);
- the two CI jobs that call `build`: the `drift guards (roster · marketplace · catalog)` job on every pull request, and the publish workflow's `pages` job;
- GitHub Pages, which hosts the uploaded output (this unit never calls it);
- GitHub's blob, tree and raw hosts, which rewritten links point at (never contacted);
- the jsDelivr CDN, which serves Mermaid 11.12.0 to the reader's browser (never contacted by this unit).

The data stores this unit owns are the output folder (the Pages artifact), the config file and the stylesheet.

The map must show three flows:

- **Check links on a pull request:** the CI job runs `build`, which reads the checkout, and the outcome is the exit code.
- **Publish the site:** the `pages` job runs `build --ref <sha>`, writing the output folder, which is uploaded to GitHub Pages and reaches the reader, whose browser fetches Mermaid from the CDN.
- **Preview locally:** the maintainer runs `serve`, and a browser opens `http://127.0.0.1:8000/dotfiles-agents/`.

## Out of scope for v1

Syntax highlighting, search, a generated nav or sidebar, watch mode and live reload, footnotes, GitHub alerts (`> [!NOTE]`), emoji shortcodes, math, HTML sanitising, checking external URLs, a sitemap or feed, a custom domain, bundling Mermaid, dark mode, and removing stale files from the output folder. Also out of scope: editing or normalising the content (decision frontmatter stays as it is), deploying (the CI job does that), and the Makefile, CI, `flow.yaml` and publish-workflow changes, which are made when the unit lands.
