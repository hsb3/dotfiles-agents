import { afterAll, beforeAll, describe, expect, setDefaultTimeout, test } from "bun:test";
import { copyFileSync, mkdirSync, mkdtempSync, readFileSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { buildRun, execution, linkLogs, readLedger, validPreconditions, type LedgerRow } from "../src/runs.ts";
import { runCli } from "./cli.ts";
import { api, HAS_POCKETBASE, REPO_ROOT, startPocketBase, type PbServer } from "./pb.ts";

// Tests that spawn the CLI or a real PocketBase take seconds.
setDefaultTimeout(60000);

const vector = (name: string) => readFileSync(join(REPO_ROOT, "test/vectors", name), "utf8");
const one = (text: string): LedgerRow => readLedger(text, [])[0]!;

const PRECONDITIONS = {
  auth_env_present: ["ANTHROPIC_API_KEY"], campaign: "c", cli_version: "1.0.0", grader_model: null, harness: "claude",
  model: "m", network_assumption: "assumed-available", self_installs: [], timeout: 600,
};

describe("run measurement (Appendix C.2)", () => {
  test("ledger line 24 with no log and nothing stored", () => {
    const r = one(vector("c1-ledger-line-24.jsonl"));
    const built = buildRun(r, { path: null, logPath: null }, null);
    expect(built.body.measurement).toEqual(JSON.parse(vector("c2-measurement-line-24.json")));
    expect(built.body.era).toBe("na");
    expect(built.body.session_id).toBe("");
    expect(built.body.log_path).toBeUndefined();
    expect(built.body.input_tokens).toBeNull();
  });

  test("ledger line 188 with its log_path file absent", () => {
    const r = one(vector("c1-ledger-line-188.jsonl"));
    const built = buildRun(r, { path: null, logPath: String(r.row.log_path) }, null);
    expect(built.body.measurement).toEqual(JSON.parse(vector("c2-measurement-line-188.json")));
    expect(Object.keys(built.body).sort()).toEqual([
      "cache_creation_tokens", "cache_read_tokens", "campaign", "candidate", "case", "checks", "cli_version", "config", "cost_usd",
      "duration_ms", "era", "exit_code", "grader_model", "grades", "harness", "input_tokens", "kind", "log_path", "measurement",
      "model", "num_turns", "output_tokens", "passed", "session_id", "skill_used", "tool_names", "trial", "ts",
    ]);
    expect([built.body.era, built.body.session_id, built.body.log_path]).toEqual(["na", "", r.row.log_path]);
  });

  test("record_sha256 comes from the ledger lexemes (C.1)", () => {
    expect(one(vector("c1-ledger-line-58.jsonl")).recordSha256).toBe("fa5978f82d55751f1dd3324463cff039ead7fd01d9a9bac1012743454669b593");
  });

  test("execution validity, first matching rule", () => {
    const base = { exit_code: 0, plugin_errors: [], passed: true, error: null, preconditions: PRECONDITIONS };
    const cases: [Record<string, unknown>, string, string][] = [
      [{ exit_code: 2 }, "invalid", "producer exit_code was nonzero"],
      [{ plugin_errors: ["x"] }, "invalid", "producer recorded plugin_errors"],
      [{ passed: null, error: "unsupported: codex cannot host kind=agent" }, "skipped", "explicit unsupported producer row"],
      [{ error: "boom" }, "invalid", "producer recorded error"],
      [{ passed: null }, "unknown", "passed was not an explicit boolean"],
      [{ exit_code: null }, "unknown", "exit_code was not explicitly zero"],
      [{ plugin_errors: undefined }, "unknown", "plugin_errors were not recorded"],
      [{ preconditions: { ...PRECONDITIONS, timeout: -1 } }, "unknown", "preconditions were missing or malformed"],
      [{}, "valid", "producer recorded completed run evidence"],
    ];
    for (const [over, validity, reason] of cases) expect(execution({ ...base, ...over })).toEqual({ validity, reason });
    expect(validPreconditions({ ...PRECONDITIONS, grader_model: "g" })).toBe(true);
    const { grader_model: _g, ...noGrader } = PRECONDITIONS;
    expect(validPreconditions(noGrader)).toBe(false);
    expect(validPreconditions({})).toBe(false);
    expect(validPreconditions({ ...PRECONDITIONS, self_installs: [1] })).toBe(false);
  });

  test("a logless re-run keeps stored session, era, rollup values and the observed log hash", () => {
    const r = one(JSON.stringify({ harness: "opencode", candidate: "c", case: "k", config: "with", trial: 0, model: "m", passed: true, exit_code: 0, cost_usd: null, input_tokens: null }));
    const stored = {
      id: "x", session_id: "ses-1", era: "na", cost_usd: 0.5, input_tokens: 11,
      measurement: {
        available: { cost_usd: true, input_tokens: true }, provenance: { cost_usd: "log-rollup", input_tokens: "log-rollup" },
        source_identity: { log_observation: "observed", log_sha256: "f".repeat(64) },
      },
    };
    const built = buildRun(r, { path: null, logPath: null }, null, stored);
    const m = built.body.measurement as any;
    expect([built.body.session_id, built.body.era, built.body.cost_usd, built.body.input_tokens]).toEqual(["ses-1", "na", 0.5, 11]);
    expect([m.available.cost_usd, m.provenance.cost_usd, m.available.output_tokens]).toEqual([true, "log-rollup", false]);
    expect(m.source_identity).toMatchObject({ log_sha256: "f".repeat(64), log_available: true, log_observation: "observed" });
  });
});

describe("ledger and linkage", () => {
  test("a later row replaces an earlier one; bad lines warn by number", () => {
    const warnings: string[] = [];
    const rows = readLedger(
      ['{"harness":"claude","candidate":"a","case":"k","config":"with","trial":0,"model":"m","passed":false}', "", "[1,2]", "not json",
        '{"harness":"claude","candidate":"a","case":"k","config":"with","trial":0,"model":"m","passed":true}'].join("\n"),
      warnings,
    );
    expect(rows.length).toBe(1);
    expect(rows[0]!.row.passed).toBe(true);
    expect(rows[0]!.key).toBe("|claude|m|a|k|with|0");
    expect(warnings).toEqual(["ledger line 3 skipped: not a JSON object", "ledger line 4 skipped: not a JSON object"]);
  });

  test("explicit claims first, then the earliest unclaimed prefix match", () => {
    const dir = mkdtempSync(join(tmpdir(), "evals-link-"));
    mkdirSync(join(dir, "runs"));
    for (const n of ["claude-a-k-with-0-20260101-000002.log", "claude-a-k-with-0-20260101-000001.log", "claude-a-k-with-0-20260101-000003.log", "opencode-b-k-with-0-20260101-000000.log"]) {
      writeFileSync(join(dir, "runs", n), "");
    }
    const row = (o: Record<string, unknown>) => one(JSON.stringify({ harness: "claude", candidate: "a", case: "k", config: "with", model: "m", ...o }));
    const rows = [
      row({ trial: 0, campaign: "x" }),
      row({ trial: 0, campaign: "y", log_path: "harness/runs/claude-a-k-with-0-20260101-000001.log" }),
      row({ trial: 0, campaign: "z", log_path: "runs/claude-a-k-with-0-20260101-000003.log" }),
      row({ trial: 1 }),
    ];
    const warnings: string[] = [];
    const links = linkLogs(rows, dir, join(dir, "runs"), (_r, w) => warnings.push(w));
    expect(links.get(rows[0]!.key)).toEqual({ path: join(dir, "runs", "claude-a-k-with-0-20260101-000002.log"), logPath: "harness/runs/claude-a-k-with-0-20260101-000002.log" });
    expect(links.get(rows[1]!.key)).toEqual({ path: join(dir, "runs", "claude-a-k-with-0-20260101-000001.log"), logPath: "harness/runs/claude-a-k-with-0-20260101-000001.log" });
    expect(links.get(rows[2]!.key)).toEqual({ path: join(dir, "runs/claude-a-k-with-0-20260101-000003.log"), logPath: "runs/claude-a-k-with-0-20260101-000003.log" });
    expect(links.get(rows[3]!.key)).toEqual({ path: null, logPath: null });
    expect(warnings).toEqual(["no log matches prefix 'claude-a-k-with-1-' (run ingested with empty log fields)"]);
    const w2: string[] = [];
    linkLogs([row({ trial: 0 })], dir, join(dir, "runs"), (_r, w) => w2.push(w));
    expect(w2).toEqual(["ambiguous link for 'claude-a-k-with-0-': 3 candidates, picked earliest 'claude-a-k-with-0-20260101-000001.log'"]);
    rmSync(dir, { recursive: true, force: true });
  });
});

const CODEX_LOG = [
  '# preconditions: {"harness": "codex"}',
  '{"type":"thread.started","thread_id":"01a132ee-ff13-7c01-8170-7d57383f6262"}',
  '{"type":"turn.started"}',
  '{"type":"item.started","item":{"id":"item_0","type":"command_execution","command":"cat SKILL.md","aggregated_output":"","exit_code":null,"status":"in_progress"}}',
  '{"type":"item.completed","item":{"id":"item_0","type":"command_execution","command":"cat SKILL.md","aggregated_output":"name: x","exit_code":0,"status":"completed"}}',
  '{"type":"item.completed","item":{"id":"item_2","type":"agent_message","text":"OK"}}',
  '{"type":"turn.completed","usage":{"input_tokens":12868,"cached_input_tokens":0,"cache_write_input_tokens":12865,"output_tokens":5,"reasoning_output_tokens":0}}',
  "",
].join("\n");

function ledgerRows(): Record<string, unknown>[] {
  const common = { campaign: "weekly", model: "claude-sonnet-4-5", kind: "skill", grader_model: "g", cli_version: "1.0.0", checks: [], grades: [], tool_names: [], ts: "2026-08-17T13:35:52", skill_used: false, error: null, workspace: null, plugin_errors: [] };
  return [
    { ...common, harness: "claude", candidate: "scout", case: "c1", config: "with", trial: 0, passed: true, exit_code: 0, num_turns: 3, cost_usd: 0.01, duration_ms: 1000, input_tokens: 5, output_tokens: 7, cache_creation_tokens: 3, cache_read_tokens: 2, log_path: "runs/claude-scout-c1-with-0-20260817-000000.log", preconditions: { ...PRECONDITIONS, campaign: "weekly" } },
    { ...common, harness: "opencode", candidate: "scout", case: "c2", config: "baseline", trial: 1, passed: false, exit_code: 0, num_turns: 2, cost_usd: null, duration_ms: null, input_tokens: null, output_tokens: null, cache_creation_tokens: null, cache_read_tokens: null },
    { ...common, harness: "codex", candidate: "mermaid", case: "c3", config: "with", trial: 0, passed: true, exit_code: 0, num_turns: null, cost_usd: null, duration_ms: 900, input_tokens: null, output_tokens: null, cache_creation_tokens: null, cache_read_tokens: null, log_path: "harness/runs/codex-mermaid-c3-with-0-20260817-000003.log" },
    { ...common, campaign: "other", harness: "codex", candidate: "scout", case: "c4", config: "with", trial: 0, passed: null, exit_code: null, error: "unsupported: codex cannot host kind=agent" },
  ];
}

function writeHarness(dir: string): string {
  mkdirSync(join(dir, "runs"), { recursive: true });
  copyFileSync(join(REPO_ROOT, "test/vectors/c3-claude.log"), join(dir, "runs/claude-scout-c1-with-0-20260817-000000.log"));
  copyFileSync(join(REPO_ROOT, "test/vectors/c3-opencode.log"), join(dir, "runs/opencode-scout-c2-baseline-1-20260817-000001.log"));
  writeFileSync(join(dir, "runs/opencode-scout-c2-baseline-1-20260817-000002.log"), "");
  writeFileSync(join(dir, "runs/codex-mermaid-c3-with-0-20260817-000003.log"), CODEX_LOG);
  const ledger = join(dir, "results.jsonl");
  writeFileSync(ledger, ledgerRows().map((r) => JSON.stringify(r)).join("\n") + "\n" + vector("c1-ledger-line-24.jsonl"));
  return ledger;
}

describe("load-runs without a database", () => {
  test("--parse-only prints the documented shape", async () => {
    const dir = mkdtempSync(join(tmpdir(), "evals-runs-"));
    const ledger = writeHarness(dir);
    const r = await runCli(["load-runs", "--ledger", ledger, "--parse-only"], { PB_URL: "http://127.0.0.1:1" });
    expect(r.stderr).toBe("");
    expect(r.stdout).toBe(
      [
        "[parse-only] planned records (no DB connection):",
        "  runs:        5",
        "  run_events:  19",
        "  tool_calls:  6",
        "  artifacts:   2 post-dedup (1 screenshot, 1 text)",
        "  runs with log reference: 3/5",
        "  runs with observed log bytes: 3/5",
        "  era split:   legacy=1, post=0, na=2",
        "  warnings (3):",
        "    - ambiguous link for 'opencode-scout-c2-baseline-1-': 2 candidates, picked earliest 'opencode-scout-c2-baseline-1-20260817-000001.log'",
        "    - no log matches prefix 'codex-scout-c4-with-0-' (run ingested with empty log fields)",
        "    - no log matches prefix 'opencode-mermaid-avoid-reserved-node-id-baseline-2-' (run ingested with empty log fields)",
        "",
      ].join("\n"),
    );
    const scoped = await runCli(["load-runs", "--ledger", ledger, "--parse-only", "--campaign", "nope"]);
    expect(scoped.stdout).toBe("no ledger rows in scope; nothing to do\n");
    expect(scoped.code).toBe(0);
    const legacy = await runCli(["load-runs", "--ledger", ledger, "--parse-only", "--campaign", ""]);
    expect(legacy.stdout).toContain("  runs:        1\n");
    rmSync(dir, { recursive: true, force: true });
  });

  test("validation names the row key and field; an unreadable ledger exits 1", async () => {
    const dir = mkdtempSync(join(tmpdir(), "evals-runs-"));
    const ledger = join(dir, "bad.jsonl");
    writeFileSync(ledger, JSON.stringify({ harness: "claude", candidate: "a", case: "k", config: "with", trial: 0, model: "m", passed: "yes", cost_usd: -1, exit_code: 1.5, num_turns: true }) + "\n");
    const r = await runCli(["load-runs", "--ledger", ledger, "--parse-only"]);
    expect(r.code).toBe(1);
    for (const field of ["passed", "cost_usd", "exit_code", "num_turns"]) expect(r.stderr).toContain(`evals load-runs: |claude|m|a|k|with|0: ${field} must be`);
    const missing = await runCli(["load-runs", "--ledger", join(dir, "nope.jsonl"), "--parse-only"]);
    expect(missing.code).toBe(1);
    expect(missing.stderr).toContain("evals load-runs: cannot read ledger");
    rmSync(dir, { recursive: true, force: true });
  });
});

describe.skipIf(!HAS_POCKETBASE)("load-runs against PocketBase", () => {
  let server: PbServer;
  let env: Record<string, string>;
  let token: string;
  let dir: string;
  let ledger: string;
  const list = async (collection: string, filter = "") => {
    const q = new URLSearchParams({ perPage: "500", sort: "id" });
    if (filter) q.set("filter", filter);
    return (await api(server, "GET", `/api/collections/${collection}/records?${q}`, undefined, token)).body.items as any[];
  };
  const runOf = async (harness: string) => (await list("runs", `harness = "${harness}" && campaign = "weekly"`))[0];

  beforeAll(async () => {
    server = await startPocketBase();
    token = await server.superuserToken();
    env = { PB_URL: server.url, PB_ADMIN_EMAIL: server.email, PB_ADMIN_PASSWORD: server.password };
    dir = mkdtempSync(join(tmpdir(), "evals-runs-db-"));
    ledger = writeHarness(dir);
  });
  afterAll(async () => {
    await server?.stop();
    rmSync(dir, { recursive: true, force: true });
  });

  test("loads runs, artifacts, events and tool calls", async () => {
    const dry = await runCli(["load-runs", "--ledger", ledger, "--dry-run"], env);
    expect(dry.stdout).toContain("linkage warnings (3):\n  - ambiguous link for");
    expect(dry.stdout).toContain(
      "[dry-run] plan (create / update / unchanged):\n  runs 5 create / 0 update / 0 unchanged\n  artifacts 2 create / 0 update / 0 unchanged\n  run_events 19 create / 0 update / 0 unchanged\n  tool_calls 6 create / 0 update / 0 unchanged\n  no writes made\n",
    );
    expect(await list("runs")).toEqual([]);
    const r = await runCli(["load-runs", "--ledger", ledger], env);
    expect(r.stderr).toBe("");
    expect(r.stdout).toContain("applied (create / update / unchanged):\n  runs 5 create");

    const claude = await runOf("claude");
    expect([claude.era, claude.session_id, claude.log_path, claude.campaign]).toEqual(["legacy", "sess-1", "runs/claude-scout-c1-with-0-20260817-000000.log", "weekly"]);
    expect(claude.provenance).toEqual({ apiKeySource: "apiKeyHelper", plugins: [], tools: ["Bash", "Read", "Skill"] });
    expect(claude.model_usage).toEqual({ "claude-sonnet-4-5": { costUSD: 0.01 } });
    const logSha = new Bun.CryptoHasher("sha256").update(readFileSync(join(REPO_ROOT, "test/vectors/c3-claude.log"))).digest("hex");
    expect(claude.measurement.source_identity).toMatchObject({ log_sha256: logSha, log_available: true, log_observation: "observed" });
    expect(claude.measurement.execution.validity).toBe("valid");

    const oc = await runOf("opencode");
    expect([oc.era, oc.session_id, oc.log_path, oc.cost_usd, oc.input_tokens, oc.output_tokens, oc.cache_read_tokens, oc.cache_creation_tokens, oc.duration_ms]).toEqual([
      "na", "ses-oc", "harness/runs/opencode-scout-c2-baseline-1-20260817-000001.log", 0.005, 11, 22, 33, 44, 1500,
    ]);
    expect(oc.measurement.provenance).toMatchObject({ cost_usd: "log-rollup", input_tokens: "log-rollup", num_turns: "ledger", passed: "ledger" });
    expect(oc.measurement.available.cost_usd).toBe(true);
    expect(oc.measurement.execution.reason).toBe("preconditions were missing or malformed");

    const codex = await runOf("codex");
    expect([codex.session_id, codex.era, codex.input_tokens, codex.output_tokens, codex.cache_read_tokens, codex.cache_creation_tokens, codex.duration_ms]).toEqual([
      "01a132ee-ff13-7c01-8170-7d57383f6262", "na", 12868, 5, 0, 12865, 900,
    ]);
    expect([codex.measurement.provenance.cost_usd, codex.measurement.available.cost_usd, codex.measurement.provenance.duration_ms]).toEqual([null, false, "ledger"]);
    const skip = (await list("runs", 'case = "c4"'))[0];
    expect(skip.measurement.execution.validity).toBe("skipped");
    expect(skip.measurement.source_identity.log_observation).toBe("absent");
    const legacy = (await list("runs", 'campaign = ""'))[0];
    expect(legacy.measurement).toEqual(JSON.parse(vector("c2-measurement-line-24.json")));

    const artifacts = await list("artifacts");
    expect(artifacts.map((a) => [a.sha256, a.kind, a.mime, a.byte_size, a.run, a.blob.replace(/_[a-z0-9]+(\.\w+)$/, "$1")]).sort()).toEqual([
      ["89206d01a7a5f7f6d904c37e473b8b9c695376f9bada9711cde47b23aff314f9", "write_content", "text/plain", 5001, claude.id, "89206d01a7a5.txt"],
      ["c4c7a80748655c031bc38b16ba41e13650acfe8f0e5b4b1841d3d2f7a9616450", "screenshot", "image/png", 12, claude.id, "c4c7a8074865.png"],
    ]);
    const shot = artifacts.find((a) => a.kind === "screenshot");
    const fileToken = (await api(server, "POST", "/api/files/token", undefined, token)).body.token;
    const blob = await fetch(`${server.url}/api/files/artifacts/${shot.id}/${shot.blob}?token=${fileToken}`);
    expect(new Uint8Array(await blob.arrayBuffer())).toEqual(new Uint8Array([0x89, ...new TextEncoder().encode("PNG-fixture")]));

    const events = await list("run_events", `run = "${claude.id}"`);
    expect(events.map((e) => e.seq).sort((a, b) => a - b)).toEqual([1, 3, 4, 5, 6, 7, 8]);
    const seq4 = events.find((e) => e.seq === 4);
    expect(seq4.artifact).toBe(shot.id);
    expect(seq4.ts).toBe(1784660448339);
    const calls = await list("tool_calls", `run = "${claude.id}"`);
    expect(calls.map((c) => [c.tool_call_id, c.status]).sort()).toEqual([["toolu_1", "ok"], ["toolu_2", "ok"], ["toolu_3", "no_result"]]);
    const ocCalls = await list("tool_calls", `run = "${oc.id}"`);
    expect(ocCalls.find((c) => c.tool_call_id === "c2").output).toEqual([1, 2]);
  });

  test("a re-run plans no writes, and a logless re-run erases no evidence", async () => {
    const again = await runCli(["load-runs", "--ledger", ledger, "--dry-run"], env);
    expect(again.stdout).toContain("  runs 0 create / 0 update / 5 unchanged\n  artifacts 0 create / 0 update / 2 unchanged\n  run_events 0 create / 0 update / 19 unchanged\n  tool_calls 0 create / 0 update / 6 unchanged\n");
    const before = await list("runs");
    renameSync(join(dir, "runs"), join(dir, "runs-away"));
    const logless = await runCli(["load-runs", "--ledger", ledger], env);
    expect(logless.code).toBe(0);
    expect(logless.stdout).toContain("  runs 0 create / 0 update / 5 unchanged\n  artifacts 0 create / 0 update / 0 unchanged\n  run_events 0 create / 0 update / 0 unchanged\n");
    expect(await list("runs")).toEqual(before);
    expect((await list("run_events")).length).toBe(19);
    renameSync(join(dir, "runs-away"), join(dir, "runs"));
  });

  test("a scoped load leaves runs outside the scope untouched", async () => {
    const rows = ledgerRows();
    rows[0]!.passed = false; // changes the claude run (campaign weekly)
    rows[3]!.cli_version = "9.9.9"; // changes the skip row (campaign other)
    writeFileSync(ledger, rows.map((r) => JSON.stringify(r)).join("\n") + "\n" + vector("c1-ledger-line-24.jsonl"));
    const other = (await list("runs", 'campaign = "other"'))[0];
    const r = await runCli(["load-runs", "--ledger", ledger, "--campaign", "weekly", "--candidate", "scout"], env);
    expect(r.stdout).toContain("  runs 0 create / 1 update / 1 unchanged");
    expect((await list("runs", `id = "${other.id}"`))[0].updated).toBe(other.updated);
    expect((await runOf("claude")).passed).toBe(false);
  });
});
