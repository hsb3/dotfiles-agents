import { describe, expect, test } from "bun:test";
import { parseConfig } from "../src/config.ts";
import { layoutPage, MERMAID_SCRIPT } from "../src/layout.ts";
import { selectPages, type Site } from "../src/pages.ts";
import { checkout } from "./fixture.ts";

async function site(): Promise<Site> {
  const root = await checkout({
    "README.md": "",
    ".github/CONTRIBUTING.md": "",
    "docs/README.md": "",
    "docs/codex-compatibility.md": "",
    "docs/decisions/README.md": "",
    "docs/decisions/0000-template.md": "",
    "docs/licenses.md": "",
    "plugins/atelier/README.md": "",
  });
  const config = parseConfig(await Bun.file(`${import.meta.dir}/../site.config.json`).json(), "site.config.json");
  return selectPages(config, root);
}

const H2S = ["Distribution and setup", "Worker isolation", "Atelier member verdicts", "Other bundles and prerequisites", "Repeatable local checks"];

describe("the SPEC page document", () => {
  test("docs/codex-compatibility.md at ref dev", async () => {
    const s = await site();
    const body = [
      '<h1 id="codex-distribution-and-runtime-contract">Codex distribution and runtime contract</h1>',
      "<p>Intro.</p>",
      ...H2S.map((text) => `<h2 id="${text.toLowerCase().replace(/ /g, "-")}">${text}</h2>`),
      "",
    ].join("\n");
    const html = await layoutPage({
      site: s,
      ref: "dev",
      page: s.byPath.get("docs/codex-compatibility.md")!,
      title: "Codex distribution and runtime contract",
      body,
      mermaid: false,
    });
    expect(html).toBe(`<!doctype html>
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
${body.trimEnd()}
<footer><a href="https://github.com/hsb3/dotfiles-agents/blob/dev/docs/codex-compatibility.md">View canonical Markdown</a> · <a href="/dotfiles-agents/docs/licenses.html">Licenses</a></footer>
</main>
</div>
</body>
</html>
`);
  });
});

describe("parts", () => {
  async function render(body: string, mermaid = false, path = "README.md", ref = "dev") {
    const s = await site();
    return layoutPage({ site: s, ref, page: s.byPath.get(path)!, title: "T &amp; U", body, mermaid });
  }

  test("aria-current marks only the current page; titles stay escaped", async () => {
    const html = await render('<h1 id="t">T</h1>');
    expect(html).toContain('<a href="/dotfiles-agents/README.html" aria-current="page">Install &amp; catalog</a>');
    expect(html.match(/aria-current/g)).toHaveLength(1);
    expect(html).toContain("<title>T &amp; U · dotfiles-agents</title>");
  });

  test("a page with no nav entry has no aria-current", async () => {
    expect(await render('<h1 id="t">T</h1>', false, "docs/licenses.md")).not.toContain("aria-current");
  });

  test("no contents block without an H2", async () => {
    expect(await render('<h1 id="a">A</h1>\n<h3 id="b">B</h3>\n')).not.toContain("<details");
  });

  test("contents: H2 before any H1 is top level; links unwrapped, code kept, ids dropped; H1 without H2 is a leaf", async () => {
    const html = await render(
      [
        '<h2 id="early">Early</h2>',
        '<h1 id="first">First <a href="/x.html">link</a></h1>',
        '<h1 id="second">Second</h1>',
        '<h2 id="code-x">Code <code>x</code> <span id="raw">raw</span></h2>',
        "<h3 id=\"deep\">Deep</h3>",
      ].join("\n"),
    );
    expect(html).toContain(`<details class="contents"><summary>On this page</summary><ul>
<li><a href="#early">Early</a></li>
<li><a href="#first">First link</a></li>
<li><a href="#second">Second</a><ul>
<li><a href="#code-x">Code <code>x</code> <span>raw</span></a></li>
</ul></li>
</ul></details>`);
  });

  test("footer links the listed path at the build ref", async () => {
    const html = await render('<h1 id="t">T</h1>', false, ".github/CONTRIBUTING.md", "abc123");
    expect(html).toContain(
      '<footer><a href="https://github.com/hsb3/dotfiles-agents/blob/abc123/.github/CONTRIBUTING.md">View canonical Markdown</a> · <a href="/dotfiles-agents/docs/licenses.html">Licenses</a></footer>',
    );
  });

  test("the Mermaid script follows </div> only on pages with a diagram", async () => {
    const withDiagram = await render('<h1 id="t">T</h1>\n<pre class="mermaid">graph TD</pre>', true);
    expect(withDiagram).toContain(`</div>\n${MERMAID_SCRIPT}\n</body>`);
    expect(MERMAID_SCRIPT).toContain("mermaid@11.12.0/dist/mermaid.esm.min.mjs");
    expect(await render('<h1 id="t">T</h1>')).not.toContain("<script");
  });
});

test("the Mermaid script is the SPEC's, verbatim", async () => {
  const spec = await Bun.file(`${import.meta.dir}/../SPEC.md`).text();
  const block = /\n( {2}<script type="module">[\s\S]*? {2}<\/script>)\n/.exec(spec)![1]!;
  expect(MERMAID_SCRIPT).toBe(block.replace(/^ {2}/gm, ""));
});
