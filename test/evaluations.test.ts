import { afterAll, beforeAll, describe, expect, test, setDefaultTimeout } from "bun:test";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { canonicalSha256, parseJson } from "../src/canonical.ts";
import { runCli } from "./cli.ts";
import { api, HAS_POCKETBASE, startPocketBase, type PbServer } from "./pb.ts";
import { writeSyntheticTree } from "./synthetic-tree.ts";

// Tests that spawn the CLI or a real PocketBase take seconds.
setDefaultTimeout(60000);

function writeJson(dir: string, name: string, value: unknown): string {
  const path = join(dir, name);
  mkdirSync(join(path, ".."), { recursive: true });
  writeFileSync(path, typeof value === "string" ? value : JSON.stringify(value, null, 2));
  return path;
}

const verdictFile = (over: Record<string, unknown> = {}) => ({
  assessor: "coverage-v1",
  framework: "hsb3-jobs-to-be-done",
  eval_run: "judged-run",
  fill: "absent",
  extenders: [
    { extender: "mermaid", verdicts: [{ element: "orient-codebase", verdict: "present", evidence: "draws maps" }, { element: "plan-work", verdict: "partial", evidence: "…", score: 0.5 }] },
    { extender: "builder", verdicts: [] },
  ],
  ...over,
});

describe("compare-verdicts (offline)", () => {
  let dir: string;
  beforeAll(() => {
    dir = mkdtempSync(join(tmpdir(), "evals-cmp-"));
  });
  afterAll(() => rmSync(dir, { recursive: true, force: true }));

  test("reports sorted disagreements and agreement, honouring fill", async () => {
    const left = writeJson(dir, "left.json", {
      assessor: "a", framework: "fw", eval_run: "r", fill: "absent",
      extenders: [
        { extender: "x", verdicts: [{ element: "e1", verdict: "present" }, { element: "e2", verdict: "partial" }] },
        { extender: "only-left", verdicts: [{ element: "e1", verdict: "present" }] },
      ],
    });
    const right1 = writeJson(dir, "right1.json", {
      assessor: "b", framework: "fw", eval_run: "r",
      extenders: [{ extender: "x", verdicts: [{ element: "e1", verdict: "present" }, { element: "e3", verdict: "present" }, { element: "e2", verdict: "absent" }] }],
    });
    const right2 = writeJson(dir, "right2.json", {
      assessor: "b", framework: "fw2", eval_run: "r", extenders: [{ extender: "x", verdicts: [{ element: "e9", verdict: "absent" }] }],
    });
    const r = await runCli(["compare-verdicts", "--left", left, "--right", right1, right2]);
    expect(r.code).toBe(0);
    // e1 agrees, e2 differs, e3 left fill=absent vs present: differs; fw2 x only on the right.
    expect(r.stdout).toBe("fw x e2: left=partial right=absent\nfw x e3: left=absent right=present\nverdict agreement: 1/3 (33%)\n");
  });

  test("skips an element a side neither lists nor fills, and rounds half to even", async () => {
    const mk = (name: string, verdicts: [string, string][], fill?: string) =>
      writeJson(dir, name, { assessor: "a", framework: "fw", eval_run: "r", ...(fill ? { fill } : {}), extenders: [{ extender: "x", verdicts: verdicts.map(([element, verdict]) => ({ element, verdict })) }] });
    const left = mk("l2.json", [["a", "present"], ["b", "present"], ["c", "present"], ["d", "present"], ["e", "present"], ["f", "present"], ["g", "present"], ["h", "present"], ["z", "present"]]);
    const right = mk("r2.json", [["a", "present"], ["b", "absent"], ["c", "absent"], ["d", "absent"], ["e", "absent"], ["f", "absent"], ["g", "absent"], ["h", "absent"]]);
    const r = await runCli(["compare-verdicts", "--left", left, "--right", right]);
    expect(r.stdout.trim().split("\n").at(-1)).toBe("verdict agreement: 1/8 (12%)");
  });

  test("no overlap or bad input exits 1", async () => {
    const a = writeJson(dir, "a.json", { assessor: "a", framework: "fw", eval_run: "r", extenders: [{ extender: "x", verdicts: [] }] });
    const b = writeJson(dir, "b.json", { assessor: "a", framework: "fw", eval_run: "r", extenders: [{ extender: "y", verdicts: [] }] });
    const r = await runCli(["compare-verdicts", "--left", a, "--right", b]);
    expect([r.code, r.stderr]).toEqual([1, "evals compare-verdicts: no overlapping extenders\n"]);
    const bad = writeJson(dir, "bad.json", "{nope");
    const r2 = await runCli(["compare-verdicts", "--left", a, "--right", bad]);
    expect(r2.code).toBe(1);
    expect(r2.stderr).toContain("invalid JSON");
  });
});

describe.skipIf(!HAS_POCKETBASE)("evaluation loaders against PocketBase", () => {
  let server: PbServer;
  let env: Record<string, string>;
  let token: string;
  let dir: string;
  let src: string;
  const list = async (collection: string, filter = "") => {
    const q = new URLSearchParams({ perPage: "500", sort: "id" });
    if (filter) q.set("filter", filter);
    return (await api(server, "GET", `/api/collections/${collection}/records?${q}`, undefined, token)).body.items as any[];
  };

  beforeAll(async () => {
    server = await startPocketBase();
    token = await server.superuserToken();
    env = { PB_URL: server.url, PB_ADMIN_EMAIL: server.email, PB_ADMIN_PASSWORD: server.password };
    src = mkdtempSync(join(tmpdir(), "evals-src-"));
    writeSyntheticTree(src);
    const r = await runCli(["ingest", "--source-root", src], env);
    expect(r.code).toBe(0);
    dir = mkdtempSync(join(tmpdir(), "evals-eval-"));
    writeJson(dir, "JUDGING-CRITERIA.md", "Judge carefully.\n");
    writeJson(dir, "prompts/judge-1.md", "Prompt one\n");
    writeJson(dir, "responses/judge-1.txt", "Answer one\n");
    writeJson(dir, "responses/judge-1.json", '{"score": 1.0, "items": [1, 2]}');
    writeJson(dir, "manifest.json", {
      run: { slug: "judged-run", kind: "judged", method: "how", criteria_file: "JUDGING-CRITERIA.md", frameworks: ["hsb3-jobs-to-be-done"], notes: "" },
      responses: [
        { role: "judge-1", agent_type: "foreman-kit:scout", model: "sonnet", prompt_file: "prompts/judge-1.md", response_text_file: "responses/judge-1.txt", response_json_file: "responses/judge-1.json", extenders: ["mermaid", "builder"], tokens: 65840, duration_ms: 174422 },
        { role: "judge-2", prompt: "inline prompt", extenders: [] },
      ],
    });
  });
  afterAll(async () => {
    await server?.stop();
    rmSync(dir, { recursive: true, force: true });
    rmSync(src, { recursive: true, force: true });
  });

  test("load-eval-run writes the run and responses with their measurement", async () => {
    const manifest = join(dir, "manifest.json");
    const parse = await runCli(["load-eval-run", manifest, "--parse-only"]);
    expect(parse.stdout).toBe("[parse-only] planned records (no DB connection):\n  eval_runs: 1\n  eval_responses: 2\n");
    const r = await runCli(["load-eval-run", manifest], env);
    expect(r.stderr).toBe("");
    expect(r.stdout).toBe("applied (create / update / unchanged):\n  eval_runs 1 create / 0 update / 0 unchanged\n  eval_responses 2 create / 0 update / 0 unchanged\n");
    const [run] = await list("eval_runs", 'slug = "judged-run"');
    const [fw] = await list("frameworks", 'slug = "hsb3-jobs-to-be-done"');
    expect([run.kind, run.method, run.criteria_text, run.frameworks, run.status, run.notes]).toEqual(["judged", "how", "Judge carefully.\n", [fw.id], "complete", ""]);
    const responses = await list("eval_responses", `run = "${run.id}"`);
    const one = responses.find((x) => x.role === "judge-1");
    const two = responses.find((x) => x.role === "judge-2");
    const exts = await list("extenders");
    const id = (slug: string) => exts.find((e) => e.slug === slug).id;
    expect([one.agent_type, one.model, one.prompt, one.response_text, one.response_json, one.extenders, one.tokens, one.duration_ms]).toEqual([
      "foreman-kit:scout", "sonnet", "Prompt one\n", "Answer one\n", { score: 1, items: [1, 2] }, [id("mermaid"), id("builder")], 65840, 174422,
    ]);
    const manifestSha = new Bun.CryptoHasher("sha256").update(readFileSync(manifest)).digest("hex");
    const resolved = {
      role: "judge-1", agent_type: "foreman-kit:scout", model: "sonnet", prompt: "Prompt one\n", response_text: "Answer one\n",
      response_json: parseJson('{"score": 1.0, "items": [1, 2]}'), extender_slugs: ["mermaid", "builder"],
      tokens: { value: 65840, available: true }, duration_ms: { value: 174422, available: true },
    };
    expect(one.measurement).toEqual({
      version: 1, source: "eval-run-manifest",
      available: { tokens: true, duration_ms: true },
      provenance: { tokens: "manifest", duration_ms: "manifest" },
      execution: { validity: "unknown", reason: "manifest does not attest execution validity", preconditions: null },
      source_identity: { manifest_file_sha256: manifestSha, resolved_response_sha256: canonicalSha256(resolved), resolved_response_canonicalization: "json-sorted-keys-utf8", revision: { value: null, available: false } },
    });
    expect([two.prompt, two.response_text, two.response_json, two.tokens, two.duration_ms]).toEqual(["inline prompt", "", {}, 0, 0]);
    expect(two.measurement.available).toEqual({ tokens: false, duration_ms: false });
    expect(two.measurement.provenance).toEqual({ tokens: null, duration_ms: null });
    const again = await runCli(["load-eval-run", manifest, "--dry-run"], env);
    expect(again.stdout).toBe("[dry-run] plan (create / update / unchanged):\n  eval_runs 0 create / 0 update / 1 unchanged\n  eval_responses 0 create / 0 update / 2 unchanged\n  no writes made\n");
  });

  test("load-eval-run refuses bad extenders, metrics and NaN response_json", async () => {
    writeJson(dir, "bad/nan.json", '{"x": NaN}');
    const bad = writeJson(dir, "bad/manifest.json", {
      run: { slug: "bad-run", kind: "judged" },
      responses: [
        { role: "r1", extenders: ["nope"], tokens: -1 },
        { role: "r1", duration_ms: true, response_json_file: "nan.json" },
      ],
    });
    const parse = await runCli(["load-eval-run", bad, "--parse-only"]);
    expect(parse.code).toBe(1);
    expect(parse.stderr).toContain("tokens must be a finite non-negative number");
    expect(parse.stderr).toContain("duration_ms must be a finite non-negative number");
    expect(parse.stderr).toContain("duplicate role r1");
    expect(parse.stderr).toContain("response_json holds NaN or Infinity");
    const ok = writeJson(dir, "bad/m2.json", { run: { slug: "bad-run", kind: "judged" }, responses: [{ role: "r1", extenders: ["nope", "mermaid"] }] });
    await runCli(["ingest", "--source-root", src], env);
    const r = await runCli(["load-eval-run", ok], env);
    expect(r.code).toBe(1);
    expect(r.stderr).toContain("nope (no such extender)");
    expect(await list("eval_runs", 'slug = "bad-run"')).toEqual([]);
  });

  test("load-verdicts expands fill, sends score only when given, and converges", async () => {
    const f = writeJson(dir, "verdicts/coverage.json", verdictFile());
    const parse = await runCli(["load-verdicts", f, "--parse-only"]);
    expect(parse.stdout).toBe("[parse-only] planned records (no DB connection):\n  assessments: 48\n");
    const r = await runCli(["load-verdicts", f], env);
    expect(r.stderr).toBe("");
    expect(r.stdout).toContain("  assessments 48 create / 0 update / 0 unchanged");
    const rows = await list("assessments", 'assessor = "coverage-v1"');
    expect(rows.length).toBe(48);
    const els = await list("framework_elements");
    const slug = (id: string) => els.find((e) => e.id === id).slug;
    const [run] = await list("eval_runs", 'slug = "judged-run"');
    const mermaid = (await list("extenders", 'slug = "mermaid"'))[0];
    const m = rows.filter((x) => x.extender === mermaid.id);
    const plan = m.find((x) => slug(x.element) === "plan-work");
    expect([plan.verdict, plan.score, plan.evidence, plan.eval_run]).toEqual(["partial", 0.5, "…", run.id]);
    const filled = m.find((x) => slug(x.element) === "research-question");
    expect([filled.verdict, filled.evidence, filled.score]).toEqual(["absent", "", 0]);
    const again = await runCli(["load-verdicts", f, "--dry-run"], env);
    expect(again.stdout).toContain("  assessments 0 create / 0 update / 48 unchanged");
  });

  test("load-verdicts refuses what the spec refuses", async () => {
    const cases: [Record<string, unknown>, string][] = [
      [{ assessor: "mechanical-v1" }, "assessor mechanical-v1 is refused"],
      [{ eval_run: "no-such-run" }, "unknown eval_run no-such-run"],
      [{ extenders: [{ extender: "ghost", verdicts: [] }] }, "unknown extender ghost (not in DB)"],
      [{ extenders: [{ extender: "mermaid", verdicts: [{ element: "skill-md-entrypoint", verdict: "present" }] }] }, "element skill-md-entrypoint is not in framework hsb3-jobs-to-be-done"],
      [{ extenders: [{ extender: "mermaid", verdicts: [] }, { extender: "mermaid", verdicts: [] }] }, "duplicate extender mermaid"],
      [{ extenders: [{ extender: "mermaid", verdicts: [{ element: "plan-work", verdict: "present" }, { element: "plan-work", verdict: "absent" }] }] }, "duplicate element plan-work for mermaid"],
    ];
    for (const [over, message] of cases) {
      const f = writeJson(dir, "verdicts/bad.json", verdictFile(over));
      const r = await runCli(["load-verdicts", f], env);
      expect(r.code, message).toBe(1);
      expect(r.stderr, message).toContain(message);
    }
    const a = writeJson(dir, "verdicts/a.json", verdictFile({ fill: undefined }));
    const b = writeJson(dir, "verdicts/b.json", verdictFile({ fill: undefined }));
    const twice = await runCli(["load-verdicts", a, b], env);
    expect(twice.stderr).toContain("mermaid orient-codebase is also given by");
    const guard = await runCli(["load-verdicts", a, "--extenders", "mermaid,kata"], env);
    expect(guard.stderr).toContain("--extenders: kata is not in the verdict files");
    expect(guard.stderr).toContain("--extenders: builder is in the verdict files but not listed");
    const complete = await runCli(["load-verdicts", a, "--complete"], env);
    expect(complete.stderr).toContain("--complete: extender context-watermark is not listed");
    const ok = await runCli(["load-verdicts", a, "--extenders", "builder,mermaid", "--dry-run"], env);
    expect(ok.code).toBe(0);
  });

  test("load-eval-run with link_assessor stamps that assessor's rows", async () => {
    const m = writeJson(dir, "adjudication.json", { run: { slug: "adjudication-run", kind: "adjudication" }, responses: [], link_assessor: "coverage-v1" });
    const r = await runCli(["load-eval-run", m], env);
    expect(r.stdout).toContain("  assessments 0 create / 48 update / 0 unchanged");
    const [run] = await list("eval_runs", 'slug = "adjudication-run"');
    const rows = await list("assessments", 'assessor = "coverage-v1"');
    expect(rows.every((x) => x.eval_run === run.id)).toBe(true);
    const mech = await list("assessments", 'assessor = "mechanical-v1"');
    expect(mech.every((x) => x.eval_run === "")).toBe(true);
    const again = await runCli(["load-eval-run", m, "--dry-run"], env);
    expect(again.stdout).toContain("  assessments 0 create / 0 update / 48 unchanged");
  });

  test("load-curation writes only the rows it lists", async () => {
    const [run] = await list("eval_runs", 'slug = "adjudication-run"');
    const els = await list("framework_elements");
    const orient = els.find((e) => e.slug === "orient-codebase");
    const outside = await api(server, "POST", "/api/collections/job_coverage/records", { job: orient.id, status: "covered", rationale: "outside" }, token);
    const f = writeJson(dir, "curation.json", {
      eval_run: "adjudication-run",
      job_coverage: [
        { job: "produce-dataviz", status: "partial", disposition: "author", source: "", rationale: "needs charts" },
        { job: "plan-work", status: "covered", disposition: "vendor", source: "anthropic", rationale: "" },
      ],
      relationships: [
        { extender_a: "prepare-compact", extender_b: "builder", kind: "feeds-into", job: "plan-work", evidence: "hands off", assessor: "adjudication-v1" },
        { extender_a: "mermaid", extender_b: "builder", kind: "complementary", evidence: "" },
      ],
    });
    const r = await runCli(["load-curation", f], env);
    expect(r.stderr).toBe("");
    expect(r.stdout).toBe("applied (create / update / unchanged):\n  job_coverage 2 create / 0 update / 0 unchanged\n  relationships 2 create / 0 update / 0 unchanged\n");
    const cov = await list("job_coverage");
    const dataviz = cov.find((c) => c.job === els.find((e) => e.slug === "produce-dataviz").id);
    expect([dataviz.status, dataviz.disposition, dataviz.source, dataviz.rationale, dataviz.eval_run]).toEqual(["partial", "author", "", "needs charts", run.id]);
    const rels = await list("relationships");
    expect(rels.length).toBe(2);
    expect(rels.find((x) => x.kind === "feeds-into").job).toBe(els.find((e) => e.slug === "plan-work").id);
    const after = (await list("job_coverage", `id = "${outside.body.id}"`))[0];
    expect(after.updated).toBe(outside.body.updated);
    const again = await runCli(["load-curation", f, "--dry-run"], env);
    expect(again.stdout).toContain("  job_coverage 0 create / 0 update / 2 unchanged\n  relationships 0 create / 0 update / 2 unchanged\n");
    const dup = writeJson(dir, "dup.json", { eval_run: "nope", job_coverage: [{ job: "plan-work" }, { job: "plan-work" }] });
    const d = await runCli(["load-curation", dup], env);
    expect(d.code).toBe(1);
    expect(d.stderr).toContain("duplicate job plan-work");
    const missing = writeJson(dir, "missing.json", { eval_run: "nope", job_coverage: [{ job: "plan-work" }] });
    const m = await runCli(["load-curation", missing], env);
    expect(m.stderr).toContain("unknown eval_run nope");
  });
});
