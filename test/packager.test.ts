import { afterAll, beforeAll, describe, expect, setDefaultTimeout, test } from "bun:test";
import { existsSync, lstatSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, statSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { runCli } from "./cli.ts";
import { api, freePort, HAS_POCKETBASE, pocketbaseBinary, REPO_ROOT, startPocketBase, type PbServer } from "./pb.ts";
import { WORKFLOWS_MD, writeSyntheticTree } from "./synthetic-tree.ts";

// Tests that spawn the CLI or a real PocketBase take seconds.
setDefaultTimeout(60000);

function specBlock(label: string): string {
  const spec = readFileSync(join(REPO_ROOT, "SPEC.md"), "utf8");
  const i = spec.indexOf(label);
  const open = spec.indexOf("```", i);
  const start = spec.indexOf("\n", open) + 1;
  const end = spec.indexOf("\n  ```", start);
  return spec.slice(start, end + 1).split("\n").map((l) => (l.startsWith("  ") ? l.slice(2) : l)).join("\n");
}

function writeUi(dir: string, extra: Record<string, string> = {}, html?: string): string {
  mkdirSync(join(dir, "assets"), { recursive: true });
  writeFileSync(join(dir, "index.html"), html ?? '<!doctype html><html><head><title>Toolbox</title><script type="module" crossorigin src="./assets/app.js"></script><link rel="stylesheet" href="/assets/app.css"></head><body></body></html>');
  writeFileSync(join(dir, "assets/app.js"), "console.log(1)\n");
  writeFileSync(join(dir, "assets/app.css"), "body{}\n");
  for (const [rel, content] of Object.entries(extra)) {
    mkdirSync(join(dir, rel, ".."), { recursive: true });
    writeFileSync(join(dir, rel), content);
  }
  return dir;
}

function tree(dir: string): string[] {
  const out: string[] = [];
  const walk = (d: string, rel: string) => {
    for (const name of readdirSync(d).sort()) {
      const p = join(d, name);
      const r = rel ? `${rel}/${name}` : name;
      if (statSync(p).isDirectory()) walk(p, r);
      else out.push(`${r} ${(statSync(p).mode & 0o777).toString(8)} ${Bun.hash(readFileSync(p))}`);
    }
  };
  walk(dir, "");
  return out;
}

describe("package", () => {
  let base: string;
  let src: string;
  let ui: string;
  beforeAll(() => {
    base = mkdtempSync(join(tmpdir(), "evals-pkg-"));
    src = join(base, "src-root");
    mkdirSync(src);
    writeSyntheticTree(src);
    ui = writeUi(join(base, "ui"));
  });
  afterAll(() => rmSync(base, { recursive: true, force: true }));

  test("builds the documented tree, byte-identical across runs", async () => {
    const a = join(base, "out", "a");
    const r = await runCli(["package", "--source-root", src, "--out", a, "--ui-build", ui]);
    expect(r.stderr).toBe("");
    expect(r).toMatchObject({ code: 0, stdout: `packaged ${a}\n` });
    const b = join(base, "out", "b");
    await runCli(["package", "--source-root", src, "--out", b, "--ui-build", ui]);
    expect(tree(a)).toEqual(tree(b));
    const migrations = readdirSync(join(REPO_ROOT, "pb_migrations")).sort();
    expect(tree(a).map((l) => l.split(" ")[0])).toEqual(
      [
        "Dockerfile", "pb_hooks/toolbox-catalog.json", "pb_hooks/toolbox-package.json", "pb_hooks/toolbox_catalog.pb.js",
        ...migrations.map((m) => `pb_migrations/${m}`), "pb_public/assets/app.css", "pb_public/assets/app.js", "pb_public/index.html",
        "railway.toml", "start.sh",
      ].sort(),
    );
    expect(readFileSync(join(a, "Dockerfile"), "utf8")).toBe(specBlock("**`Dockerfile`**, exactly"));
    expect(readFileSync(join(a, "start.sh"), "utf8")).toBe(specBlock("**`start.sh`**, exactly"));
    expect(statSync(join(a, "start.sh")).mode & 0o111).toBe(0o111);
    expect(readFileSync(join(a, "railway.toml"), "utf8")).toBe(specBlock("**`railway.toml`**, exactly"));
  });

  test("writes the catalog and the receipt with sorted keys and snapshots", async () => {
    const out = join(base, "out", "c");
    await runCli(["package", "--source-root", src, "--out", out, "--ui-build", ui]);
    const manifest = readFileSync(join(src, ".claude-plugin/marketplace.json"));
    const workflows = readFileSync(join(src, "docs/workflows.md"));
    const sourceSnapshot = new Bun.CryptoHasher("sha256").update(manifest).update(new Uint8Array([0])).update(workflows).digest("hex");
    const catalog = {
      plugins: [
        { description: "Delegate work to model-tiered agents", id: "atelier", name: "atelier", version: "0.39.0", workflows: ["release", "start-a-project"] },
        { description: "", id: "empty", name: "empty", version: "", workflows: [] },
        { description: "Diagrams", id: "mermaid", name: "mermaid", version: "1.0.0", workflows: ["start-a-project"] },
      ],
      source_snapshot: sourceSnapshot,
      workflows: [
        { guidance: "Use its contract before release. Ünïcödé ✓", id: "release", name: "Release", plugins: ["atelier"] },
        { guidance: "Use atelier to plan — then draw it → ship.", id: "start-a-project", name: "Start a project", plugins: ["atelier", "mermaid"] },
      ],
    };
    expect(readFileSync(join(out, "pb_hooks/toolbox-catalog.json"), "utf8")).toBe(JSON.stringify(catalog, null, 2) + "\n");
    const snap = (dir: string, files: string[]) => {
      const h = new Bun.CryptoHasher("sha256");
      for (const f of files) h.update(f).update(new Uint8Array([0])).update(readFileSync(join(dir, f))).update(new Uint8Array([0]));
      return h.digest("hex");
    };
    const migrations = readdirSync(join(REPO_ROOT, "pb_migrations")).sort();
    const receipt = {
      migrations,
      migrations_snapshot: snap(join(REPO_ROOT, "pb_migrations"), migrations),
      source_snapshot: sourceSnapshot,
      ui_files: ["assets/app.css", "assets/app.js", "index.html"],
      ui_snapshot: snap(ui, ["assets/app.css", "assets/app.js", "index.html"]),
    };
    expect(readFileSync(join(out, "pb_hooks/toolbox-package.json"), "utf8")).toBe(JSON.stringify(receipt, null, 2) + "\n");
  });

  test("refuses an existing --out or one inside --source-root", async () => {
    const existing = join(base, "exists");
    mkdirSync(existing);
    const r = await runCli(["package", "--source-root", src, "--out", existing, "--ui-build", ui]);
    expect([r.code, r.stderr]).toEqual([1, `evals package: ${existing} already exists\n`]);
    const inside = join(src, "deep", "pkg");
    const r2 = await runCli(["package", "--source-root", src, "--out", inside, "--ui-build", ui]);
    expect(r2.code).toBe(1);
    expect(r2.stderr).toContain("is inside --source-root");
    expect(existsSync(join(src, "deep"))).toBe(false);
  });

  const uiCases: [string, (dir: string) => void, string][] = [
    ["source map", (d) => writeUi(d, { "assets/app.js.map": "{}" }), "contains a source map"],
    ["env file", (d) => writeUi(d, { ".env.local": "X=1" }), "contains an environment file"],
    ["node_modules", (d) => writeUi(d, { "node_modules/x.js": "" }), "contains a forbidden path"],
    ["private dir", (d) => writeUi(d, { "private-notes/x.txt": "" }), "contains a forbidden path"],
    ["symlink", (d) => {
      writeUi(d);
      symlinkSync("/etc/hosts", join(d, "assets/hosts"));
    }, "contains a symlink"],
    ["external script", (d) => writeUi(d, {}, '<script type="module" src="https://cdn.example/app.js"></script>'), "not a relative or root path"],
    ["protocol-relative stylesheet", (d) => writeUi(d, {}, '<link rel="stylesheet" href="//cdn.example/a.css">'), "not a relative or root path"],
    ["parent path", (d) => writeUi(d, {}, '<script type="module" src="../assets/app.js"></script>'), "not a relative or root path"],
    ["missing asset", (d) => writeUi(d, {}, '<script type="module" src="./assets/nope.js"></script>'), "not a file of the build"],
  ];
  for (const [name, make, message] of uiCases) {
    test(`refuses a UI build with a ${name}`, async () => {
      const dir = join(base, `ui-${name.replace(/\W+/g, "-")}`);
      make(dir);
      const out = join(base, "refused", name.replace(/\W+/g, "-"), "pkg");
      const r = await runCli(["package", "--source-root", src, "--out", out, "--ui-build", dir]);
      expect(r.code).toBe(1);
      expect(r.stderr).toContain(message);
      expect(existsSync(join(base, "refused"))).toBe(false);
    });
  }

  test("refuses a missing UI build with the build hint", async () => {
    const r = await runCli(["package", "--source-root", src, "--out", join(base, "x"), "--ui-build", join(base, "no-ui")]);
    expect([r.code, r.stderr]).toEqual([1, `evals package: no UI build at ${join(base, "no-ui")}; run bun run build:ui\n`]);
  });

  const table = (rows: string[], header = "| Stage | Current marketplace plugin(s) | Choose them when |", sep = "| --- | :---: | ---: |") =>
    `# W\n\n### Choose a workflow\n\n${header}\n${sep}\n${rows.join("\n")}\n\n## Next\n`;
  const link = (id: string) => `[${id}](../plugins/${id}/README.md)`;
  const catalogCases: [string, string, string][] = [
    ["a wrong header", table([`| A | ${link("atelier")} | g |`], "| Stage | Plugins | Choose them when |"), "header cells must be"],
    ["a bad separator", table([`| A | ${link("atelier")} | g |`], undefined, "| --- | x | --- |"), "invalid separator row"],
    ["a short row", table([`| A | ${link("atelier")} |`]), "must have exactly 3 non-empty cells"],
    ["an empty cell", table([`| A | ${link("atelier")} |  |`]), "must have exactly 3 non-empty cells"],
    ["a mislabelled link", table([`| A | [Atelier](../plugins/atelier/README.md) | g |`]), "must read [<id>](../plugins/<id>/README.md)"],
    ["an unknown plugin", table([`| A | ${link("ghost")} | g |`]), "ghost is not a marketplace plugin"],
    ["no link", table(["| A | atelier | g |"]), "no plugin link"],
    ["an empty id", table([`| !!! | ${link("atelier")} | g |`]), "gives an empty workflow id"],
    ["disagreeing rows", table([`| Ship it | ${link("atelier")} | g |`, `| ship-it | ${link("mermaid")} | g |`]), "disagrees with an earlier row"],
    ["no table", "## Choose a workflow\n\nNothing here.\n", "needs a header row"],
  ];
  for (const [name, md, message] of catalogCases) {
    test(`refuses a workflows table with ${name}`, async () => {
      const root = join(base, `src-${name.replace(/\W+/g, "-")}`);
      mkdirSync(root);
      writeSyntheticTree(root);
      writeFileSync(join(root, "docs/workflows.md"), md);
      const r = await runCli(["package", "--source-root", root, "--out", join(base, "never"), "--ui-build", ui]);
      expect(r.code).toBe(1);
      expect(r.stderr).toContain(message);
      expect(existsSync(join(base, "never"))).toBe(false);
    });
  }

  test("accepts a level-2 heading table and identical repeated rows", async () => {
    const root = join(base, "src-ok");
    mkdirSync(root);
    writeSyntheticTree(root);
    writeFileSync(join(root, "docs/workflows.md"), WORKFLOWS_MD.replace("| Release |", "| Release |").concat(""));
    const r = await runCli(["package", "--source-root", root, "--out", join(base, "ok-pkg"), "--ui-build", ui]);
    expect(r.code).toBe(0);
  });

  test("refuses symlinked catalog inputs and duplicate plugin names", async () => {
    const root = join(base, "src-link");
    mkdirSync(root);
    writeSyntheticTree(root);
    rmSync(join(root, "docs"), { recursive: true });
    mkdirSync(join(base, "elsewhere"));
    writeFileSync(join(base, "elsewhere/workflows.md"), WORKFLOWS_MD);
    symlinkSync(join(base, "elsewhere"), join(root, "docs"));
    const r = await runCli(["package", "--source-root", root, "--out", join(base, "never2"), "--ui-build", ui]);
    expect(r.code).toBe(1);
    expect(r.stderr).toContain("docs/workflows.md: docs is a symlink");
    const dup = join(base, "src-dup");
    mkdirSync(dup);
    writeSyntheticTree(dup);
    writeFileSync(join(dup, ".claude-plugin/marketplace.json"), JSON.stringify({ plugins: [{ name: "atelier" }, { name: "atelier" }, { name: "mermaid" }] }));
    const r2 = await runCli(["package", "--source-root", dup, "--out", join(base, "never2"), "--ui-build", ui]);
    expect(r2.stderr).toContain("duplicate plugin name atelier");
  });

  test("packages this repository's UI build", async () => {
    if (!existsSync(join(REPO_ROOT, "ui/dist/index.html"))) return;
    const out = join(base, "real-ui");
    const r = await runCli(["package", "--source-root", src, "--out", out]);
    expect(r.code).toBe(0);
    expect(existsSync(join(out, "pb_public/index.html"))).toBe(true);
    expect(readFileSync(join(out, "pb_public/index.html"), "utf8")).toContain("<title>Toolbox</title>");
  });
});

describe.skipIf(!HAS_POCKETBASE)("the packaged service", () => {
  let base: string;
  let pkg: string;
  let server: PbServer;
  beforeAll(async () => {
    base = mkdtempSync(join(tmpdir(), "evals-pkg-srv-"));
    const src = join(base, "src");
    mkdirSync(src);
    writeSyntheticTree(src);
    pkg = join(base, "pkg");
    const r = await runCli(["package", "--source-root", src, "--out", pkg, "--ui-build", writeUi(join(base, "ui"))]);
    expect(r.code).toBe(0);
    server = await startPocketBase({ migrationsDir: join(pkg, "pb_migrations"), hooksDir: join(pkg, "pb_hooks") });
  });
  afterAll(async () => {
    await server?.stop();
    rmSync(base, { recursive: true, force: true });
  });

  test("serves the catalog to authenticated requests only", async () => {
    const anon = await api(server, "GET", "/api/toolbox/catalog");
    expect(anon.status).toBe(401);
    const token = await server.superuserToken();
    const catalog = JSON.parse(readFileSync(join(pkg, "pb_hooks/toolbox-catalog.json"), "utf8"));
    expect(await api(server, "GET", "/api/toolbox/catalog", undefined, token)).toEqual({ status: 200, body: catalog });
    await api(server, "POST", "/api/collections/users/records", { email: "r@example.test", password: "ReaderPassword123", passwordConfirm: "ReaderPassword123", verified: true }, token);
    const auth = await api(server, "POST", "/api/collections/users/auth-with-password", { identity: "r@example.test", password: "ReaderPassword123" });
    expect(await api(server, "GET", "/api/toolbox/catalog", undefined, auth.body.token)).toEqual({ status: 200, body: catalog });
    expect((await fetch(`${server.url}/toolbox-catalog.json`)).status).not.toBe(200);
  });

  test("start.sh bootstraps the superuser, serves, and keeps an existing superuser on restart", async () => {
    const data = join(base, "data");
    const start = async () => {
      const port = await freePort();
      const proc = Bun.spawn(["/bin/sh", join(pkg, "start.sh")], {
        env: { PATH: process.env.PATH ?? "", PB_DATA_DIR: data, POCKETBASE_BIN: pocketbaseBinary()!, PB_BIND: "127.0.0.1", PORT: String(port), PB_SUPERUSER_EMAIL: "owner@example.test", PB_SUPERUSER_PASSWORD: "OwnerPassword123" },
        stdout: "ignore",
        stderr: "pipe",
      });
      const url = `http://127.0.0.1:${port}`;
      for (let i = 0; i < 200; i++) {
        if (proc.exitCode !== null) break;
        try {
          if ((await fetch(`${url}/api/health`)).ok) break;
        } catch {}
        await Bun.sleep(50);
      }
      return { proc, url };
    };
    for (let round = 0; round < 2; round++) {
      const { proc, url } = await start();
      expect(proc.exitCode).toBeNull();
      const auth = await fetch(`${url}/api/collections/_superusers/auth-with-password`, {
        method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ identity: "owner@example.test", password: "OwnerPassword123" }),
      });
      expect(auth.status).toBe(200);
      expect((await fetch(`${url}/`)).status).toBe(200);
      proc.kill("SIGTERM");
      await proc.exited;
    }
    const missing = Bun.spawn(["/bin/sh", join(pkg, "start.sh")], { env: { PATH: process.env.PATH ?? "", PB_DATA_DIR: data }, stdout: "ignore", stderr: "pipe" });
    expect(await missing.exited).not.toBe(0);
    expect(await new Response(missing.stderr).text()).toContain("PB_SUPERUSER_EMAIL is required");
  });
});
