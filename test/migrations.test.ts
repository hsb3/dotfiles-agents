import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import { copyFileSync, mkdtempSync, readdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { appendixA, legacySchema, restBody, type CollectionSpec } from "./appendix-a.ts";
import { api, HAS_POCKETBASE, REPO_ROOT, startPocketBase, type PbServer } from "./pb.ts";

const DEPENDENCY_ORDER = [
  "frameworks", "sources", "extenders", "framework_elements", "files", "distributions",
  "frontmatter_dimensions", "eval_runs", "eval_responses", "assessments", "job_coverage",
  "relationships", "coverage_gaps", "runs", "artifacts", "run_events", "tool_calls",
];
const AUTH = "@request.auth.id != ''";
const SUPER_ONLY = new Set(["frontmatter_dimensions", "relationships", "coverage_gaps"]);

async function collections(server: PbServer): Promise<Record<string, any>> {
  const token = await server.superuserToken();
  const res = await api(server, "GET", "/api/collections?perPage=200", undefined, token);
  expect(res.status).toBe(200);
  const out: Record<string, any> = {};
  for (const c of res.body.items) out[c.name] = c;
  return out;
}

function checkAgainstAppendix(all: Record<string, any>) {
  const byId: Record<string, string> = {};
  for (const c of Object.values(all)) byId[c.id] = c.name;
  for (const spec of appendixA()) {
    const c = all[spec.name];
    expect(c, spec.name).toBeDefined();
    expect(c.type).toBe(spec.type);
    if (spec.type === "view") {
      expect(c.viewQuery).toBe(spec.viewQuery);
      continue;
    }
    const names = c.fields.map((f: any) => f.name);
    expect(names).toEqual(["id", ...spec.fields.map((f) => f.name), "created", "updated"]);
    for (const f of spec.fields) {
      const got = c.fields.find((x: any) => x.name === f.name);
      const where = `${spec.name}.${f.name}`;
      expect(got.type, where).toBe(f.type);
      expect(got.required, where).toBe(f.required);
      if (f.type === "text") expect(got.max, where).toBe(f.max);
      if (f.type === "json") expect(got.maxSize, where).toBe(2000000);
      if (f.type === "number") {
        expect([got.min, got.max, got.onlyInt], where).toEqual([null, null, false]);
      }
      if (f.type === "select") {
        expect(got.values, where).toEqual(f.values);
        expect(got.maxSelect, where).toBe(f.maxSelect);
      }
      if (f.type === "relation") {
        expect(byId[got.collectionId], where).toBe(f.target);
        expect(got.maxSelect, where).toBe(f.maxSelect);
        expect(got.cascadeDelete, where).toBe(f.cascadeDelete);
      }
      if (f.type === "file") {
        expect([got.maxSelect, got.maxSize, got.mimeTypes, got.thumbs, got.protected], where).toEqual([1, 10000000, [], [], true]);
      }
    }
    const created = c.fields.find((x: any) => x.name === "created");
    const updated = c.fields.find((x: any) => x.name === "updated");
    expect([created.type, created.onCreate, created.onUpdate]).toEqual(["autodate", true, false]);
    expect([updated.type, updated.onCreate, updated.onUpdate]).toEqual(["autodate", true, true]);
    expect([...c.indexes].sort()).toEqual([...spec.indexes].sort());
  }
}

function checkRules(all: Record<string, any>) {
  for (const name of DEPENDENCY_ORDER) {
    const c = all[name];
    const read = SUPER_ONLY.has(name) ? null : AUTH;
    expect([c.listRule, c.viewRule], name).toEqual([read, read]);
    if (c.type !== "view") expect([c.createRule, c.updateRule, c.deleteRule], name).toEqual([null, null, null]);
  }
  const users = all.users;
  expect([users.listRule, users.viewRule, users.createRule, users.updateRule, users.deleteRule]).toEqual([
    "id = @request.auth.id", "id = @request.auth.id", null, null, null,
  ]);
}

describe.skipIf(!HAS_POCKETBASE)("migrations on an empty database", () => {
  let server: PbServer;
  beforeAll(async () => {
    server = await startPocketBase();
  });
  afterAll(async () => {
    await server?.stop();
  });

  test("create every collection of Appendix A with its rules and settings", async () => {
    const all = await collections(server);
    checkAgainstAppendix(all);
    checkRules(all);
    const settings = await api(server, "GET", "/api/settings", undefined, await server.superuserToken());
    expect(settings.body.rateLimits.enabled).toBe(true);
    expect(settings.body.rateLimits.rules.map((r: any) => r.label)).toEqual(["*:auth", "*:create", "/api/batch", "/api/"]);
  });

  test("change nothing when they run again on a migrated database", async () => {
    const before = await collections(server);
    const beforeSettings = await api(server, "GET", "/api/settings", undefined, await server.superuserToken());
    // Run the same migration again under a new name, so PocketBase treats it as pending.
    const dir = mkdtempSync(join(tmpdir(), "evals-rerun-"));
    for (const f of readdirSync(join(REPO_ROOT, "pb_migrations"))) copyFileSync(join(REPO_ROOT, "pb_migrations", f), join(dir, f));
    for (const f of readdirSync(join(REPO_ROOT, "pb_migrations")))
      copyFileSync(join(REPO_ROOT, "pb_migrations", f), join(dir, f.replace(/^(\d+)/, (d) => String(Number(d) + 1))));
    await server.restart({ migrationsDir: dir });
    const after = await collections(server);
    const afterSettings = await api(server, "GET", "/api/settings", undefined, await server.superuserToken());
    expect(after).toEqual(before);
    expect(afterSettings.body.rateLimits).toEqual(beforeSettings.body.rateLimits);
    rmSync(dir, { recursive: true, force: true });
  });
});

// One record per base collection of the legacy schema; returns name -> record id.
async function seedLegacy(server: PbServer, token: string): Promise<Record<string, Record<string, unknown>>> {
  const ids: Record<string, string> = {};
  const sent: Record<string, Record<string, unknown>> = {};
  const bodies: Record<string, Record<string, unknown>> = {
    frameworks: { slug: "fw", name: "Framework", kind: "job-taxonomy", applies_to: ["skill", "any"], status: "active" },
    sources: { slug: "src", name: "Source", publishes: ["skill"], publishes_evals: true, rationale: "why" },
    extenders: { slug: "ext", name: "Ext", kind: "skill", requires: ["a"], frontmatter: { name: "ext" }, retired: false, file_count: 2 },
    framework_elements: { slug: "job", name: "Job", element_kind: "job", sort_order: 0, category: "cat" },
    files: { relpath: "SKILL.md", role: "entrypoint", content: "# x", size_bytes: 3 },
    distributions: { slug: "dist", kind: "bundle", version: "1.0.0" },
    frontmatter_dimensions: { key: "name", applies_to: "skill", requirement: "required", observed_count: 1 },
    eval_runs: { slug: "run-1", kind: "judged", status: "complete" },
    eval_responses: { role: "judge-1", tokens: 10, response_json: { ok: true } },
    assessments: { verdict: "present", score: 1, evidence: "e", assessor: "coverage-v1" },
    job_coverage: { status: "gap", disposition: "author", rationale: "missing" },
    relationships: { kind: "precedes", evidence: "x", assessor: "adjudication-v1" },
    runs: { harness: "opencode", candidate: "scout", case: "c1", config: "baseline", trial: 0, passed: true, checks: [] },
    artifacts: { sha256: "a".repeat(64), kind: "tool_output", byte_size: 4 },
    run_events: { seq: 0, vendor: "opencode", role: "system", payload: { type: "x" } },
    tool_calls: { tool_call_id: "call-1", tool_name: "read", input: { path: "x" } },
  };
  const links: Record<string, Record<string, string>> = {
    extenders: { source: "sources" },
    framework_elements: { framework: "frameworks" },
    files: { extender: "extenders" },
    distributions: { members: "extenders" },
    frontmatter_dimensions: { spec_framework: "frameworks" },
    eval_runs: { frameworks: "frameworks" },
    eval_responses: { run: "eval_runs", extenders: "extenders" },
    assessments: { extender: "extenders", framework: "frameworks", element: "framework_elements", eval_run: "eval_runs" },
    job_coverage: { job: "framework_elements", source: "sources", eval_run: "eval_runs" },
    relationships: { extender_a: "extenders", extender_b: "extenders", job: "framework_elements", eval_run: "eval_runs" },
    artifacts: { run: "runs" },
    run_events: { run: "runs", artifact: "artifacts" },
    tool_calls: { run: "runs", artifact: "artifacts" },
  };
  for (const name of DEPENDENCY_ORDER) {
    if (name === "coverage_gaps") continue;
    const body: Record<string, unknown> = { ...bodies[name] };
    for (const [field, target] of Object.entries(links[name] ?? {})) body[field] = ids[target];
    const res = await api(server, "POST", `/api/collections/${name}/records`, body, token);
    expect(res.status, `${name}: ${JSON.stringify(res.body)}`).toBe(200);
    ids[name] = res.body.id;
    sent[name] = { id: res.body.id, ...body };
  }
  return sent;
}

describe.skipIf(!HAS_POCKETBASE)("migrations on a legacy database", () => {
  let server: PbServer;
  beforeAll(async () => {
    server = await startPocketBase({ migrationsDir: null });
  });
  afterAll(async () => {
    await server?.stop();
  });

  test("upgrade it in place, keeping records, field ids and options", async () => {
    const token = await server.superuserToken();
    const legacy = legacySchema();
    const byName: Record<string, CollectionSpec> = {};
    for (const c of legacy) byName[c.name] = c;
    const ids: Record<string, string> = {};
    for (const name of DEPENDENCY_ORDER) {
      const res = await api(server, "POST", "/api/collections", restBody(byName[name]!, ids), token);
      expect(res.status, `${name}: ${JSON.stringify(res.body)}`).toBe(200);
      ids[name] = res.body.id;
    }
    const sent = await seedLegacy(server, token);
    const before = await collections(server);
    expect(before.extenders.fields.some((f: any) => f.name === "assumes")).toBe(false);
    const recordsBefore: Record<string, any> = {};
    for (const name of DEPENDENCY_ORDER) {
      const res = await api(server, "GET", `/api/collections/${name}/records?perPage=10`, undefined, token);
      recordsBefore[name] = res.body.items;
    }
    expect(recordsBefore.coverage_gaps.length).toBe(1);

    await server.restart({ migrationsDir: join(REPO_ROOT, "pb_migrations") });
    const after = await collections(server);
    checkAgainstAppendix(after);
    checkRules(after);

    for (const name of DEPENDENCY_ORDER) {
      expect(after[name].id, name).toBe(before[name].id);
      for (const f of before[name].fields) {
        const same = after[name].fields.find((x: any) => x.name === f.name);
        expect(same.id, `${name}.${f.name}`).toBe(f.id);
        if (f.type === "select") {
          expect(same.values.slice(0, f.values.length)).toEqual(f.values);
        }
        const { values: _bv, ...beforeOpts } = f;
        const { values: _av, ...afterOpts } = same;
        expect(afterOpts, `${name}.${f.name}`).toEqual(beforeOpts);
      }
    }
    expect(after.runs.fields.find((f: any) => f.name === "harness").values).toEqual(["claude", "opencode", "codex"]);
    expect(after.run_events.fields.find((f: any) => f.name === "vendor").values).toEqual(["claude", "opencode", "codex"]);
    const added = after.extenders.fields.filter((f: any) => !before.extenders.fields.some((b: any) => b.name === f.name));
    expect(added.map((f: any) => [f.name, f.type, f.maxSize])).toEqual([["assumes", "json", 2000000]]);

    const token2 = await server.superuserToken();
    for (const name of DEPENDENCY_ORDER) {
      const res = await api(server, "GET", `/api/collections/${name}/records?perPage=10`, undefined, token2);
      const items = res.body.items.map((r: any) => {
        const { assumes: _a, ...rest } = r;
        return rest;
      });
      expect(items, name).toEqual(recordsBefore[name]);
      if (sent[name]) expect(res.body.items[0].id).toBe(sent[name]!.id);
    }
    const settings = await api(server, "GET", "/api/settings", undefined, token2);
    expect(settings.body.rateLimits.enabled).toBe(true);
  });
});

describe.skipIf(!HAS_POCKETBASE)("access rules", () => {
  let server: PbServer;
  let userToken = "";
  let userId = "";
  let otherId = "";
  let artifactId = "";
  let blobName = "";
  beforeAll(async () => {
    server = await startPocketBase();
    const token = await server.superuserToken();
    const u = await api(server, "POST", "/api/collections/users/records",
      { email: "reader@example.test", password: "ReaderPassword123", passwordConfirm: "ReaderPassword123", verified: true }, token);
    userId = u.body.id;
    const o = await api(server, "POST", "/api/collections/users/records",
      { email: "other@example.test", password: "OtherPassword123", passwordConfirm: "OtherPassword123", verified: true }, token);
    otherId = o.body.id;
    const auth = await api(server, "POST", "/api/collections/users/auth-with-password",
      { identity: "reader@example.test", password: "ReaderPassword123" });
    userToken = auth.body.token;
    await api(server, "POST", "/api/collections/frameworks/records", { slug: "fw", name: "FW", kind: "principles" }, token);
    const run = await api(server, "POST", "/api/collections/runs/records", { harness: "codex", candidate: "c", case: "k", trial: 0 }, token);
    expect(run.status).toBe(200);
    const form = new FormData();
    form.set("run", run.body.id);
    form.set("sha256", "b".repeat(64));
    form.set("blob", new File(["secret evidence\n"], "bbbbbbbbbbbb.txt", { type: "text/plain" }));
    const res = await fetch(`${server.url}/api/collections/artifacts/records`, { method: "POST", headers: { authorization: token }, body: form });
    const art = (await res.json()) as any;
    expect(res.status).toBe(200);
    artifactId = art.id;
    blobName = art.blob;
  });
  afterAll(async () => {
    await server?.stop();
  });

  test("anonymous readers see nothing", async () => {
    const list = await api(server, "GET", "/api/collections/frameworks/records");
    expect(list.status).toBe(200);
    expect(list.body.items).toEqual([]);
    const view = await api(server, "GET", `/api/collections/artifacts/records/${artifactId}`);
    expect(view.status).toBe(404);
  });

  test("users read the readable collections but never write", async () => {
    const list = await api(server, "GET", "/api/collections/frameworks/records", undefined, userToken);
    expect(list.body.items.length).toBe(1);
    const id = list.body.items[0].id;
    expect((await api(server, "POST", "/api/collections/frameworks/records", { slug: "x", name: "X", kind: "principles" }, userToken)).status).toBe(403);
    expect((await api(server, "PATCH", `/api/collections/frameworks/records/${id}`, { name: "Y" }, userToken)).status).toBe(403);
    expect((await api(server, "DELETE", `/api/collections/frameworks/records/${id}`, undefined, userToken)).status).toBe(403);
    for (const name of SUPER_ONLY) {
      const res = await api(server, "GET", `/api/collections/${name}/records`, undefined, userToken);
      expect(res.status, name).toBe(403);
    }
  });

  test("a user lists only itself and cannot view another user", async () => {
    const list = await api(server, "GET", "/api/collections/users/records", undefined, userToken);
    expect(list.body.items.map((u: any) => u.id)).toEqual([userId]);
    expect((await api(server, "GET", `/api/collections/users/records/${otherId}`, undefined, userToken)).status).toBe(404);
    expect((await api(server, "POST", "/api/collections/users/records",
      { email: "new@example.test", password: "NewPassword1234", passwordConfirm: "NewPassword1234" })).status).toBe(403);
  });

  test("a protected blob needs a file token", async () => {
    const plain = await fetch(`${server.url}/api/files/artifacts/${artifactId}/${blobName}`);
    expect(plain.status).not.toBe(200);
    const tokenRes = await api(server, "POST", "/api/files/token", undefined, userToken);
    const withToken = await fetch(`${server.url}/api/files/artifacts/${artifactId}/${blobName}?token=${tokenRes.body.token}`);
    expect(withToken.status).toBe(200);
    expect(await withToken.text()).toBe("secret evidence\n");
  });
});
