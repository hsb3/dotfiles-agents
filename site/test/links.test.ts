import { describe, expect, test } from "bun:test";
import { parseConfig } from "../src/config.ts";
import { rewriteLinks, type LinkContext } from "../src/links.ts";
import { selectPages } from "../src/pages.ts";
import { checkout } from "./fixture.ts";

async function context(ref = "dev"): Promise<LinkContext> {
  const root = await checkout({
    "README.md": "# Repo\n",
    LICENSE: "MIT",
    ".github/CONTRIBUTING.md": "# Contributing\n",
    "docs/README.md": "# Documentation\n",
    "docs/atelier-parity.md": "# Parity\n",
    "docs/My Notes.md": "# Notes\n",
    "docs/img/flow.png": "png",
    "docs/decisions/README.md": "# Decisions\n",
    "docs/decisions/0000-template.md": "# Template\n",
    "plugins/atelier/README.md": "# Atelier\n",
    "plugins/bun/README.md": { link: "../../primitives-core/skills/bun/README.md" },
    "plugins/bun/notes.md": "plugin-local notes",
    "primitives-core/skills/bun/README.md": "# Bun\n[notes](notes.md)\n",
    "primitives-core/skills/bun/notes.md": "skill-local notes",
    "primitives-core/escape": { link: "../.." },
    "docs/outside.md": { link: "../../outside.md" },
  });
  const config = parseConfig(
    {
      repo: "hsb3/dotfiles-agents",
      ref: "dev",
      pages: ["README.md", ".github/CONTRIBUTING.md", "docs/**/*.md", "plugins/*/README.md"],
      exclude: ["docs/decisions/0000-template.md"],
      rename: { "docs/README.md": "index.html", ".github/CONTRIBUTING.md": "contributing.html" },
    },
    "site.config.json",
  );
  const site = await selectPages(config, root);
  const ids = new Map(site.pages.map((page) => [page.path, new Set(["content"])]));
  ids.get("README.md")!.add("install");
  ids.get("docs/README.md")!.add("documentation");
  ids.get("docs/My Notes.md")!.add("üï");
  return { site, ref, ids };
}

async function rewrite(context: LinkContext, path: string, body: string) {
  return rewriteLinks(context, context.site.byPath.get(path)!, body);
}

async function href(context: LinkContext, path: string, written: string): Promise<string> {
  const { body, problems } = await rewrite(context, path, `<p><a href="${written}">x</a></p>`);
  expect(problems).toEqual([]);
  return /href="([^"]*)"/.exec(body)![1]!;
}

describe("SPEC examples from docs/README.md at ref dev", () => {
  const rows: [string, string][] = [
    ["../README.md#install", "/dotfiles-agents/README.html#install"],
    ["../.github/CONTRIBUTING.md", "/dotfiles-agents/contributing.html"],
    ["../plugins/atelier/", "/dotfiles-agents/plugins/atelier/README.html"],
    ["atelier-parity.md", "/dotfiles-agents/docs/atelier-parity.html"],
    ["#documentation", "#documentation"],
    ["../LICENSE", "https://github.com/hsb3/dotfiles-agents/blob/dev/LICENSE"],
    ["../primitives-core", "https://github.com/hsb3/dotfiles-agents/tree/dev/primitives-core"],
    [
      "decisions/0000-template.md",
      "https://github.com/hsb3/dotfiles-agents/blob/dev/docs/decisions/0000-template.md",
    ],
    ["https://hsb3.github.io/dotfiles-agents/", "https://hsb3.github.io/dotfiles-agents/"],
  ];
  for (const [written, becomes] of rows) {
    test(written, async () => {
      expect(await href(await context(), "docs/README.md", written)).toBe(becomes);
    });
  }

  test("![flow](img/flow.png)", async () => {
    const { body } = await rewrite(await context(), "docs/README.md", '<img src="img/flow.png" alt="flow" />');
    expect(body).toBe('<img src="https://raw.githubusercontent.com/hsb3/dotfiles-agents/dev/docs/img/flow.png" alt="flow" />');
  });

  test("broken local link and missing heading", async () => {
    const { problems } = await rewrite(
      await context(),
      "docs/README.md",
      '<a href="../scripts/gone.py">a</a><a href="../README.md#instal">b</a>',
    );
    expect(problems).toEqual([
      "docs/README.md: broken local link: ../scripts/gone.py",
      "docs/README.md: missing heading: ../README.md#instal",
    ]);
  });
});

describe("resolution", () => {
  test("a symlinked page resolves links from its listed folder", async () => {
    const ctx = await context();
    expect(await href(ctx, "plugins/bun/README.md", "notes.md")).toBe(
      "https://github.com/hsb3/dotfiles-agents/blob/dev/plugins/bun/notes.md",
    );
    expect(await href(ctx, "plugins/bun/README.md", "../../docs/")).toBe("/dotfiles-agents/index.html");
  });

  test("root-relative paths start at the checkout root; the root folder is its README page", async () => {
    const ctx = await context();
    expect(await href(ctx, "docs/atelier-parity.md", "/LICENSE")).toBe(
      "https://github.com/hsb3/dotfiles-agents/blob/dev/LICENSE",
    );
    expect(await href(ctx, "docs/atelier-parity.md", "/")).toBe("/dotfiles-agents/README.html");
    expect(await href(ctx, "docs/atelier-parity.md", "..")).toBe("/dotfiles-agents/README.html");
  });

  test("percent-encoded paths are decoded, then re-encoded; fragments compared decoded", async () => {
    const ctx = await context();
    expect(await href(ctx, "docs/README.md", "My%20Notes.md#%C3%BC%C3%AF")).toBe(
      "/dotfiles-agents/docs/My%20Notes.html#%C3%BC%C3%AF",
    );
  });

  test("query and fragment are kept as written; entities in attributes are handled", async () => {
    const ctx = await context();
    const { body } = await rewrite(ctx, "docs/README.md", '<a href="../LICENSE?plain=1&amp;x=2#L3">l</a>');
    expect(body).toBe('<a href="https://github.com/hsb3/dotfiles-agents/blob/dev/LICENSE?plain=1&amp;x=2#L3">l</a>');
  });

  test("fragments on GitHub links are not checked", async () => {
    expect(await href(await context(), "docs/README.md", "../LICENSE#nowhere")).toBe(
      "https://github.com/hsb3/dotfiles-agents/blob/dev/LICENSE#nowhere",
    );
  });

  test("a self link with a query, and an empty href, become the page URL", async () => {
    const ctx = await context();
    expect(await href(ctx, "docs/atelier-parity.md", "?tab=1#content")).toBe(
      "/dotfiles-agents/docs/atelier-parity.html?tab=1#content",
    );
    expect(await href(ctx, "docs/atelier-parity.md", "")).toBe("/dotfiles-agents/docs/atelier-parity.html");
  });

  test("the ref is the one passed, not the config's", async () => {
    expect(await href(await context("0123abc"), "docs/README.md", "../LICENSE")).toBe(
      "https://github.com/hsb3/dotfiles-agents/blob/0123abc/LICENSE",
    );
  });

  test("leaving the checkout through .. or a symlink is broken; so is a file with a trailing slash", async () => {
    const { problems } = await rewrite(
      await context(),
      "docs/README.md",
      [
        '<a href="../../outside.md">a</a>',
        '<a href="outside.md">b</a>',
        '<a href="../primitives-core/escape/">c</a>',
        '<a href="../LICENSE/">d</a>',
        '<img src="img/missing.png">',
        '<a href="#nope">e</a>',
        '<a href="%E0%A4%A">f</a>',
      ].join(""),
    );
    expect(problems).toEqual([
      "docs/README.md: broken local link: ../../outside.md",
      "docs/README.md: broken local link: outside.md",
      "docs/README.md: broken local link: ../primitives-core/escape/",
      "docs/README.md: broken local link: ../LICENSE/",
      "docs/README.md: broken local link: img/missing.png",
      "docs/README.md: missing heading: #nope",
      "docs/README.md: broken local link: %E0%A4%A",
    ]);
  });

  test("raw HTML links and schemes", async () => {
    const ctx = await context();
    const { body } = await rewrite(
      ctx,
      "docs/README.md",
      "<a href='atelier-parity.md'>p</a> <a href=\"mailto:me@example.com\">m</a> <a href=\"//cdn.example.com/x\">c</a> <a name=\"top\">t</a>",
    );
    expect(body).toBe(
      '<a href="/dotfiles-agents/docs/atelier-parity.html">p</a> <a href="mailto:me@example.com">m</a> <a href="//cdn.example.com/x">c</a> <a name="top">t</a>',
    );
  });
});
