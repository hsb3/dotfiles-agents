import { describe, expect, test } from "bun:test";
import { dirname, join } from "node:path";
import { DEFAULTS, USAGE } from "../src/commands.ts";
import { checkout, DOTFILES, specConfig, tempDir, UNIT } from "./fixture.ts";

const CLI = join(UNIT, "src", "cli.ts");

function site(args: string[], cwd = UNIT) {
  const result = Bun.spawnSync([process.execPath, CLI, ...args], { cwd, stdout: "pipe", stderr: "pipe" });
  return { code: result.exitCode, stdout: result.stdout.toString(), stderr: result.stderr.toString() };
}

describe("usage", () => {
  for (const [args, reason] of [
    [[], "missing command"],
    [["publish"], "unknown command: publish"],
    [["build", "--verbose"], "unknown option: --verbose"],
    [["build", "--root"], "option --root needs a value"],
    [["build", "--root", "--ref", "x"], "option --root needs a value"],
    [["build", "--port", "8000"], "unknown option: --port"],
    [["build", "extra"], "unknown option: extra"],
  ] as [string[], string][]) {
    test(`site ${args.join(" ")}`, () => {
      const result = site(args);
      expect(result).toEqual({ code: 1, stdout: "", stderr: `site: ${reason}\n${USAGE}\n` });
    });
  }
});

describe("site build", () => {
  test("prints the success line and exits 0; --opt=value works too", async () => {
    const root = await checkout(DOTFILES);
    const output = join(await tempDir(), "out");
    const result = site(["build", `--root=${root}`, "--output", output, "--ref", "main"]);
    expect(result).toEqual({ code: 0, stdout: `10 pages built, links verified: ${output}\n`, stderr: "" });
    expect(await Bun.file(join(output, "index.html")).text()).toContain("/blob/main/docs/README.md");
  });

  test("the default config is the unit's own, named relative to the working folder", async () => {
    const root = await checkout({ "README.md": "# Only\n" });
    const result = site(["build", "--root", root, "--output", join(await tempDir(), "out")]);
    expect(result.code).toBe(1);
    expect(result.stderr).toContain('site.config.json: pages entry ".github/CONTRIBUTING.md" matches no file\n');
    const elsewhere = site(["build", "--root", root, "--output", join(await tempDir(), "out")], root);
    expect(elsewhere.stderr).toContain(`${join(UNIT, "site.config.json")}: pages entry`);
  });

  test("problems go to stderr, then the summary line; exit 1", async () => {
    const root = await checkout({ ...DOTFILES, "docs/README.md": "# Documentation\n\n[gone](../scripts/gone.py)\n" });
    const output = join(await tempDir(), "out");
    const result = site(["build", "--root", root, "--output", output]);
    expect(result).toEqual({
      code: 1,
      stdout: "",
      stderr: "docs/README.md: broken local link: ../scripts/gone.py\nbuild: 1 problems; nothing written\n",
    });
    expect(await Bun.file(join(output, "index.html")).exists()).toBe(false);
  });

  test("--config names the file as given", async () => {
    const dir = await tempDir();
    await Bun.write(join(dir, "my.json"), JSON.stringify({ ...(await specConfig()), base: "nope" }));
    const result = site(["build", "--root", await checkout(DOTFILES), "--config", join(dir, "my.json"), "--output", join(dir, "out")]);
    expect(result.stderr).toBe(
      `${join(dir, "my.json")}: bad base "nope": expected / followed by one segment of A-Z a-z 0-9 _ -\nbuild: 1 problems; nothing written\n`,
    );
  });

  test("the defaults: root is the folder that contains the unit, config and stylesheet are the unit's", () => {
    expect(DEFAULTS).toEqual({
      root: dirname(UNIT),
      config: join(UNIT, "site.config.json"),
      stylesheet: join(UNIT, "assets", "site.css"),
    });
  });
});
