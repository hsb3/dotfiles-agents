# site

Renders the canonical Markdown of a repository checkout into the static documentation site GitHub Pages serves at a project subpath, and fails when any link in those pages is broken. It reads a checkout it does not own, writes a self-contained HTML tree outside that checkout, and never touches the network.

The unit lives at `site/` in `hsb3/dotfiles-agents`. CI runs `site build` as the repo-wide link check on every pull request and as the build step of the Pages deploy.

Requires Bun 1.4. Install once with `bun install --frozen-lockfile`; check with `bunx tsc --noEmit && bun test`.

## Commands

Run from the unit folder as `bun src/cli.ts <command>` (the package's `site` binary).

### `site build [--root DIR] [--config FILE] [--output DIR] [--ref REF]`

Renders every page in the config's page list from the checkout at `--root` into `--output`, rewriting and checking every link.

| Option | Default |
|---|---|
| `--root DIR` | the folder that contains the unit folder (the dotfiles-agents checkout when the unit sits at `site/`) |
| `--config FILE` | the unit's own `site.config.json` |
| `--output DIR` | `/tmp/<name>-site/<name>`, where `<name>` is the site name (`/tmp/dotfiles-agents-site/dotfiles-agents`) |
| `--ref REF` | the config's `ref`; the Pages deploy passes the exact commit SHA |

Options take their value as the next argument or after `=` (`--ref=dev`).

- Everything is rendered and checked before anything is written, so a failed build writes nothing.
- A successful build writes each page and `assets/site.css`, overwrites files of the same name, and leaves other files in the output folder alone. It never deletes stale files.
- The output folder must not be the checkout or lie inside it, after resolving symlinks.
- The same checkout, config and ref produce byte-identical output.

On success it prints `<N> pages built, links verified: <output>` and exits 0. On failure stderr gets one line per problem, sorted by page and then by position within the page, then `build: <K> problems; nothing written`, and it exits 1.

`site` with no command, or with an unknown command or option, prints usage to stderr and exits 1.

## Config

`site.config.json` in the unit folder:

| Key | Required | Meaning |
|---|---|---|
| `repo` | yes | `<owner>/<name>` on GitHub |
| `ref` | yes | the Git ref GitHub links point at unless `--ref` is given |
| `base` | no | the site's base path, `/` followed by one segment of `A–Z a–z 0–9 _ -`; defaults to `/<name>` from `repo`. The site name shown in titles and the header is the base without its `/` |
| `pages` | no | repo-relative paths and globs of `.md` files |
| `exclude` | no | paths and globs removed from the page list |
| `rename` | no | `{ "<page>": "<output path>" }` for pages that publish somewhere other than the default |
| `nav` | no | `[{ "label", "page" }]`, the sidebar links in order |
| `footer` | no | `[{ "label", "page" }]`, footer links after "View canonical Markdown" |

Globs: `*` matches within one path segment and `**` across segments; no other character is special. Wildcards do not match names that start with `.`, but an explicit name does (`.github/CONTRIBUTING.md`). A symlinked file matches like any other file; `**` does not descend into symlinked folders. Only regular `.md` files become pages.

A page's output path is its `rename` entry, or its repo path with `.md` replaced by `.html`. Its site URL is `<base>/<output path>`, each segment percent-encoded except `A–Z a–z 0–9 - . _ ~`. A symlinked page is known by its listed path: it publishes there, its links resolve from its listed folder, and its source link points at the listed path.

These are config problems, printed as `<config path>: <problem>`:

- an unknown or missing key, or a value of the wrong type;
- a bad `repo` or `base`;
- a `pages` or `exclude` entry that matches nothing;
- a `nav`, `footer` or `rename` page that is not in the page list;
- no page publishing at `index.html` (the header links there);
- two pages with the same output path;
- an output path with a segment starting with `.`, because the Pages artifact drops hidden paths.

## Pages

- YAML frontmatter at the very top of a file (`---` to the next `---` or `...`) is removed; invalid YAML, or YAML that is not a mapping, fails the page with `<page>: bad frontmatter: <reason>`.
- A page with no level-1 heading gets one, from the frontmatter `title` or else the file name. `<title>` is `<first H1 text> · <site name>`.
- Markdown renders as GitHub renders it, without sanitising: GFM tables, strikethrough, task lists, autolinks and raw HTML. A `mermaid` code block becomes `<pre class="mermaid">`, drawn in the reader's browser by Mermaid 11.12.0 from jsDelivr.
- Every heading gets the ID GitHub gives it (github-slugger), so anchors written against GitHub keep working.

## Links

Every `href` of an `<a>` and `src` of an `<img>` in a page, from Markdown or raw HTML:

1. A destination with a scheme (`https:`, `mailto:`) or starting with `//` is left alone. A `#fragment` points at the page itself and stays; an empty or query-only destination becomes the page's own URL.
2. Otherwise its path, percent-decoded, is a repo path, relative to the page's folder or to the checkout root when it starts with `/`. It must name an existing file or folder inside the checkout; a path that leaves the checkout through `..` or a symlink counts as missing. Otherwise: `<page>: broken local link: <destination>`.
3. A folder whose `README.md` is a page stands for that page.
4. A page becomes its site URL. Any other file becomes `https://github.com/<repo>/blob/<ref>/<path>` (`tree` for a folder), and an image `https://raw.githubusercontent.com/<repo>/<ref>/<path>`.
5. The query and fragment are kept as written.
6. A fragment on a link to a page must equal an `id` in that page's final HTML (a heading, a raw-HTML `id`, or `content`). Otherwise: `<page>: missing heading: <destination>`. Fragments on GitHub links are not checked.

No `href` or `src` in the output is a relative path, and every root-relative URL names a file the same build produced; files left by earlier builds never satisfy a link.
