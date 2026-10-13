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

describe("site serve", () => {
  /** Starts `site serve`, waits for its two lines, and returns them with the process. */
  async function serve(args: string[]) {
    const child = Bun.spawn([process.execPath, CLI, "serve", ...args], { cwd: UNIT, stdout: "pipe", stderr: "pipe" });
    const reader = child.stdout.getReader();
    let stdout = "";
    while (!stdout.includes("Ctrl-C to stop)\n")) {
      const { value, done } = await reader.read();
      if (done) break;
      stdout += new TextDecoder().decode(value);
    }
    return { child, stdout };
  }

  test("builds, prints the build line and the address, and serves under the base", async () => {
    const root = await checkout(DOTFILES);
    const output = join(await tempDir(), "out");
    const { child, stdout } = await serve(["--root", root, "--output", output, "--port", "0"]);
    try {
      const [built, serving] = stdout.trimEnd().split("\n");
      expect(built).toBe(`10 pages built, links verified: ${output}`);
      const match = /^Serving http:\/\/127\.0\.0\.1:(\d+)\/dotfiles-agents\/ \(Ctrl-C to stop\)$/.exec(serving!);
      expect(match).not.toBeNull();
      const home = await fetch(`http://127.0.0.1:${match![1]}/dotfiles-agents/`);
      expect(home.status).toBe(200);
      expect(await home.text()).toContain("<title>Documentation · dotfiles-agents</title>");
      // Never rebuilds: a page removed from the output stays removed.
      await Bun.file(join(output, "README.html")).delete();
      expect((await fetch(`http://127.0.0.1:${match![1]}/dotfiles-agents/README.html`)).status).toBe(404);
    } finally {
      child.kill();
      await child.exited;
    }
  });

  test("a taken port exits 1", async () => {
    const holder = Bun.serve({ hostname: "127.0.0.1", port: 0, fetch: () => new Response("busy") });
    try {
      const child = Bun.spawn(
        [process.execPath, CLI, "serve", "--root", await checkout(DOTFILES), "--output", join(await tempDir(), "out"), "--port", String(holder.port)],
        { cwd: UNIT, stdout: "pipe", stderr: "pipe" },
      );
      expect(await child.exited).toBe(1);
      expect(await new Response(child.stderr).text()).toBe(`serve: port ${holder.port} is taken\n`);
    } finally {
      holder.stop(true);
    }
  });

  test("a failed build exits 1 without serving", () => {
    const result = site(["serve", "--root", "/nonexistent/checkout", "--port", "0"]);
    expect(result).toEqual({
      code: 1,
      stdout: "",
      stderr: "/nonexistent/checkout: checkout folder not found\nbuild: 1 problems; nothing written\n",
    });
  });

  for (const [args, reason] of [
    [["--port", "http"], "bad port: http"],
    [["--port", "70000"], "bad port: 70000"],
    [["--watch"], "unknown option: --watch"],
  ] as [string[], string][]) {
    test(`site serve ${args.join(" ")} prints usage`, () => {
      expect(site(["serve", ...args])).toEqual({ code: 1, stdout: "", stderr: `site: ${reason}\n${USAGE}\n` });
    });
  }
});
