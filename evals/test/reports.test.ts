import { afterAll, beforeAll, describe, expect, setDefaultTimeout, test } from "bun:test";
import { mkdtempSync, readFileSync, rmSync, writeFileSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { runCli } from "./cli.ts";
import { api, HAS_POCKETBASE, startPocketBase, type PbServer } from "./pb.ts";

// Tests that spawn the CLI or a real PocketBase take seconds.
setDefaultTimeout(60000);

// A small dump: the jobs framework with three jobs in two families, four
// extenders (one retired), coverage rows, curation and relationships.
function fixtures(): Record<string, unknown[]> {
  const fw = { id: "fwjobs000000001", slug: "hsb3-jobs-to-be-done", name: "Jobs" };
  const other = { id: "fwother00000001", slug: "anthropic-agent-skills", name: "Skills" };
  const job = (id: string, slug: string, category: string, sort_order: number) => ({ id, framework: fw.id, slug, name: slug, category, sort_order });
  const jobs = [job("job000000000002", "plan-work", "build-software", 1), job("job000000000001", "orient-codebase", "understand-research", 0), job("job000000000003", "produce-dataviz", "build-software", 2)];
  const ext = (id: string, slug: string, kind: string, retired = false) => ({ id, slug, kind, retired });
  const extenders = [ext("ext000000000001", "mermaid", "skill"), ext("ext000000000002", "handoff", "skill"), ext("ext000000000003", "builder", "agent"), ext("ext000000000004", "old-one", "command", true)];
  const runs = [
    { id: "run000000000001", slug: "m1-coverage-judged", kind: "judged", status: "complete" },
    { id: "run000000000002", slug: "m1-adjudication", kind: "adjudication", status: "complete" },
    { id: "run000000000003", slug: "unused-run", kind: "experiment", status: "planned" },
  ];
  const a = (id: string, extender: string, element: string, verdict: string, assessor = "coverage-v1", framework = fw.id, eval_run = "run000000000001") => ({ id, extender, framework, element, verdict, assessor, eval_run, evidence: "" });
  const assessments = [
    a("as0000000000001", "ext000000000001", "job000000000001", "present"),
    a("as0000000000002", "ext000000000002", "job000000000001", "present"),
    a("as0000000000003", "ext000000000002", "job000000000002", "partial"),
    a("as0000000000004", "ext000000000003", "job000000000003", "absent"),
    a("as0000000000005", "ext000000000004", "job000000000001", "present"),
    a("as0000000000006", "ext000000000001", "el0000000000001", "present", "mechanical-v1", other.id, ""),
    a("as0000000000007", "ext000000000001", "el0000000000002", "absent", "mechanical-v1", other.id, ""),
    a("as0000000000008", "ext000000000001", "el0000000000003", "not-applicable", "judged-v1", other.id, "run000000000001"),
  ];
  const job_coverage = [
    { id: "jc0000000000001", job: "job000000000001", status: "covered", disposition: "author", source: "src000000000001", rationale: "", eval_run: "run000000000002" },
    { id: "jc0000000000003", job: "job000000000003", status: "partial", disposition: "", source: "", rationale: "needs\ncharts | soon", eval_run: "run000000000002" },
  ];
  const r = (id: string, a: string, b: string, kind: string, evidence = "", eval_run = "run000000000002") => ({ id, extender_a: a, extender_b: b, kind, job: "", evidence, eval_run, assessor: "adjudication-v1" });
  const relationships = [
    r("rel000000000001", "ext000000000002", "ext000000000001", "duplicative", "same | job"),
    r("rel000000000002", "ext000000000001", "ext000000000003", "feeds-into", "hands off"),
    r("rel000000000003", "ext000000000001", "ext000000000002", "precedes", "RESOLVED: order"),
    r("rel000000000004", "ext000000000003", "ext000000000002", "complementary"),
    r("rel000000000005", "ext000000000004", "ext000000000001", "conflicting", "retired endpoint"),
    r("rel000000000006", "ext000000000003", "ext000000000001", "conflicting", "clash\nhere"),
  ];
  return {
    frameworks: [fw, other],
    framework_elements: jobs,
    extenders,
    sources: [{ id: "src000000000001", slug: "anthropic" }],
    job_coverage,
    relationships,
    assessments,
    eval_runs: runs,
  };
}

function writeFixtures(dir: string, data: Record<string, unknown[]>): void {
  mkdirSync(dir, { recursive: true });
  for (const [name, rows] of Object.entries(data)) writeFileSync(join(dir, `${name}.json`), JSON.stringify(rows));
}

const SCOPE =
  "Retired units excluded: **1**. Suppressed rows: **1 assessments**, **1 relationships**. Counts cover all fetched rows, before section-specific filtering. Assessments and relationships referencing retired or missing extenders are excluded; each relationship counts once even if both endpoints are excluded. Stored history is retained; eval-run linked-row counts reflect this active projection.";

describe("report from fixtures", () => {
  let dir: string;
  beforeAll(() => {
    dir = mkdtempSync(join(tmpdir(), "evals-report-"));
    writeFixtures(join(dir, "fx"), fixtures());
  });
  afterAll(() => rmSync(dir, { recursive: true, force: true }));

  test("renders both files exactly", async () => {
    const out = join(dir, "out", "nested");
    const r = await runCli(["report", "--out", out, "--fixtures", join(dir, "fx")]);
    expect(r.stderr).toBe("");
    expect(r.code).toBe(0);
    expect(r.stdout).toBe(
      `wrote ${join(out, "coverage-matrix.md")}: 3 jobs (0 gap, 1 partial), 5 relationships\nwrote ${join(out, "analysis.md")}: 3 extenders, 3 eval_runs\n`,
    );
    expect(readFileSync(join(out, "coverage-matrix.md"), "utf8")).toBe(
      [
        "# Extender coverage matrix — jobs-to-be-done",
        "",
        "_Generated by `evals report` — do not hand-edit. Truth lives in the database",
        "(assessor `coverage-v1` assessments + `job_coverage` + `relationships`);",
        "this file is a rendered snapshot for reading and diff review._",
        "",
        "Framework: `hsb3-jobs-to-be-done` (3 jobs, 2 families) x 3 extenders.",
        "Provenance: eval_runs `m1-adjudication`, `m1-coverage-judged`.",
        "",
        SCOPE,
        "",
        "## Matrix",
        "",
        "| Job | Family | Status | Present | Partial | Disposition | Source |",
        "|---|---|---|---|---|---|---|",
        "| `orient-codebase` | understand-research | **covered** | handoff, mermaid | — | author | anthropic |",
        "| `plan-work` | build-software | **?** | — | handoff | ? | — |",
        "| `produce-dataviz` | build-software | **partial** | — | — | ? | — |",
        "",
        "## Gaps and partial coverage",
        "",
        "- **`produce-dataviz`** (partial, disposition ?): needs charts | soon",
        "",
        "## Relationships",
        "",
        "| Kind | Count |",
        "|---|---|",
        "| complementary | 1 |",
        "| conflicting | 1 |",
        "| duplicative | 1 |",
        "| feeds-into | 1 |",
        "| precedes | 1 |",
        "",
        "### Duplicative pairs (M3 coalesce candidates)",
        "",
        "- handoff = mermaid: same | job",
        "",
        "### Conflicting pairs",
        "",
        "- builder x mermaid: clash here",
        "",
        "### Directed hand-off links (composition-planner substrate, EDB-22)",
        "",
        "- mermaid => builder (feeds-into)",
        "- mermaid -> handoff (precedes)",
        "",
      ].join("\n"),
    );
    expect(readFileSync(join(out, "analysis.md"), "utf8")).toBe(
      [
        "# Extender-DB analysis",
        "",
        "_Generated by `evals report` — do not hand-edit. Companion to `coverage-matrix.md`;",
        "covers the DB's other cross-cutting answers: per-extender profiles, duplicative/conflicting/directed relationships, an assessor comparison, and the",
        "eval-runs provenance index._",
        "",
        SCOPE,
        "",
        "## Extender profiles",
        "",
        "| Extender | Kind | Jobs present | Jobs partial | Relationship degree |",
        "|---|---|---|---|---|",
        "| `builder` | agent | 0 | 0 | 3 |",
        "| `handoff` | skill | 1 | 1 | 3 |",
        "| `mermaid` | skill | 1 | 0 | 4 |",
        "",
        "## Duplicative, conflicting, and directed relationships",
        "",
        "_Pairs that need a resolution (`duplicative`/`conflicting`) or carry an ordering",
        "decision (`precedes`/`feeds-into`, the composition-planner substrate, EDB-22)._",
        "`complementary` pairs are informational and excluded — see the kind-count table",
        "in `coverage-matrix.md`.",
        "",
        "| Kind | A | B | Status | Evidence |",
        "|---|---|---|---|---|",
        "| conflicting | `builder` | `mermaid` | open | clash here |",
        "| duplicative | `handoff` | `mermaid` | open | same \\| job |",
        "| feeds-into | `mermaid` | `builder` | open | hands off |",
        "| precedes | `mermaid` | `handoff` | resolved | RESOLVED: order |",
        "",
        "## Assessor comparison",
        "",
        "_Present/partial/absent verdict counts per extender, per assessor. `—` = the",
        "assessor never assessed that extender (not the same as an all-absent triple)._",
        "",
        "| Extender | Kind | mechanical-v1 (P/Pa/Ab) | judged-v1 (P/Pa/Ab) | coverage-v1 (P/Pa/Ab) |",
        "|---|---|---|---|---|",
        "| `builder` | agent | — | — | 0/0/1 |",
        "| `handoff` | skill | — | — | 1/1/0 |",
        "| `mermaid` | skill | 1/0/1 | 0/0/0 | 1/0/0 |",
        "",
        "## Eval-run provenance index",
        "",
        "| Slug | Kind | Status | assessments | job_coverage | relationships | Total |",
        "|---|---|---|---|---|---|---|",
        "| `m1-adjudication` | adjudication | complete | 0 | 2 | 5 | 7 |",
        "| `m1-coverage-judged` | judged | complete | 5 | 0 | 0 | 5 |",
        "| `unused-run` | experiment | planned | 0 | 0 | 0 | 0 |",
        "",
      ].join("\n"),
    );
  });

  test("is deterministic and refuses a missing jobs framework", async () => {
    const a = join(dir, "a");
    const b = join(dir, "b");
    await runCli(["report", "--out", a, "--fixtures", join(dir, "fx")]);
    await runCli(["report", "--out", b, "--fixtures", join(dir, "fx")]);
    for (const f of ["coverage-matrix.md", "analysis.md"]) expect(readFileSync(join(a, f), "utf8")).toBe(readFileSync(join(b, f), "utf8"));
    const data = fixtures();
    data.frameworks = data.frameworks!.filter((f: any) => f.slug !== "hsb3-jobs-to-be-done");
    writeFixtures(join(dir, "nojobs"), data);
    const r = await runCli(["report", "--out", join(dir, "c"), "--fixtures", join(dir, "nojobs")]);
    expect(r.code).toBe(1);
    expect(r.stderr).toBe("evals report: framework hsb3-jobs-to-be-done is missing\n");
  });
});

describe.skipIf(!HAS_POCKETBASE)("report from the database", () => {
  let server: PbServer;
  let dir: string;
  beforeAll(async () => {
    server = await startPocketBase();
    dir = mkdtempSync(join(tmpdir(), "evals-report-db-"));
  });
  afterAll(async () => {
    await server?.stop();
    rmSync(dir, { recursive: true, force: true });
  });

  test("matches the report rendered from dumps of the same records", async () => {
    const token = await server.superuserToken();
    const data = fixtures();
    const order = ["frameworks", "sources", "extenders", "framework_elements", "eval_runs", "assessments", "job_coverage", "relationships"];
    // the dump's element ids for mechanical/judged rows point at elements that do not exist; create them
    data.framework_elements!.push(
      { id: "el0000000000001", framework: "fwother00000001", slug: "e1", name: "e1", category: "", sort_order: 0 },
      { id: "el0000000000002", framework: "fwother00000001", slug: "e2", name: "e2", category: "", sort_order: 1 },
      { id: "el0000000000003", framework: "fwother00000001", slug: "e3", name: "e3", category: "", sort_order: 2 },
    );
    for (const name of order) {
      for (const row of data[name]!) {
        const body: any = { ...(row as object) };
        if (name === "frameworks") body.kind = "principles";
        if (name === "framework_elements") body.element_kind = "job";
        if (name === "sources") body.name = "Anthropic";
        const res = await api(server, "POST", `/api/collections/${name}/records`, body, token);
        expect(res.status, `${name} ${JSON.stringify(res.body)}`).toBe(200);
      }
    }
    const env = { PB_URL: server.url, PB_ADMIN_EMAIL: server.email, PB_ADMIN_PASSWORD: server.password };
    const fromDb = await runCli(["report", "--out", join(dir, "db")], env);
    expect(fromDb.code).toBe(0);
    // dump the same collections as the API returns them
    const dump = join(dir, "dump");
    mkdirSync(dump);
    for (const name of [...order]) {
      const res = await api(server, "GET", `/api/collections/${name}/records?perPage=500`, undefined, token);
      writeFileSync(join(dump, `${name}.json`), JSON.stringify(res.body.items));
    }
    await runCli(["report", "--out", join(dir, "fx"), "--fixtures", dump]);
    for (const f of ["coverage-matrix.md", "analysis.md"]) expect(readFileSync(join(dir, "db", f), "utf8")).toBe(readFileSync(join(dir, "fx", f), "utf8"));
  });
});
