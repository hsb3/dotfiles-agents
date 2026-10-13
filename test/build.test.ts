import { describe, expect, test } from "bun:test";
import { readdir, symlink } from "node:fs/promises";
import { join, relative } from "node:path";
import { build, defaultOutput, type BuildOptions } from "../src/build.ts";
import { checkout, DOTFILES, specConfig, tempDir, UNIT, writeTree } from "./fixture.ts";

const STYLESHEET = join(UNIT, "assets", "site.css");

/** A checkout plus a config file written next to it (outside the checkout). */
async function setup(files: Record<string, string | { link: string }> = DOTFILES, config?: Record<string, unknown>) {
  const root = await checkout(files);
  const dir = await tempDir();
  const configPath = join(dir, "site.config.json");
  await Bun.write(configPath, JSON.stringify(config ?? (await specConfig())));
  const options: BuildOptions = {
    root,
    config: configPath,
    configLabel: "site.config.json",
    stylesheet: STYLESHEET,
    output: join(dir, "out"),
  };
  return { root, dir, options, output: join(dir, "out") };
}

async function files(folder: string): Promise<string[]> {
  return (await readdir(folder, { recursive: true, withFileTypes: true }))
    .filter((entry) => entry.isFile())
    .map((entry) => relative(folder, join(entry.parentPath, entry.name)))
    .sort();
}

async function read(output: string, path: string): Promise<string> {
  return Bun.file(join(output, path)).text();
}

describe("a successful build", () => {
  test("writes every page and the stylesheet", async () => {
    const { options, output } = await setup();
    const result = await build(options);
    expect(result).toMatchObject({ ok: true, output, pages: 10 });
    expect(await files(output)).toEqual([
      "README.html",
      "assets/site.css",
      "contributing.html",
      "docs/codex-compatibility.html",
      "docs/decisions/0021-kaneo.html",
      "docs/decisions/0030-split.html",
      "docs/decisions/README.html",
      "docs/licenses.html",
      "index.html",
      "plugins/atelier/README.html",
      "plugins/bun/README.html",
    ]);
    const css = await Bun.file(join(output, "assets/site.css")).bytes();
    expect(css).toEqual(await Bun.file(STYLESHEET).bytes());
  });

  test("docs/README.md becomes index.html with the SPEC link rewrites", async () => {
    const { options, output } = await setup();
    await build(options);
    const html = await read(output, "index.html");
    expect(html).toContain("<title>Documentation · dotfiles-agents</title>");
    expect(html).toContain('<a href="/dotfiles-agents/index.html" aria-current="page">Documentation</a>');
    for (const url of [
      "/dotfiles-agents/docs/codex-compatibility.html",
      "/dotfiles-agents/plugins/atelier/README.html",
      "https://github.com/hsb3/dotfiles-agents/blob/dev/docs/decisions/0000-template.md",
      "/dotfiles-agents/docs/decisions/README.html",
      "https://github.com/hsb3/dotfiles-agents/tree/dev/primitives-core",
      "#documentation",
    ]) {
      expect(html).toContain(`href="${url}"`);
    }
    expect(html).toContain('<img src="https://raw.githubusercontent.com/hsb3/dotfiles-agents/dev/docs/img/flow.png" alt="flow" />');
    expect(html).toContain(
      '<footer><a href="https://github.com/hsb3/dotfiles-agents/blob/dev/docs/README.md">View canonical Markdown</a> · <a href="/dotfiles-agents/docs/licenses.html">Licenses</a></footer>',
    );
  });

  test("the renamed CONTRIBUTING, both decision shapes, Mermaid and the symlinked plugin README", async () => {
    const { options, output } = await setup();
    await build(options);
    const contributing = await read(output, "contributing.html");
    expect(contributing).toContain('href="/dotfiles-agents/README.html#install"');
    expect(contributing).toContain(
      '<a href="https://github.com/hsb3/dotfiles-agents/blob/dev/.github/CONTRIBUTING.md">View canonical Markdown</a>',
    );

    const kaneo = await read(output, "docs/decisions/0021-kaneo.html");
    expect(kaneo).toContain(
      "<title>retired primitives are sunset by decision record, tag, and deletion (applied to kaneo) · dotfiles-agents</title>",
    );
    expect(kaneo).toContain(
      '<h1 id="retired-primitives-are-sunset-by-decision-record-tag-and-deletion-applied-to-kaneo">retired primitives are sunset by decision record, tag, and deletion (applied to kaneo)</h1>',
    );
    expect(kaneo).not.toContain("status: accepted");

    const split = await read(output, "docs/decisions/0030-split.html");
    expect(split).toContain("<title>Decision 030 · Split the catalog · dotfiles-agents</title>");
    expect(split.match(/<h1 /g)).toHaveLength(1);

    const codex = await read(output, "docs/codex-compatibility.html");
    expect(codex).toContain('<pre class="mermaid" tabindex="0">graph TD; A--&gt;B\n</pre>');
    expect(codex).toContain("</div>\n<script type=\"module\">");
    expect(await read(output, "README.html")).not.toContain("<script");

    const bun = await read(output, "plugins/bun/README.html");
    expect(bun).toContain('href="https://github.com/hsb3/dotfiles-agents/blob/dev/plugins/bun/notes.md"');
    expect(bun).toContain('href="/dotfiles-agents/plugins/atelier/README.html"');
    expect(bun).toContain('href="https://github.com/hsb3/dotfiles-agents/blob/dev/plugins/bun/README.md">View canonical Markdown');
  });

  test("no href or src is relative, and every root-relative URL names a built file", async () => {
    const { options, output } = await setup();
    await build(options);
    for (const path of await files(output)) {
      if (!path.endsWith(".html")) continue;
      const html = await read(output, path);
      for (const [, url] of html.matchAll(/\s(?:href|src)="([^"]*)"/g)) {
        if (/^(https?:|mailto:|#)/.test(url!)) continue;
        expect(url!.startsWith("/dotfiles-agents/")).toBe(true);
        const file = decodeURIComponent(url!.replace(/[?#].*$/, "").slice("/dotfiles-agents/".length));
        expect(await Bun.file(join(output, file)).exists()).toBe(true);
      }
    }
  });

  test("--ref sets the ref of every GitHub link", async () => {
    const { options, output } = await setup();
    await build({ ...options, ref: "0123456789abcdef" });
    const html = await read(output, "index.html");
    expect(html).toContain("https://github.com/hsb3/dotfiles-agents/tree/0123456789abcdef/primitives-core");
    expect(html).not.toContain("/dev/");
  });

  test("the same checkout, config and ref give byte-identical output", async () => {
    const first = await setup();
    await build(first.options);
    const second = await build({ ...first.options, output: join(first.dir, "again") });
    expect(second.ok).toBe(true);
    const paths = await files(first.output);
    expect(await files(join(first.dir, "again"))).toEqual(paths);
    for (const path of paths) {
      expect(await read(join(first.dir, "again"), path)).toBe(await read(first.output, path));
    }
  });

  test("overwrites files of the same name and leaves other files alone", async () => {
    const { options, output } = await setup();
    await writeTree(output, { "README.html": "stale", "old.html": "left over", "assets/other.css": "x" });
    await build(options);
    expect(await read(output, "README.html")).toStartWith("<!doctype html>");
    expect(await read(output, "old.html")).toBe("left over");
    expect(await read(output, "assets/other.css")).toBe("x");
  });

  test("the default output folder is /tmp/<name>-site/<name>", () => {
    expect(defaultOutput("dotfiles-agents")).toBe("/tmp/dotfiles-agents-site/dotfiles-agents");
  });
});

describe("a failed build", () => {
  test("reports every problem, sorted by page then position, and writes nothing", async () => {
    const { options, output } = await setup({
      ...DOTFILES,
      "docs/licenses.md": "---\ntitle: [\n---\n",
      "docs/README.md": "# Documentation\n\n[gone](../scripts/gone.py) [typo](../README.md#instal) [old](old.md)\n",
      "README.md": "# Repo\n\n[self](#nowhere) [bad page](docs/licenses.md#x)\n",
      "docs/decisions/README.md": "# Decisions\n\n- [list](0040-list.md)\n",
      "docs/decisions/0040-list.md": "---\n- a\n---\n",
    });
    await writeTree(output, { "docs/old.html": "a file from an earlier build" });
    const result = await build(options);
    expect(result).toEqual({
      ok: false,
      problems: [
        ".github/CONTRIBUTING.md: missing heading: ../README.md#install",
        "README.md: missing heading: #nowhere",
        "docs/README.md: broken local link: ../scripts/gone.py",
        "docs/README.md: missing heading: ../README.md#instal",
        "docs/README.md: broken local link: old.md",
        "docs/decisions/0040-list.md: bad frontmatter: not a mapping (got a list)",
        "docs/licenses.md: bad frontmatter: YAML Parse error: Unexpected token",
      ],
    });
    expect(await files(output)).toEqual(["docs/old.html"]);
  });

  test("config problems name the config path", async () => {
    const config = { ...(await specConfig()), base: "/a/b", extra: 1 };
    const { options } = await setup(DOTFILES, config);
    expect(await build(options)).toEqual({
      ok: false,
      problems: [
        'site.config.json: unknown key "extra"',
        'site.config.json: bad base "/a/b": expected / followed by one segment of A-Z a-z 0-9 _ -',
      ],
    });
  });

  test("an output folder that is the checkout, inside it, or reaches it through a symlink is refused", async () => {
    const { root, dir, options } = await setup();
    await symlink(join(root, "docs"), join(dir, "link"));
    for (const output of [root, join(root, "site-out"), join(dir, "link", "deeper")]) {
      const result = await build({ ...options, output });
      expect(result).toEqual({ ok: false, problems: [`${output}: output folder is the checkout or lies inside it`] });
    }
    expect(await Bun.file(join(root, "site-out")).exists()).toBe(false);
  });

  test("a missing checkout or stylesheet", async () => {
    const { dir, options } = await setup();
    expect(await build({ ...options, root: join(dir, "nope") })).toEqual({
      ok: false,
      problems: [`${join(dir, "nope")}: checkout folder not found`],
    });
    const missing = join(dir, "missing.css");
    expect(await build({ ...options, stylesheet: missing })).toEqual({
      ok: false,
      problems: [`${missing}: stylesheet not found`],
    });
  });
});
