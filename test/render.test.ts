import { describe, expect, test } from "bun:test";
import { decodeEntities, PageError, renderPage } from "../src/render.ts";

async function body(markdown: string, path = "docs/page.md"): Promise<string> {
  return (await renderPage(path, markdown)).body;
}

describe("heading IDs", () => {
  // Each row was checked against GitHub's rendering of dotfiles-agents (SPEC.md).
  const rows: [string, string][] = [
    ["# atelier parity — the Claude Code side", "atelier-parity--the-claude-code-side"],
    ["## Amendment — 2026-08-06 (owner sign-off, item C)", "amendment--2026-08-06-owner-sign-off-item-c"],
    [
      "# Decision 007 · Distribution restructure: `dev` integrates, `main` publishes",
      "decision-007--distribution-restructure-dev-integrates-main-publishes",
    ],
    ["# Decision 025 · Hooks as script + config, never inline", "decision-025--hooks-as-script--config-never-inline"],
    [
      "# Decision 031 · `_meta/` is tracked by default; targeted ignores only",
      "decision-031--_meta-is-tracked-by-default-targeted-ignores-only",
    ],
    [
      "## Worked example 1 — hooks: `CONTEXT_WATERMARK_SOFT` / `_HARD`",
      "worked-example-1--hooks-context_watermark_soft--_hard",
    ],
    ["### Per-project settings — `atelier.local.md`", "per-project-settings--atelierlocalmd"],
    ["# Decision NNN · <decision title>", "decision-nnn--"],
  ];
  for (const [heading, id] of rows) {
    test(heading, async () => {
      const rendered = await renderPage("docs/page.md", `${heading}\n`);
      expect(rendered.body).toContain(` id="${id}"`);
      expect(rendered.ids.has(id)).toBe(true);
    });
  }

  test("repeated headings get -1, -2", async () => {
    const html = await body("# Page\n\n## Install\n\n## Install\n\n### Install\n");
    expect(html).toContain('<h2 id="install">Install</h2>');
    expect(html).toContain('<h2 id="install-1">Install</h2>');
    expect(html).toContain('<h3 id="install-2">Install</h3>');
  });

  test("entities and markup in headings", async () => {
    const html = await body("# Install &amp; *catalog* <span>now</span>\n\n#### Ünïcode 日本\n");
    expect(html).toContain('<h1 id="install--catalog-now">');
    expect(html).toContain('<h4 id="ünïcode-日本">');
  });

  test("raw HTML ids are collected and a raw heading id is kept", async () => {
    const rendered = await renderPage("a.md", '# A\n\n<h2 id="custom">Raw</h2>\n\n<a id="anchor"></a>\n');
    expect(rendered.body).toContain('<h2 id="custom">Raw</h2>');
    expect([...rendered.ids].sort()).toEqual(["a", "anchor", "custom"]);
  });
});

describe("frontmatter and titles", () => {
  test("shape 1: id, title, date, status and no H1 gets the title as H1", async () => {
    const rendered = await renderPage(
      "docs/decisions/0021-kaneo.md",
      "---\nid: \"decision-021\"\ntitle: retired primitives are sunset by decision record, tag, and deletion (applied to kaneo)\ndate: '2026-09-08'\nstatus: accepted\n---\n**Amended 2026-09-08:** After the Kaneo retirement, …\n",
    );
    expect(rendered.body.startsWith(
      '<h1 id="retired-primitives-are-sunset-by-decision-record-tag-and-deletion-applied-to-kaneo">retired primitives are sunset by decision record, tag, and deletion (applied to kaneo)</h1>\n<p><strong>Amended',
    )).toBe(true);
    expect(rendered.body).not.toContain("status");
    expect(rendered.title).toBe("retired primitives are sunset by decision record, tag, and deletion (applied to kaneo)");
  });

  test("shape 2: title, id, type, status, created, summary followed by an H1 keeps its H1", async () => {
    const rendered = await renderPage(
      "docs/decisions/0030-x.md",
      "---\ntitle: frontmatter title\nid: decision-030\ntype: decision\nstatus: accepted\ncreated: 2026-08-01\nsummary: one line\n---\n\n# Decision 030 · The real   title\n\nText\n",
    );
    expect(rendered.body.match(/<h1/g)).toHaveLength(1);
    expect(rendered.body).toContain('<h1 id="decision-030--the-real---title">');
    expect(rendered.title).toBe("Decision 030 · The real title");
  });

  test("no frontmatter title: the file name, HTML-escaped", async () => {
    const rendered = await renderPage("docs/a<b>.md", "Just text\n");
    expect(rendered.body.startsWith('<h1 id="ab">a&lt;b&gt;</h1>')).toBe(true);
    expect(rendered.title).toBe("a&lt;b&gt;");
  });

  test("an empty title falls back to the file name", async () => {
    expect(await body("---\ntitle: '  '\n---\ntext\n", "docs/notes.md")).toStartWith('<h1 id="notes">notes</h1>');
  });

  test("a Setext H1 counts; a # line in a code block does not", async () => {
    expect((await body("Title\n=====\n")).match(/<h1/g)).toHaveLength(1);
    expect(await body("```\n# not a heading\n```\n", "x/code.md")).toStartWith('<h1 id="code">code</h1>');
  });

  test("frontmatter is recognised only at the very top", async () => {
    const html = await body("\n---\ntitle: x\n---\n");
    expect(html).toContain("title: x");
  });

  test("frontmatter may end with ...", async () => {
    expect(await body("---\ntitle: Dots\n...\nbody\n")).toStartWith('<h1 id="dots">Dots</h1>\n<p>body</p>');
  });

  test("invalid YAML fails the page", async () => {
    await expect(renderPage("docs/bad.md", "---\ntitle: [\n---\n")).rejects.toThrow(
      new PageError("docs/bad.md: bad frontmatter: YAML Parse error: Unexpected token"),
    );
  });

  test("YAML that is not a mapping fails the page", async () => {
    await expect(renderPage("docs/list.md", "---\n- a\n- b\n---\n")).rejects.toThrow(
      "docs/list.md: bad frontmatter: not a mapping (got a list)",
    );
    await expect(renderPage("docs/text.md", "---\njust text\n---\n")).rejects.toThrow(
      "docs/text.md: bad frontmatter: not a mapping (got a string)",
    );
  });
});

describe("Markdown", () => {
  test("GFM tables with alignment, strikethrough, task lists, autolinks and hard breaks", async () => {
    const html = await body(
      "# T\n\n| a | b |\n|:--|--:|\n| x | ~~y~~ |\n\n- [x] done\n- [ ] todo\n\nhttps://example.com and www.example.com\nline  \nnext\n",
    );
    expect(html).toContain('<table tabindex="0">');
    expect(html).toContain('<th align="left">a</th><th align="right">b</th>');
    expect(html).toContain("<del>y</del>");
    expect(html).toContain('<input type="checkbox" class="task-list-item-checkbox" disabled checked>done');
    expect(html).toContain('<a href="https://example.com">https://example.com</a>');
    expect(html).toContain('<a href="http://www.example.com">www.example.com</a>');
    expect(html).toContain("line<br />\nnext");
  });

  test("raw HTML passes through, unknown tags included", async () => {
    const html = await body('# T\n\nThe <id> field and <kbd>x</kbd>.\n\n<div align="center">\n<b>raw</b>\n</div>\n');
    expect(html).toContain("<p>The <id> field and <kbd>x</kbd>.</p>");
    expect(html).toContain('<div align="center">\n<b>raw</b>\n</div>');
  });

  test("a mermaid fence becomes <pre class=mermaid> with only the escaped source", async () => {
    const rendered = await renderPage("m.md", "# M\n\n```mermaid\ngraph TD; A-->B & C<D\n```\n");
    expect(rendered.body).toContain('<pre class="mermaid" tabindex="0">graph TD; A--&gt;B &amp; C&lt;D\n</pre>');
    expect(rendered.body).not.toContain("<code");
    expect(rendered.mermaid).toBe(true);
  });

  test("other code blocks keep <code class=language-...>, escaped, without highlighting", async () => {
    const rendered = await renderPage("c.md", '# C\n\n```ts\nconst a = "<b>";\n```\n\n```\nplain\n```\n\n    indented\n');
    expect(rendered.body).toContain('<pre tabindex="0"><code class="language-ts">const a = &quot;&lt;b&gt;&quot;;\n</code></pre>');
    expect(rendered.body).toContain('<pre tabindex="0"><code>plain\n</code></pre>');
    expect(rendered.body).toContain('<pre tabindex="0"><code>indented\n</code></pre>');
    expect(rendered.mermaid).toBe(false);
  });

  test("raw <pre> and <table> get tabindex too", async () => {
    const html = await body("# R\n\n<pre>raw</pre>\n\n<table><tr><td>x</td></tr></table>\n");
    expect(html).toContain('<pre tabindex="0">raw</pre>');
    expect(html).toContain('<table tabindex="0">');
  });
});

describe("decodeEntities", () => {
  test("numeric and named references", () => {
    expect(decodeEntities("&amp;&lt;&#42;&#x2014;&mdash;&unknown;")).toBe("&<*——&unknown;");
  });
});
