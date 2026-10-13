import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import { mkdtempSync, readdirSync, readFileSync, rmSync, statSync, lstatSync, writeFileSync, unlinkSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { topLevelImports } from "../src/ingest.ts";
import { splitFrontmatter, roleOf } from "../src/checkout.ts";
import { runCli } from "./cli.ts";
import { HAS_POCKETBASE, startPocketBase, api, type PbServer } from "./pb.ts";
import { ROSTER_YAML, writeSyntheticTree } from "./synthetic-tree.ts";

function snapshot(dir: string): string[] {
  const out: string[] = [];
  const walk = (d: string, rel: string) => {
    for (const name of readdirSync(d).sort()) {
      const p = join(d, name);
      const r = rel ? `${rel}/${name}` : name;
      const ls = lstatSync(p);
      if (ls.isSymbolicLink()) out.push(`L ${r}`);
      else if (ls.isDirectory()) walk(p, r);
      else out.push(`F ${r} ${ls.size} ${ls.mtimeMs} ${Bun.hash(readFileSync(p))}`);
    }
  };
  walk(dir, "");
  return out;
}

describe("checkout parsing", () => {
  test("frontmatter keeps YAML types and the body after the closing line", () => {
    const fm = splitFrontmatter("---\nname: x\ntools:\n  - Read\n  - Grep\ndescription: >-\n  a\n  b\n---\nbody\n");
    expect(fm.frontmatter).toEqual({ name: "x", tools: ["Read", "Grep"], description: "a b" });
    expect(fm.body).toBe("body\n");
    expect(splitFrontmatter("no block\n")).toEqual({ frontmatter: {}, body: "no block\n", warning: null });
    const bad = splitFrontmatter("---\nname: [unclosed\n---\nrest");
    expect(bad.frontmatter).toEqual({});
    expect(bad.body).toBe("rest");
    expect(bad.warning).toContain("unparseable");
  });

  test("file roles follow the first matching rule", () => {
    expect(roleOf("SKILL.md", "SKILL.md")).toBe("entrypoint");
    expect(roleOf("references/a.md", "SKILL.md")).toBe("reference");
    expect(roleOf("eval/x.json", "SKILL.md")).toBe("eval");
    expect(roleOf("license.md", "SKILL.md")).toBe("license");
    expect(roleOf("docs/readme.txt", "SKILL.md")).toBe("doc");
    expect(roleOf("x.toml", "SKILL.md")).toBe("config");
    expect(roleOf("run.sh", "SKILL.md")).toBe("other");
  });

  test("top-level imports", () => {
    expect(topLevelImports("import a, b.c as d\nfrom x.y import z\nfrom . import q\nfrom .m import n\n  import nested\nimport e # c\n")).toEqual(["a", "b.c", "x.y", "e"]);
  });
});

describe("ingest without a database", () => {
  test("--parse-only counts records and warns without connecting", async () => {
    const root = mkdtempSync(join(tmpdir(), "evals-src-"));
    writeSyntheticTree(root);
    const r = await runCli(["ingest", "--source-root", root, "--parse-only"], { PB_URL: "http://127.0.0.1:1" });
    expect(r.code).toBe(0);
    expect(r.stdout).toBe(
      [
        "[parse-only] planned records (no DB connection):",
        "  frameworks: 9",
        "  framework_elements: 72",
        "  sources: 10",
        "  extenders: 9",
        "  files: 17",
        "  distributions: 3",
        "  frontmatter_dimensions: 12",
        "  assessments: 30",
        "warnings (2):",
        "  - external pocketbase-best-practices skipped: also a roster entry",
        "  - skill missing-skill: source primitives-core/skills/missing-skill does not exist",
        "",
      ].join("\n"),
    );
    rmSync(root, { recursive: true, force: true });
  });

  test("missing roster, externals or marketplace exits 1", async () => {
    for (const missing of ["primitives-core.yaml", "externals.yaml", ".claude-plugin/marketplace.json"]) {
      const root = mkdtempSync(join(tmpdir(), "evals-src-"));
      writeSyntheticTree(root);
      unlinkSync(join(root, missing));
      const r = await runCli(["ingest", "--source-root", root, "--parse-only"]);
      expect(r.code, missing).toBe(1);
      expect(r.stderr).toContain(`evals ingest: missing ${missing}`);
      rmSync(root, { recursive: true, force: true });
    }
  });

  test("invalid roster entries are all reported", async () => {
    const root = mkdtempSync(join(tmpdir(), "evals-src-"));
    writeSyntheticTree(root);
    writeFileSync(join(root, "primitives-core.yaml"), "primitives:\n  - id: a\n    type: widget\n    source: x\n    origin: authored\n    disposition: qualified\n  - type: skill\n");
    const r = await runCli(["ingest", "--source-root", root, "--parse-only"]);
    expect(r.code).toBe(1);
    expect(r.stderr).toContain("primitives[0] (a): type must be one of");
    expect(r.stderr).toContain("primitives[1]: missing id");
    rmSync(root, { recursive: true, force: true });
  });
});

describe.skipIf(!HAS_POCKETBASE)("ingest against PocketBase", () => {
  let server: PbServer;
  let root: string;
  let env: Record<string, string>;
  let token: string;
  const list = async (collection: string, filter = "") => {
    const q = new URLSearchParams({ perPage: "500", sort: "id" });
    if (filter) q.set("filter", filter);
    const res = await api(server, "GET", `/api/collections/${collection}/records?${q}`, undefined, token);
    return res.body.items as any[];
  };

  beforeAll(async () => {
    server = await startPocketBase();
    token = await server.superuserToken();
    root = mkdtempSync(join(tmpdir(), "evals-src-"));
    writeSyntheticTree(root);
    env = { PB_URL: server.url, PB_ADMIN_EMAIL: server.email, PB_ADMIN_PASSWORD: server.password };
  });
  afterAll(async () => {
    await server?.stop();
    rmSync(root, { recursive: true, force: true });
  });

  test("a dry run plans everything and writes nothing", async () => {
    const r = await runCli(["ingest", "--source-root", root, "--dry-run"], env);
    expect(r.code).toBe(0);
    expect(r.stdout.split("\n").slice(0, 10)).toEqual([
      "[dry-run] plan (create / update / unchanged):",
      "  frameworks 9 create / 0 update / 0 unchanged",
      "  framework_elements 72 create / 0 update / 0 unchanged",
      "  sources 10 create / 0 update / 0 unchanged",
      "  extenders 9 create / 0 update / 0 unchanged / 0 retire",
      "  files 17 create / 0 update / 0 unchanged / 0 delete",
      "  distributions 3 create / 0 update / 0 unchanged",
      "  frontmatter_dimensions 12 create / 0 update / 0 unchanged",
      "  assessments 30 create / 0 update / 0 unchanged",
      "  no writes made",
    ]);
    expect(await list("extenders")).toEqual([]);
  });

  test("projects the synthetic checkout as the spec states, without touching it", async () => {
    const before = snapshot(root);
    const r = await runCli(["ingest", "--source-root", root], env);
    expect(r.stderr).toBe("");
    expect(r.code).toBe(0);
    expect(r.stdout).toContain("applied (create / update / unchanged):\n  frameworks 9 create / 0 update / 0 unchanged\n");
    expect(snapshot(root)).toEqual(before);

    const frameworks = await list("frameworks");
    const fwSlug = new Map(frameworks.map((f) => [f.id, f.slug]));
    const ags = frameworks.find((f) => f.slug === "anthropic-agent-skills");
    expect([ags.name, ags.kind, ags.applies_to, ags.status, ags.source_org]).toEqual(["Anthropic Agent Skills structure", "authoring-spec", ["skill"], "active", "Anthropic"]);
    const elements = await list("framework_elements");
    expect(elements.length).toBe(72);
    const conciseBody = elements.find((e) => e.slug === "concise-body" && fwSlug.get(e.framework) === "anthropic-agent-skills");
    expect(conciseBody.sort_order).toBe(7);
    const sources = await list("sources");
    const anthropic = sources.find((s) => s.slug === "anthropic");
    expect(anthropic.publishes).toEqual(["skill", "plugin", "agent", "command", "hook", "mcp"]);
    expect(anthropic.publishes_evals).toBe(true);

    const extenders = await list("extenders");
    const ext = (slug: string) => extenders.find((e) => e.slug === slug);
    const pick = (e: any, keys: string[]) => Object.fromEntries(keys.map((k) => [k, e[k]]));
    const KEYS = ["slug", "name", "kind", "description", "origin", "upstream", "upstream_ref", "repo_path", "source", "shelf", "disposition", "requires", "assumes", "frontmatter", "body", "entry_file", "file_count", "total_bytes", "word_count", "retired"];
    expect(pick(ext("mermaid"), KEYS)).toEqual({
      slug: "mermaid", name: "mermaid", kind: "skill", description: "Draw diagrams with Mermaid when a picture helps.", origin: "authored",
      upstream: "", upstream_ref: "", repo_path: "primitives-core/skills/mermaid", source: "", shelf: "core", disposition: "qualified",
      requires: [], assumes: [], frontmatter: { name: "mermaid", description: "Draw diagrams with Mermaid when a picture helps.", "allowed-tools": ["Read", "Write"] },
      body: "\n# Mermaid\n\nUse mermaid fences.\n", entry_file: "SKILL.md", file_count: 9,
      total_bytes: ext("mermaid").total_bytes, word_count: 5, retired: false,
    });
    expect(pick(ext("builder"), ["name", "kind", "requires", "assumes", "disposition", "entry_file", "word_count"])).toEqual({
      name: "builder", kind: "agent", requires: ["atelier"], assumes: ["path:_meta/plans", "port:8737"], disposition: "grandfathered-pending-use", entry_file: "builder.md", word_count: 6,
    });
    expect(ext("builder").frontmatter.tools).toEqual(["Read", "Edit"]);
    expect(pick(ext("context-watermark"), ["name", "description", "frontmatter", "body", "entry_file", "file_count"])).toEqual({
      name: "context-watermark", description: "Warns when the context window fills up.", frontmatter: {}, body: "", entry_file: "hook.py", file_count: 4,
    });
    expect(pick(ext("carbon-design-server"), ["kind", "requires", "frontmatter", "body", "entry_file"])).toEqual({
      kind: "mcp", requires: ["hosted-mcp"], frontmatter: {}, body: "", entry_file: "carbon-design.json",
    });
    expect(pick(ext("pocketbase-best-practices"), ["name", "origin", "upstream", "upstream_ref", "description"])).toEqual({
      name: "pocketbase-best-practices", origin: "vendored", upstream: "https://github.com/greendesertsnow/pocketbase-skills", upstream_ref: "c573263e84a2066d0564f428dd8160e74fc54226", description: "",
    });
    expect(pick(ext("missing-skill"), ["file_count", "entry_file", "total_bytes"])).toEqual({ file_count: 0, entry_file: "", total_bytes: 0 });
    expect(pick(ext("skill-creator"), KEYS)).toEqual({
      slug: "skill-creator", name: "skill-creator", kind: "skill", description: "Anthropic's skill authoring skill.", origin: "external",
      upstream: "https://github.com/anthropics/skills", upstream_ref: "0123456789abcdef0123456789abcdef01234567", repo_path: "", source: anthropic.id, shelf: "", disposition: "",
      requires: [], assumes: [], frontmatter: {}, body: "", entry_file: "", file_count: 0, total_bytes: 0, word_count: 0, retired: false,
    });
    expect(ext("kata").source).toBe("");
    expect(ext("kata").kind).toBe("plugin");

    const files = await list("files", `extender = "${ext("mermaid").id}"`);
    const byPath = Object.fromEntries(files.map((f) => [f.relpath, f]));
    expect(ext("mermaid").total_bytes).toBe(files.reduce((n, f) => n + f.size_bytes, 0));
    expect(Object.keys(byPath).sort()).toEqual(["LICENSE", "SKILL.md", "assets/logo.png", "evals/cases.yaml", "linked.md", "notes.txt", "references/deep/flowchart.md", "references/syntax.md", "scripts/render.py"]);
    expect(pick(byPath["assets/logo.png"], ["role", "is_binary", "content", "size_bytes", "language"])).toEqual({ role: "asset", is_binary: true, content: "", size_bytes: 8, language: "" });
    expect(byPath["SKILL.md"].sha256).toBe(new Bun.CryptoHasher("sha256").update(readFileSync(join(root, "primitives-core/skills/mermaid/SKILL.md"))).digest("hex"));
    expect(pick(byPath["linked.md"], ["role", "content"])).toEqual({ role: "doc", content: "linked file\n" });
    expect(byPath["LICENSE"].role).toBe("license");
    expect(byPath["evals/cases.yaml"].role).toBe("eval");
    expect(byPath["scripts/render.py"].language).toBe("python");

    const dists = await list("distributions");
    const dist = (slug: string) => dists.find((d) => d.slug === slug);
    const slugs = (ids: string[]) => ids.map((id) => extenders.find((e) => e.id === id).slug);
    expect([dist("atelier").kind, dist("atelier").version, slugs(dist("atelier").members)]).toEqual(["bundle", "0.39.0", ["builder", "context-watermark", "prepare-compact", "carbon-design-server"]]);
    expect([dist("mermaid").kind, slugs(dist("mermaid").members)]).toEqual(["standalone", ["mermaid"]]);
    expect([dist("empty").kind, dist("empty").version, dist("empty").description, dist("empty").members]).toEqual(["bundle", "", "", []]);

    const dims = await list("frontmatter_dimensions");
    const dim = (key: string, appliesTo: string) => dims.find((d) => d.key === key && d.applies_to === appliesTo);
    expect(pick(dim("name", "skill"), ["requirement", "observed_count"])).toEqual({ requirement: "required", observed_count: 1 });
    expect(fwSlug.get(dim("name", "skill").spec_framework)).toBe("anthropic-agent-skills");
    expect(pick(dim("license", "skill"), ["requirement", "observed_count"])).toEqual({ requirement: "optional", observed_count: 0 });
    expect(pick(dim("color", "agent"), ["requirement", "observed_count"])).toEqual({ requirement: "harness", observed_count: 1 });
    expect(pick(dim("description", "command"), ["requirement", "description", "spec_framework", "observed_count"])).toEqual({ requirement: "custom", description: "", spec_framework: "", observed_count: 1 });

    const assessments = await list("assessments");
    const elSlug = new Map(elements.map((e) => [e.id, e.slug]));
    const verdicts = (slug: string) =>
      Object.fromEntries(assessments.filter((a) => a.extender === ext(slug).id).map((a) => [elSlug.get(a.element), `${a.verdict} | ${a.evidence}`]));
    expect(assessments.every((a) => a.assessor === "mechanical-v1" && a.eval_run === "")).toBe(true);
    expect(verdicts("mermaid")).toEqual({
      "skill-md-entrypoint": "present | SKILL.md at folder root",
      "frontmatter-name": 'present | name="mermaid" (7 chars)',
      "frontmatter-description": "present | 48 chars",
      "concise-body": "present | 12 lines",
      "references-dir": "present | 2 file(s)",
      "scripts-dir": "present | 1 file(s)",
      "assets-dir": "present | 1 file(s)",
    });
    expect(verdicts("builder")).toEqual({
      "frontmatter-name": 'present | name="builder"',
      "frontmatter-description": 'present | description="Builds one slice."',
      "tools-allowlist": 'present | tools=["Read","Edit"]',
      "model-tier": 'present | model="sonnet"',
      "system-prompt-body": "present | 6 words",
    });
    expect(verdicts("context-watermark")).toEqual({
      "hook-py-entrypoint": "present | hook.py in the hook's directory",
      "python-only-handler": 'absent | legacy .sh handler(s): ["legacy.sh"]',
      "stdlib-only-imports": 'partial | non-stdlib imports: ["requests","yaml.loader"]',
      "config-present": "present | 1 file(s)",
    });
    expect(verdicts("missing-skill")["skill-md-entrypoint"]).toBe("absent | no SKILL.md found");
    expect(verdicts("missing-skill")["concise-body"]).toBe("present | 0 lines");
    expect(verdicts("prepare-compact")).toEqual({});
  });

  test("a re-run on the unchanged tree plans no writes", async () => {
    const r = await runCli(["ingest", "--source-root", root, "--dry-run"], env);
    expect(r.code).toBe(0);
    for (const line of r.stdout.split("\n").slice(1, 9)) expect(line).toMatch(/ 0 create \/ 0 update \/ \d+ unchanged( \/ 0 (delete|retire))?$/);
  });

  test("another assessor's rows and a stamped eval_run survive ingest", async () => {
    const [ext] = await list("extenders", 'slug = "mermaid"');
    const [fw] = await list("frameworks", 'slug = "hsb3-jobs-to-be-done"');
    const run = await api(server, "POST", "/api/collections/eval_runs/records", { slug: "run-x", kind: "judged" }, token);
    const other = await api(server, "POST", "/api/collections/assessments/records", { extender: ext.id, framework: fw.id, verdict: "present", assessor: "coverage-v1" }, token);
    const [mech] = await list("assessments", `assessor = "mechanical-v1" && extender = "${ext.id}"`);
    await api(server, "PATCH", `/api/collections/assessments/records/${mech.id}`, { eval_run: run.body.id }, token);
    const r = await runCli(["ingest", "--source-root", root], env);
    expect(r.stdout).toContain("  assessments 0 create / 0 update / 30 unchanged");
    const after = (await list("assessments", `id = "${mech.id}"`))[0];
    expect(after.eval_run).toBe(run.body.id);
    expect((await list("assessments", `id = "${other.body.id}"`))[0].assessor).toBe("coverage-v1");
  });

  test("retires a vanished extender, deletes a vanished file, and un-retires on return", async () => {
    writeFileSync(join(root, "primitives-core.yaml"), ROSTER_YAML.replace(/  - id: prepare-compact\n(    .*\n)+?(?=  - id:)/, ""));
    unlinkSync(join(root, "primitives-core/skills/mermaid/references/syntax.md"));
    const dry = await runCli(["ingest", "--source-root", root, "--dry-run"], env);
    expect(dry.stdout).toContain("  extenders 0 create / 1 update / 7 unchanged / 1 retire");
    expect(dry.stdout).toContain("  files 0 create / 0 update / 15 unchanged / 1 delete");
    expect(dry.stdout).toContain("  no writes made\n  to retire command/prepare-compact\n");
    const r = await runCli(["ingest", "--source-root", root], env);
    expect(r.code).toBe(0);
    expect(r.stdout).toContain("\n  retired command/prepare-compact\n");
    const [pc] = await list("extenders", 'slug = "prepare-compact"');
    expect(pc.retired).toBe(true);
    expect((await list("files", `extender = "${pc.id}"`)).length).toBe(1); // a retired extender keeps its files
    const again = await runCli(["ingest", "--source-root", root, "--dry-run"], env);
    expect(again.stdout).toContain("/ 0 retire");
    expect(again.stdout).not.toContain("to retire");

    writeFileSync(join(root, "primitives-core.yaml"), ROSTER_YAML);
    const back = await runCli(["ingest", "--source-root", root], env);
    expect(back.stdout).toContain("  extenders 0 create / 1 update / 8 unchanged / 0 retire");
    expect((await list("extenders", 'slug = "prepare-compact"'))[0].retired).toBe(false);
    expect(statSync(join(root, "primitives-core.yaml")).isFile()).toBe(true);
  });
});
