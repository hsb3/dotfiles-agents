// `evals fixture`: a disposable loopback PocketBase built from a fresh package
// and seeded with synthetic records, running until interrupted. It reads no
// credentials from the environment or from files and talks only to its own server.
import { existsSync, mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { buildPackage } from "./packager.ts";
import { buildRun, readLedger } from "./runs.ts";
import { applyPlans, CommandError, connect, diff, type Body, type CollectionPlan, type Connection } from "./store.ts";
import { writeSyntheticTree } from "./synthetic-tree.ts";

export const FIXTURE_ADMIN = { email: "fixture-admin@example.test", password: "FixtureAdminPassword123" };
export const FIXTURE_USER = { email: "fixture-user@example.test", password: "FixtureUserPassword123" };

function pocketbaseBinary(flag: string | undefined): string {
  const bin = flag ?? process.env.PB_BINARY ?? Bun.which("pocketbase");
  if (!bin || !existsSync(bin)) throw new CommandError(`no PocketBase binary${bin ? ` at ${bin}` : " (use --pocketbase, PB_BINARY or PATH)"}`);
  return bin;
}

async function freePort(): Promise<number> {
  const server = Bun.listen({ hostname: "127.0.0.1", port: 0, socket: { data() {} } });
  const port = server.port;
  server.stop(true);
  return port;
}

async function waitHealthy(url: string, proc: Bun.Subprocess, ms: number): Promise<boolean> {
  const deadline = Date.now() + ms;
  while (Date.now() < deadline) {
    if (proc.exitCode !== null) return false;
    try {
      if ((await fetch(`${url}/api/health`, { signal: AbortSignal.timeout(1000) })).ok) return true;
    } catch {
      // not listening yet
    }
    await Bun.sleep(100);
  }
  return false;
}

const PRECONDITIONS = {
  auth_env_present: [],
  campaign: "ui-fixture-campaign",
  cli_version: "0.0.0-fixture",
  grader_model: null,
  harness: "opencode",
  model: "ui-fixture-model",
  network_assumption: "assumed-unavailable",
  self_installs: [],
  timeout: 600,
};

// The 27 synthetic ledger rows: a valid comparison pair, then mixed runs.
export function fixtureLedger(): string {
  const pair = (config: string, passed: boolean, duration: number, cost: number) => ({
    campaign: "ui-fixture-campaign", harness: "opencode", model: "ui-fixture-model", candidate: "ui-fixture-candidate", case: "ui-fixture-case",
    config, trial: 1, kind: "skill", passed, skill_used: config === "with", exit_code: 0, plugin_errors: [], preconditions: PRECONDITIONS,
    num_turns: 3, cost_usd: cost, duration_ms: duration, input_tokens: 100, output_tokens: 50, cache_creation_tokens: 10, cache_read_tokens: 20,
    error: null, grader_model: "ui-fixture-grader", cli_version: "0.0.0-fixture", ts: "2026-01-01T00:00:00",
    checks: [{ id: "fixture-check", passed, evidence: "synthetic" }], grades: [{ id: "fixture-grade", passed, evidence: "synthetic" }], tool_names: ["read"],
  });
  const rows: Record<string, unknown>[] = [pair("baseline", false, 2000, 0.02), pair("with", true, 1500, 0.015)];
  const harnesses = ["claude", "opencode", "codex"];
  const models = ["fixture-model-a", "fixture-model-b", "default"];
  for (let i = 2; i < 27; i++) {
    const harness = harnesses[i % 3]!;
    rows.push({
      campaign: "toolbox-fixture", harness, model: harness === "codex" ? "fixture-model-c" : models[i % 3], candidate: i === 7 ? "fixture-<img src=x onerror=alert(1)>" : `fixture-candidate-${i % 4}`,
      case: `fixture-case-${i}`, config: i % 2 === 0 ? "baseline" : "with", trial: 0, kind: "skill",
      passed: i % 5 === 0 ? null : i % 3 === 0, skill_used: i % 2 === 1, exit_code: i % 11 === 0 ? 1 : 0, plugin_errors: [],
      num_turns: harness === "codex" ? null : i, cost_usd: harness === "codex" ? null : i / 1000, duration_ms: 1000 + i * 37,
      input_tokens: i * 10, output_tokens: i * 5, cache_creation_tokens: null, cache_read_tokens: i,
      error: i % 5 === 0 ? `unsupported: ${harness} cannot host kind=skill` : null, grader_model: null, cli_version: "0.0.0-fixture", ts: "2026-01-02T00:00:00",
      checks: [], grades: [], tool_names: [],
    });
  }
  return rows.map((r) => JSON.stringify(r)).join("\n") + "\n";
}

function plan(collection: string, records: { key: string; body: Body }[]): CollectionPlan {
  return diff(collection, records, [], () => "");
}

export async function seedFixture(conn: Connection): Promise<void> {
  const source = plan("sources", [{ key: "src", body: { slug: "ui-fixture-source", name: "UI fixture source", url: "https://example.test/ui-fixture-source", publisher_kind: "individual", maintenance: "active" } }]);
  const sourceId = source.ids.get("src")!;
  const framework = plan("frameworks", [{ key: "fw", body: { slug: "ui-fixture-framework", name: "UI fixture framework", kind: "job-taxonomy", status: "active" } }]);
  const fwId = framework.ids.get("fw")!;
  const element = plan("framework_elements", [{ key: "job", body: { framework: fwId, slug: "ui-fixture-job", name: "UI fixture job", element_kind: "job", sort_order: 0 } }]);
  const jobId = element.ids.get("job")!;
  const body = "# UI fixture primitive\n";
  const extender = plan("extenders", [
    {
      key: "ext",
      body: {
        slug: "ui-fixture-primitive", name: "UI fixture primitive", kind: "skill", description: "A synthetic primitive for the UI fixture.",
        origin: "authored", source: sourceId, body, entry_file: "SKILL.md", repo_path: "primitives-core/skills/ui-fixture-primitive",
        requires: [], assumes: [], frontmatter: { name: "ui-fixture-primitive" }, file_count: 3, retired: false,
      },
    },
  ]);
  const extId = extender.ids.get("ext")!;
  const file = (relpath: string, role: string, content: string, language: string) => ({
    key: relpath,
    body: { extender: extId, relpath, role, content, is_binary: false, size_bytes: content.length, sha256: new Bun.CryptoHasher("sha256").update(content).digest("hex"), language },
  });
  const files = plan("files", [
    file("README.md", "doc", "# UI fixture primitive\n\nSynthetic reader file.\n", "markdown"),
    file("SKILL.md", "entrypoint", `---\nname: ui-fixture-primitive\n---\n${body}`, "markdown"),
    file("hooks/check.py", "script", "print('fixture')\n", "python"),
  ]);
  const distribution = plan("distributions", [{ key: "dist", body: { slug: "ui-fixture-distribution", kind: "plugin", version: "0.0.0", description: "UI fixture distribution", members: [extId] } }]);
  const evalRun = plan("eval_runs", [{ key: "run", body: { slug: "ui-fixture-evaluation", kind: "judged", status: "running", method: "Synthetic evaluation for the UI fixture.", criteria_text: "Synthetic criteria.", frameworks: [fwId] } }]);
  const runId = evalRun.ids.get("run")!;
  const response = plan("eval_responses", [
    {
      key: "resp",
      body: {
        run: runId, role: "judge-1", agent_type: "fixture-agent", model: "ui-fixture-model", prompt: "Synthetic prompt.", response_text: "Synthetic response.",
        response_json: { verdict: "present" }, extenders: [extId], tokens: 1234, duration_ms: 5678,
        measurement: { version: 1, source: "eval-run-manifest", available: { tokens: true, duration_ms: true }, provenance: { tokens: "manifest", duration_ms: "manifest" } },
      },
    },
  ]);
  const assessment = plan("assessments", [{ key: "a", body: { extender: extId, framework: fwId, element: jobId, eval_run: runId, verdict: "present", score: 1, evidence: "Synthetic evidence.", assessor: "coverage-v1" } }]);
  const coverage = plan("job_coverage", [{ key: "jc", body: { job: jobId, status: "covered", disposition: "author", source: sourceId, rationale: "Synthetic coverage.", eval_run: runId } }]);

  const rows = readLedger(fixtureLedger(), []);
  const runs = plan("runs", rows.map((r) => buildRun(r, { path: null, logPath: null }, null)).map((b) => ({ key: b.key, body: b.body })));
  const run0 = runs.ids.get(rows[0]!.key)!;
  const run1 = runs.ids.get(rows[1]!.key)!;
  const evidence = "fixture protected evidence\n";
  const sha = new Bun.CryptoHasher("sha256").update(evidence).digest("hex");
  const artifact = plan("artifacts", [{ key: sha, body: { run: run0, kind: "tool_output", mime: "text/plain", sha256: sha, byte_size: evidence.length, text_ref: evidence } }]);
  const blobId = artifact.ids.get(sha)!;
  artifact.creates[0]!.files = { blob: new File([evidence], `${sha.slice(0, 12)}.txt`, { type: "text/plain" }) };
  const events = plan(
    "run_events",
    [run0, run1].map((run, i) => ({
      key: `e${i}`,
      body: { run, seq: 1, ts: 1767225600000, vendor: "opencode", role: "tool_call", event_type: "tool_use", tool_name: "read", tool_call_id: "fixture-call", status: "completed", is_error: false, payload: { type: "tool_use", fixture: true }, artifact: blobId },
    })),
  );
  const calls = plan(
    "tool_calls",
    [run0, run1].map((run, i) => ({
      key: `t${i}`,
      body: { run, tool_call_id: "fixture-call", tool_name: "read", input: { filePath: "README.md" }, output: { $artifact: sha }, status: "completed", is_error: false, wallclock_ms: 12, started_ts: 1767225600000, artifact: blobId },
    })),
  );
  await applyPlans(conn, [source, framework, element, extender, files, distribution, evalRun, response, assessment, coverage, runs, artifact, events, calls]);
}

export interface FixtureOptions {
  pocketbase?: string;
  sourceRoot?: string;
}

export async function fixture(o: FixtureOptions): Promise<number> {
  const bin = pocketbaseBinary(o.pocketbase);
  const root = mkdtempSync(join(tmpdir(), "evals-fixture-"));
  let child: Bun.Subprocess | null = null;
  const cleanup = async () => {
    if (child && child.exitCode === null) {
      child.kill("SIGTERM");
      await child.exited;
    }
    rmSync(root, { recursive: true, force: true });
  };
  try {
    let sourceRoot = o.sourceRoot;
    if (sourceRoot === undefined) {
      sourceRoot = join(root, "source");
      mkdirSync(sourceRoot);
      writeSyntheticTree(sourceRoot);
    }
    const pkg = buildPackage({ sourceRoot, out: join(root, "package") });
    const port = await freePort();
    const url = `http://127.0.0.1:${port}`;
    child = Bun.spawn(["/bin/sh", join(pkg, "start.sh")], {
      cwd: pkg,
      env: {
        PATH: process.env.PATH ?? "/usr/bin:/bin",
        PB_DATA_DIR: join(pkg, "pb_data"),
        POCKETBASE_BIN: bin,
        PB_BIND: "127.0.0.1",
        PORT: String(port),
        PB_CORS_ORIGINS: url,
        PB_SUPERUSER_EMAIL: FIXTURE_ADMIN.email,
        PB_SUPERUSER_PASSWORD: FIXTURE_ADMIN.password,
      },
      stdout: "ignore",
      stderr: "ignore",
    });
    if (!(await waitHealthy(url, child, 10000))) throw new CommandError(`PocketBase did not answer ${url}/api/health within 10 s`);
    const conn = await connect({ PB_URL: url, PB_ADMIN_EMAIL: FIXTURE_ADMIN.email, PB_ADMIN_PASSWORD: FIXTURE_ADMIN.password });
    await conn.pb.collection("users").create({ email: FIXTURE_USER.email, password: FIXTURE_USER.password, passwordConfirm: FIXTURE_USER.password, verified: true, name: "Fixture user" });
    await seedFixture(conn);
    console.log([`URL=${url}`, `EMAIL=${FIXTURE_USER.email}`, `PASSWORD=${FIXTURE_USER.password}`, "Fixture runs until Ctrl-C; all data is deleted on exit."].join("\n"));
  } catch (err) {
    await cleanup();
    throw err;
  }
  return await new Promise<number>((done) => {
    let stopping = false;
    const stop = () => {
      if (stopping) return;
      stopping = true;
      void cleanup().then(() => done(0));
    };
    process.on("SIGINT", stop);
    process.on("SIGTERM", stop);
    void child!.exited.then(() => {
      if (stopping) return;
      // The server stopped on its own: clean up and report it.
      stopping = true;
      void cleanup().then(() => {
        console.error("evals fixture: the PocketBase server exited");
        done(1);
      });
    });
  });
}
