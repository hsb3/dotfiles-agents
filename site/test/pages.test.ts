import { describe, expect, test } from "bun:test";
import { ConfigError, parseConfig } from "../src/config.ts";
import { encodePath, githubUrl, readSource, selectPages, siteUrl } from "../src/pages.ts";
import { checkout } from "./fixture.ts";

const SPEC_CONFIG = {
  repo: "hsb3/dotfiles-agents",
  ref: "dev",
  pages: ["README.md", ".github/CONTRIBUTING.md", "docs/**/*.md", "plugins/*/README.md"],
  exclude: ["docs/decisions/0000-template.md"],
  rename: { "docs/README.md": "index.html", ".github/CONTRIBUTING.md": "contributing.html" },
  nav: [
    { label: "Documentation", page: "docs/README.md" },
    { label: "Install & catalog", page: "README.md" },
    { label: "Contribute", page: ".github/CONTRIBUTING.md" },
  ],
  footer: [{ label: "Licenses", page: "docs/licenses.md" }],
};

/** A small dotfiles-agents look-alike. */
function dotfilesCheckout() {
  return checkout({
    "README.md": "# Repo\n",
    ".github/CONTRIBUTING.md": "# Contributing\n",
    ".github/SECURITY.md": "# Security\n",
    "docs/README.md": "# Docs\n",
    "docs/licenses.md": "# Licenses\n",
    "docs/My Notes.md": "# Notes\n",
    "docs/img/flow.png": "png",
    "docs/decisions/README.md": "# Decisions\n",
    "docs/decisions/0000-template.md": "# Template\n",
    "docs/decisions/0001-first.md": "---\ntitle: first\n---\nBody\n",
    "docs/.drafts/hidden.md": "# Hidden\n",
    "docs/notes.txt": "not markdown",
    "plugins/atelier/README.md": "# Atelier\n",
    "plugins/.hidden/README.md": "# Hidden plugin\n",
    "plugins/bun/README.md": { link: "../../primitives-core/skills/bun/README.md" },
    "primitives-core/skills/bun/README.md": "# Bun skill\n",
  });
}

function configOf(overrides: Record<string, unknown> = {}) {
  return parseConfig({ ...SPEC_CONFIG, ...overrides }, "site.config.json");
}

async function problems(root: string, overrides: Record<string, unknown>): Promise<string[]> {
  try {
    await selectPages(configOf(overrides), root);
  } catch (error) {
    if (error instanceof ConfigError) return error.problems;
    throw error;
  }
  throw new Error("expected a ConfigError");
}

describe("selectPages", () => {
  test("expands globs, keeps explicit dot names, skips wildcard dot names, drops excludes", async () => {
    const root = await dotfilesCheckout();
    const site = await selectPages(configOf(), root);
    expect(site.pages.map((page) => page.path)).toEqual([
      ".github/CONTRIBUTING.md",
      "README.md",
      "docs/My Notes.md",
      "docs/README.md",
      "docs/decisions/0001-first.md",
      "docs/decisions/README.md",
      "docs/licenses.md",
      "plugins/atelier/README.md",
      "plugins/bun/README.md",
    ]);
  });

  test("assigns output paths and site URLs", async () => {
    const site = await selectPages(configOf(), await dotfilesCheckout());
    const outputs = Object.fromEntries(site.pages.map((page) => [page.path, [page.output, page.url]]));
    expect(outputs["README.md"]).toEqual(["README.html", "/dotfiles-agents/README.html"]);
    expect(outputs["docs/decisions/README.md"]).toEqual([
      "docs/decisions/README.html",
      "/dotfiles-agents/docs/decisions/README.html",
    ]);
    expect(outputs["plugins/atelier/README.md"]).toEqual([
      "plugins/atelier/README.html",
      "/dotfiles-agents/plugins/atelier/README.html",
    ]);
    expect(outputs["docs/README.md"]).toEqual(["index.html", "/dotfiles-agents/index.html"]);
    expect(outputs[".github/CONTRIBUTING.md"]).toEqual(["contributing.html", "/dotfiles-agents/contributing.html"]);
    expect(outputs["docs/My Notes.md"]).toEqual(["docs/My Notes.html", "/dotfiles-agents/docs/My%20Notes.html"]);
  });

  test("a symlinked page keeps its listed path and reads through it", async () => {
    const site = await selectPages(configOf(), await dotfilesCheckout());
    const page = site.byPath.get("plugins/bun/README.md")!;
    expect(page.output).toBe("plugins/bun/README.html");
    expect(await readSource(site, page)).toBe("# Bun skill\n");
  });

  test("** matches zero segments and does not cross dot folders", async () => {
    const root = await checkout({ "a.md": "", "x/.y/b.md": "", "x/c.md": "", "index.md": "" });
    const site = await selectPages(
      parseConfig({ repo: "o/s", ref: "r", pages: ["**/*.md"], rename: { "index.md": "index.html" } }, "c.json"),
      root,
    );
    expect(site.pages.map((page) => page.path)).toEqual(["a.md", "index.md", "x/c.md"]);
  });
});

describe("config problems from the page list", () => {
  test("entries that match nothing", async () => {
    const root = await dotfilesCheckout();
    expect(
      await problems(root, {
        pages: [...SPEC_CONFIG.pages, "guides/*.md", "../outside.md"],
        exclude: ["docs/decisions/0000-template.md", "docs/gone.md"],
      }),
    ).toEqual([
      `site.config.json: pages entry "guides/*.md" matches no file`,
      `site.config.json: pages entry "../outside.md" must be a repo-relative path`,
      `site.config.json: exclude entry "docs/gone.md" matches no page`,
    ]);
  });

  test("nav, footer and rename pages not in the page list", async () => {
    const root = await dotfilesCheckout();
    expect(
      await problems(root, {
        rename: { ...SPEC_CONFIG.rename, "docs/decisions/0000-template.md": "template.html", "docs/licenses.md": "../x.html" },
        nav: [...SPEC_CONFIG.nav, { label: "Template", page: "docs/decisions/0000-template.md" }],
        footer: [{ label: "Gone", page: "docs/gone.md" }],
      }),
    ).toEqual([
      `site.config.json: rename page docs/decisions/0000-template.md is not in the page list`,
      `site.config.json: rename of docs/licenses.md must be a relative output path: "../x.html"`,
      `site.config.json: nav page docs/decisions/0000-template.md is not in the page list`,
      `site.config.json: footer page docs/gone.md is not in the page list`,
    ]);
  });

  test("no page at index.html", async () => {
    const root = await dotfilesCheckout();
    expect(await problems(root, { rename: { ".github/CONTRIBUTING.md": "contributing.html" } })).toEqual([
      `site.config.json: no page publishes at index.html`,
    ]);
  });

  test("two pages with the same output path", async () => {
    const root = await dotfilesCheckout();
    expect(await problems(root, { rename: { ...SPEC_CONFIG.rename, "docs/licenses.md": "README.html" } })).toEqual([
      `site.config.json: README.md and docs/licenses.md would both publish at README.html`,
    ]);
  });

  test("an output path with a hidden segment", async () => {
    const root = await dotfilesCheckout();
    expect(await problems(root, { pages: [...SPEC_CONFIG.pages, ".github/SECURITY.md"] })).toEqual([
      `site.config.json: .github/SECURITY.md would publish at hidden path .github/SECURITY.html`,
    ]);
  });
});

describe("URLs", () => {
  test("segments are percent-encoded except unreserved characters", () => {
    expect(encodePath("docs/My Notes (1)!~_-.md")).toBe("docs/My%20Notes%20%281%29%21~_-.md");
    expect(encodePath("é/a#b?c")).toBe("%C3%A9/a%23b%3Fc");
    expect(siteUrl("/dotfiles-agents", "docs/My Notes.html")).toBe("/dotfiles-agents/docs/My%20Notes.html");
  });

  test("GitHub blob, tree and raw URLs", () => {
    expect(githubUrl("hsb3/dotfiles-agents", "dev", "blob", "LICENSE")).toBe(
      "https://github.com/hsb3/dotfiles-agents/blob/dev/LICENSE",
    );
    expect(githubUrl("hsb3/dotfiles-agents", "dev", "tree", "primitives-core")).toBe(
      "https://github.com/hsb3/dotfiles-agents/tree/dev/primitives-core",
    );
    expect(githubUrl("hsb3/dotfiles-agents", "dev", "raw", "docs/img/flow.png")).toBe(
      "https://raw.githubusercontent.com/hsb3/dotfiles-agents/dev/docs/img/flow.png",
    );
    expect(githubUrl("o/r", "feature/x", "tree", "")).toBe("https://github.com/o/r/tree/feature/x");
  });
});
