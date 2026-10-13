// Renders one page's Markdown to its HTML body: frontmatter removed, an H1
// inserted when the page has none, GitHub heading IDs, Mermaid blocks and
// keyboard-scrollable <pre> and <table> elements.
import GithubSlugger from "github-slugger";

export interface Rendered {
  /** The page body, before link rewriting. */
  body: string;
  /** Text of the page's first H1, whitespace collapsed, HTML-escaped. */
  title: string;
  /** Every `id` in the body, decoded. */
  ids: Set<string>;
  /** Whether the body has at least one Mermaid diagram. */
  mermaid: boolean;
}

/** A page that cannot be rendered; the message is `<page>: <problem>`. */
export class PageError extends Error {}

const MARKDOWN: Bun.markdown.Options = { tables: true, strikethrough: true, tasklists: true, autolinks: true };
const HEADINGS = "h1, h2, h3, h4, h5, h6";
const MERMAID = /<pre><code class="language-mermaid">([\s\S]*?)<\/code><\/pre>/g;

/** Renders the page at listed path `path` from its Markdown `source`. */
export async function renderPage(path: string, source: string): Promise<Rendered> {
  const { data, markdown } = splitFrontmatter(path, source);
  let html = Bun.markdown.html(markdown, MARKDOWN);
  if (!/<h1[\s>]/i.test(html)) {
    const title = typeof data.title === "string" && data.title.trim() !== "" ? data.title : fileStem(path);
    html = `<h1>${Bun.escapeHTML(title)}</h1>\n${html}`;
  }
  let mermaid = false;
  html = html.replace(MERMAID, (_, code: string) => {
    mermaid = true;
    return `<pre class="mermaid">${code}</pre>`;
  });

  const scan = await scanHeadings(html);
  const slugger = new GithubSlugger();
  const ids = new Set(scan.ids);
  const headingIds = scan.headings.map((heading) => {
    const id = heading.id ?? slugger.slug(decodeEntities(heading.text));
    ids.add(id);
    return id;
  });

  let index = 0;
  const body = await new HTMLRewriter()
    .on(HEADINGS, {
      element(element) {
        const id = headingIds[index++];
        if (id !== undefined && !element.hasAttribute("id")) element.setAttribute("id", escapeAttribute(id));
      },
    })
    .on("pre, table", {
      element(element) {
        element.setAttribute("tabindex", "0");
      },
    })
    .transform(new Response(html))
    .text();

  return { body, title: scan.firstH1.replace(/\s+/g, " ").trim(), ids, mermaid };
}

interface Frontmatter {
  data: Record<string, unknown>;
  markdown: string;
}

/** Removes YAML frontmatter that starts on the first line with `---` and ends at the next `---` or `...` line. */
export function splitFrontmatter(path: string, source: string): Frontmatter {
  const text = source.replace(/^﻿/, "");
  const lines = text.split("\n");
  if (lines[0]?.replace(/\r$/, "") !== "---") return { data: {}, markdown: text };
  const end = lines.findIndex((line, index) => index > 0 && /^(---|\.\.\.)\r?$/.test(line));
  if (end === -1) return { data: {}, markdown: text };
  const yaml = lines.slice(1, end).join("\n");
  let data: unknown;
  try {
    data = Bun.YAML.parse(yaml);
  } catch (error) {
    throw new PageError(`${path}: bad frontmatter: ${error instanceof Error ? error.message : String(error)}`);
  }
  if (data === null && yaml.trim() === "") data = {};
  if (typeof data !== "object" || data === null || Array.isArray(data)) {
    const kind = Array.isArray(data) ? "a list" : data === null ? "null" : `a ${typeof data}`;
    throw new PageError(`${path}: bad frontmatter: not a mapping (got ${kind})`);
  }
  return { data: data as Record<string, unknown>, markdown: lines.slice(end + 1).join("\n") };
}

interface HeadingScan {
  headings: { text: string; id: string | undefined }[];
  ids: string[];
  firstH1: string;
}

/** Collects each heading's text content (raw, still entity-encoded), and every existing `id`. */
async function scanHeadings(html: string): Promise<HeadingScan> {
  const scan: HeadingScan = { headings: [], ids: [], firstH1: "" };
  let current: { text: string; id: string | undefined } | undefined;
  let sawH1 = false;
  let inFirstH1 = false;
  await new HTMLRewriter()
    .on("[id]", {
      element(element) {
        scan.ids.push(decodeEntities(element.getAttribute("id")!));
      },
    })
    .on(HEADINGS, {
      element(element) {
        const id = element.getAttribute("id");
        current = { text: "", id: id === null ? undefined : decodeEntities(id) };
        scan.headings.push(current);
        inFirstH1 = element.tagName === "h1" && !sawH1;
        sawH1 ||= inFirstH1;
        element.onEndTag(() => {
          current = undefined;
          inFirstH1 = false;
        });
      },
      text(chunk) {
        if (current === undefined) return;
        current.text += chunk.text;
        if (inFirstH1) scan.firstH1 += chunk.text;
      },
    })
    .transform(new Response(html))
    .text();
  return scan;
}

function fileStem(path: string): string {
  return path.slice(path.lastIndexOf("/") + 1).replace(/\.md$/, "");
}

function escapeAttribute(value: string): string {
  return value.replace(/&/g, "&amp;");
}

const NAMED: Record<string, string> = {
  amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " ", ensp: " ", emsp: " ",
  thinsp: " ", zwnj: "‌", zwj: "‍", shy: "­", mdash: "—", ndash: "–", hellip: "…",
  middot: "·", bull: "•", copy: "©", reg: "®", trade: "™", deg: "°", plusmn: "±", times: "×",
  divide: "÷", sect: "§", para: "¶", laquo: "«", raquo: "»", lsquo: "‘", rsquo: "’", ldquo: "“",
  rdquo: "”", larr: "←", rarr: "→", uarr: "↑", darr: "↓", harr: "↔", euro: "€", pound: "£",
  yen: "¥", cent: "¢", check: "✓",
};

/** Decodes numeric character references and common named entities; unknown names stay as written. */
export function decodeEntities(text: string): string {
  return text.replace(/&(#[xX][0-9a-fA-F]+|#[0-9]+|[A-Za-z][A-Za-z0-9]*);/g, (match, name: string) => {
    if (name.startsWith("#")) {
      const code = name[1] === "x" || name[1] === "X" ? parseInt(name.slice(2), 16) : parseInt(name.slice(1), 10);
      return code > 0 && code <= 0x10ffff ? String.fromCodePoint(code) : match;
    }
    return NAMED[name] ?? match;
  });
}
