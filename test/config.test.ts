import { describe, expect, test } from "bun:test";
import { join } from "node:path";
import { ConfigError, loadConfig, parseConfig } from "../src/config.ts";
import { tempDir } from "./fixture.ts";

const UNIT = join(import.meta.dir, "..");

function problems(data: unknown): string[] {
  try {
    parseConfig(data, "site.config.json");
  } catch (error) {
    if (error instanceof ConfigError) return error.problems;
    throw error;
  }
  throw new Error("expected a ConfigError");
}

describe("shipped site.config.json", () => {
  test("holds exactly the SPEC values", async () => {
    const data = await Bun.file(join(UNIT, "site.config.json")).json();
    expect(data).toEqual({
      repo: "hsb3/dotfiles-agents",
      ref: "dev",
      pages: ["README.md", ".github/CONTRIBUTING.md", "docs/**/*.md", "plugins/*/README.md"],
      exclude: ["docs/decisions/0000-template.md"],
      rename: { "docs/README.md": "index.html", ".github/CONTRIBUTING.md": "contributing.html" },
      nav: [
        { label: "Documentation", page: "docs/README.md" },
        { label: "Install & catalog", page: "README.md" },
        { label: "Codex support", page: "docs/codex-compatibility.md" },
        { label: "Atelier setup", page: "plugins/atelier/README.md" },
        { label: "Contribute", page: ".github/CONTRIBUTING.md" },
        { label: "Decision history", page: "docs/decisions/README.md" },
      ],
      footer: [{ label: "Licenses", page: "docs/licenses.md" }],
    });
  });

  test("loads with the default base and site name", async () => {
    const config = await loadConfig(join(UNIT, "site.config.json"), "site.config.json");
    expect(config.base).toBe("/dotfiles-agents");
    expect(config.name).toBe("dotfiles-agents");
    expect(config.ref).toBe("dev");
    expect(config.nav).toHaveLength(6);
    expect(config.footer).toEqual([{ label: "Licenses", page: "docs/licenses.md" }]);
  });
});

describe("base", () => {
  test("defaults to /<name> from repo", () => {
    const config = parseConfig({ repo: "me/My_site-2", ref: "main" }, "c.json");
    expect(config.base).toBe("/My_site-2");
    expect(config.name).toBe("My_site-2");
  });

  test("an explicit base sets the site name", () => {
    const config = parseConfig({ repo: "me/x", ref: "main", base: "/docs" }, "c.json");
    expect(config.base).toBe("/docs");
    expect(config.name).toBe("docs");
  });

  for (const base of ["docs", "/", "/a/b", "/a b", "/a.b", "/docs/", ""]) {
    test(`rejects ${JSON.stringify(base)}`, () => {
      expect(problems({ repo: "me/x", ref: "main", base })).toEqual([
        `site.config.json: bad base "${base}": expected / followed by one segment of A-Z a-z 0-9 _ -`,
      ]);
    });
  }

  test("a repo name that cannot be a base asks for one", () => {
    expect(problems({ repo: "me/my.site", ref: "main" })).toEqual([
      `site.config.json: bad base "/my.site" from repo: set "base" to / followed by one segment of A-Z a-z 0-9 _ -`,
    ]);
  });
});

describe("problems", () => {
  test("missing repo and ref", () => {
    expect(problems({})).toEqual([`site.config.json: missing key "repo"`, `site.config.json: missing key "ref"`]);
  });

  test("unknown keys, top level and in links", () => {
    expect(
      problems({ repo: "me/x", ref: "main", title: "x", nav: [{ label: "A", page: "a.md", icon: "i" }] }),
    ).toEqual([`site.config.json: unknown key "title"`, `site.config.json: nav[0]: unknown key "icon"`]);
  });

  test("wrong types", () => {
    expect(
      problems({
        repo: 1,
        ref: false,
        base: 2,
        pages: "README.md",
        exclude: [1],
        rename: { "a.md": 3 },
        nav: {},
        footer: [{ label: "", page: 2 }, "x", { label: "L" }],
      }),
    ).toEqual([
      `site.config.json: "repo" must be a string`,
      `site.config.json: "ref" must be a string`,
      `site.config.json: "base" must be a string`,
      `site.config.json: "pages" must be a list of non-empty strings`,
      `site.config.json: "exclude" must be a list of non-empty strings`,
      `site.config.json: "rename" must map page paths to non-empty output paths`,
      `site.config.json: "nav" must be a list of { "label", "page" } entries`,
      `site.config.json: footer[0]: "label" must be a non-empty string`,
      `site.config.json: footer[0]: "page" must be a non-empty string`,
      `site.config.json: footer[1] must be a { "label", "page" } entry`,
      `site.config.json: footer[2]: missing key "page"`,
    ]);
  });

  test("bad repo and empty ref", () => {
    expect(problems({ repo: "dotfiles-agents", ref: "" })).toEqual([
      `site.config.json: bad repo "dotfiles-agents": expected <owner>/<name>`,
      `site.config.json: "ref" must not be empty`,
    ]);
  });

  test("not an object", () => {
    expect(problems([])).toEqual([`site.config.json: config must be a JSON object`]);
  });

  test("unreadable file and invalid JSON name the config path", async () => {
    const dir = await tempDir();
    const missing = join(dir, "nope.json");
    await expect(loadConfig(missing, "nope.json")).rejects.toThrow(/^nope\.json: cannot read config: /);
    await Bun.write(join(dir, "bad.json"), "{ repo: ");
    await expect(loadConfig(join(dir, "bad.json"), "bad.json")).rejects.toThrow(/^bad\.json: invalid JSON: /);
  });
});
