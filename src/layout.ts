// Wraps a page's final body in the site's page document: head, header, nav,
// the "On this page" contents, the footer and, for diagrams, the Mermaid loader.
import { githubUrl, siteUrl, type Page, type Site } from "./pages.ts";

export interface PageParts {
  site: Site;
  /** The Git ref GitHub links point at. */
  ref: string;
  page: Page;
  /** Text of the page's first H1, HTML-escaped. */
  title: string;
  /** The rendered body with its links rewritten. */
  body: string;
  mermaid: boolean;
}

export const MERMAID_SCRIPT = `<script type="module">
const diagrams = document.querySelectorAll('pre.mermaid');
try {
  const {default: mermaid} = await import('https://cdn.jsdelivr.net/npm/mermaid@11.12.0/dist/mermaid.esm.min.mjs');
  mermaid.initialize({startOnLoad: false, securityLevel: 'strict', theme: 'neutral'});
  await mermaid.run({nodes: diagrams});
} catch { /* The readable diagram source stays when JavaScript or the CDN is unavailable. */ }
</script>`;

/** The complete HTML document for one page. */
export async function layoutPage({ site, ref, page, title, body, mermaid }: PageParts): Promise<string> {
  const { config } = site;
  const name = Bun.escapeHTML(config.name);
  const link = (target: string, label: string, current = false) => {
    const url = site.byPath.get(target)!.url;
    return `<a href="${url}"${current ? ' aria-current="page"' : ""}>${Bun.escapeHTML(label)}</a>`;
  };
  const footer = [`<a href="${githubUrl(config.repo, ref, "blob", page.path)}">View canonical Markdown</a>`];
  for (const entry of config.footer) footer.push(link(entry.page, entry.label));

  const lines = [
    "<!doctype html>",
    '<html lang="en">',
    "<head>",
    '<meta charset="utf-8">',
    '<meta name="viewport" content="width=device-width, initial-scale=1">',
    `<title>${title} · ${name}</title>`,
    `<link rel="stylesheet" href="${siteUrl(config.base, "assets/site.css")}">`,
    "</head>",
    "<body>",
    '<a class="skip" href="#content">Skip to content</a>',
    `<header><a class="brand" href="${siteUrl(config.base, "index.html")}">${name}</a><a href="https://github.com/${config.repo}">Repository</a></header>`,
    '<div class="layout">',
    '<nav aria-label="Documentation">',
    ...config.nav.map((entry) => link(entry.page, entry.label, entry.page === page.path)),
    "</nav>",
    '<main id="content" tabindex="-1">',
    ...(await contents(body)),
    body.replace(/\n+$/, ""),
    `<footer>${footer.join(" · ")}</footer>`,
    "</main>",
    "</div>",
    ...(mermaid ? [MERMAID_SCRIPT] : []),
    "</body>",
    "</html>",
  ];
  return `${lines.join("\n")}\n`;
}

interface Entry {
  id: string;
  html: string;
  children: Entry[] | undefined;
}

/** The "On this page" block: H1s with their H2s nested beneath; nothing when the page has no H2. */
async function contents(body: string): Promise<string[]> {
  const top: Entry[] = [];
  let parent: Entry | undefined;
  let hasH2 = false;
  for (const match of body.matchAll(/<(h[12])\b([^>]*)>([\s\S]*?)<\/\1>/gi)) {
    const id = /\bid="([^"]*)"/.exec(match[2]!)?.[1] ?? "";
    const entry: Entry = { id, html: await inline(match[3]!), children: undefined };
    if (match[1]!.toLowerCase() === "h1") {
      entry.children = [];
      parent = entry;
      top.push(entry);
    } else {
      hasH2 = true;
      (parent?.children ?? top).push(entry);
    }
  }
  if (!hasH2) return [];
  const item = (entry: Entry): string => {
    const anchor = `<li><a href="#${entry.id}">${entry.html}</a>`;
    if (entry.children === undefined || entry.children.length === 0) return `${anchor}</li>`;
    return `${anchor}<ul>\n${entry.children.map(item).join("\n")}\n</ul></li>`;
  };
  return ['<details class="contents"><summary>On this page</summary><ul>', ...top.map(item), "</ul></details>"];
}

/** A heading's inline content for the contents block: links unwrapped, ids dropped, code spans kept. */
async function inline(html: string): Promise<string> {
  return new HTMLRewriter()
    .on("a", {
      element(element) {
        element.removeAndKeepContent();
      },
    })
    .on("[id]", {
      element(element) {
        element.removeAttribute("id");
      },
    })
    .transform(new Response(html))
    .text();
}
