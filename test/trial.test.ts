import { afterEach, beforeEach, expect, test } from "bun:test";
import { existsSync, mkdirSync, readdirSync, readFileSync, realpathSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { loadCandidate } from "../src/candidate.ts";
import type { Case } from "../src/cases.ts";
import { readRows } from "../src/ledger.ts";
import { runTrial, selfInstalls, type TrialSpec } from "../src/trial.ts";
import { installStub, sandbox, stubCalls, type StubRule } from "./helpers/stubs.ts";

let box: ReturnType<typeof sandbox>;
let tmp: string;
const savedTmp = process.env.TMPDIR;
beforeEach(() => {
  box = sandbox();
  tmp = join(box.root, "tmp");
  mkdirSync(tmp);
  process.env.TMPDIR = tmp;
});
afterEach(() => {
  process.env.TMPDIR = savedTmp;
  box.cleanup();
});

const ROW_KEYS = [
  "cache_creation_tokens", "cache_read_tokens", "campaign", "candidate", "case", "checks", "cli_version", "config", "cost_usd",
  "duration_ms", "error", "exit_code", "grader_model", "grades", "harness", "input_tokens", "kind", "log_path", "model",
  "num_turns", "output_tokens", "passed", "plugin_errors", "preconditions", "skill_used", "tool_names", "trial", "ts", "workspace",
];

function candidateDir(name: string, files: Record<string, string>): string {
  const d = join(box.root, "cands", name);
  for (const [rel, body] of Object.entries(files)) {
    mkdirSync(join(d, rel, ".."), { recursive: true });
    writeFileSync(join(d, rel), body);
  }
  return d;
}

const skill = () => loadCandidate("mermaid", candidateDir("mermaid", { "SKILL.md": "skill" }));
const plugin = () => loadCandidate("demo", candidateDir("demo", { ".claude-plugin/plugin.json": '{"name":"demo-plugin"}' }));

function kase(over: Partial<Case> = {}): Case {
  return { id: "create-file", dir: join(box.root, "case"), prompt: "Create HELLO.txt", assertions: [], fixture: null, check: null, ...over };
}

function spec(over: Partial<TrialSpec> = {}): TrialSpec {
  return {
    harness: "claude", model: "claude-sonnet-4-5", candidate: skill(), kase: kase(), config: "with", trial: 0, campaign: "c1",
    graderModel: "claude-haiku-4-5-20251001", timeoutSec: 10, keepWorkspaces: false,
    resultsPath: join(box.root, "out", "results.jsonl"), runsDir: join(box.root, "out", "runs"), cliVersion: "2.1.296 (Claude Code)",
    baseEnv: { PATH: box.bin, ANTHROPIC_API_KEY: "sk-a", OPENAI_API_KEY: "sk-o", CLAUDECODE: "1" },
    ...over,
  };
}

const claudeRules = (agent: StubRule): StubRule[] => [
  { has: ["--bare"], stream: "A11-grader-result.json" },
  agent,
];

const PASSING_CHECK: StubRule = { stdout: '[{"id":"hello-file-exists","passed":true,"evidence":"HELLO.txt present"}]' };

test("a passing claude skill trial appends a complete row, logs stdout and deletes its run dir", async () => {
  installStub(box.bin, "claude", claudeRules({ prefix: ["-p"], stream: "A2-claude-skill-trial.jsonl", writeFiles: { "HELLO.txt": "harness-ok" } }));
  installStub(box.bin, "python3", [PASSING_CHECK]);
  const s = spec({ kase: kase({ check: "/case/check.py" }) });
  const row = await runTrial(s);
  expect(Object.keys(row).sort()).toEqual(ROW_KEYS);
  expect(row).toMatchObject({
    campaign: "c1", harness: "claude", model: "claude-sonnet-4-5", candidate: "mermaid", case: "create-file", config: "with", trial: 0,
    kind: "skill", grader_model: null, passed: true, grades: [], skill_used: true, tool_names: ["Read", "Skill", "Edit"],
    plugin_errors: [], exit_code: 0, error: null, cost_usd: 0.19766235, duration_ms: 44168, num_turns: 12, input_tokens: 36,
    output_tokens: 1964, cache_read_tokens: 105942, cache_creation_tokens: 36157, workspace: null, cli_version: "2.1.296 (Claude Code)",
  });
  expect(row.checks).toEqual([{ id: "hello-file-exists", passed: true, evidence: "HELLO.txt present" }]);
  expect(row.ts).toMatch(/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d$/);
  expect(row.preconditions).toEqual({
    auth_env_present: ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"], campaign: "c1", cli_version: "2.1.296 (Claude Code)",
    grader_model: "claude-haiku-4-5-20251001", harness: "claude", model: "claude-sonnet-4-5", network_assumption: "assumed-available",
    self_installs: [], timeout: 10,
  });
  // The log: name pattern, header line, then raw stdout; log_path relative to the ledger dir.
  expect(row.log_path).toMatch(/^runs\/claude-mermaid-create-file-with-0-\d{8}-\d{6}-[0-9a-f]{32}\.log$/);
  const log = readFileSync(join(box.root, "out", row.log_path!), "utf8");
  const stream = readFileSync(join(import.meta.dir, "fixtures/streams/A2-claude-skill-trial.jsonl"), "utf8");
  expect(log).toBe(`# preconditions: {"auth_env_present": ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"], "campaign": "c1", "cli_version": "2.1.296 (Claude Code)", "grader_model": "claude-haiku-4-5-20251001", "harness": "claude", "model": "claude-sonnet-4-5", "network_assumption": "assumed-available", "self_installs": [], "timeout": 10}\n${stream}`);
  // The ledger holds exactly this row; the run dir is gone.
  expect(readRows(s.resultsPath)).toEqual([JSON.parse(JSON.stringify(row))]);
  expect(readdirSync(tmp)).toEqual([]);
  // The agent ran in ws/ under a per-run home, injected, scrubbed, never --bare.
  const [call] = stubCalls(box.bin, "claude");
  expect(call!.cwd).toMatch(/\/harness-claude-mermaid-create-file-with-0-[^/]+\/ws$/);
  expect(call!.cwd.startsWith(realpathSync(tmp))).toBe(true);
  expect(call!.env.HOME).toBe(call!.cwd.replace(/ws$/, "home"));
  expect(call!.env.CLAUDECODE).toBeUndefined();
  expect(call!.argv).toContain("--plugin-dir");
  expect(call!.argv).not.toContain("--bare");
  const [check] = stubCalls(box.bin, "python3");
  expect(check!.argv).toEqual(["/case/check.py"]);
  expect(check!.cwd).toBe(call!.cwd);
});

test("baseline injects nothing; the fixture is copied into ws/", async () => {
  installStub(box.bin, "claude", claudeRules({ prefix: ["-p"], stream: "A2-claude-skill-trial.jsonl" }));
  const fixture = join(box.root, "fixture");
  mkdirSync(join(fixture, "src"), { recursive: true });
  writeFileSync(join(fixture, "src", "pipeline.py"), "x");
  installStub(box.bin, "python3", [{ stdout: "[]" }]);
  const row = await runTrial(spec({ config: "baseline", kase: kase({ fixture, check: "/c.py" }), keepWorkspaces: true }));
  expect(row.passed).toBe(true);
  const [call] = stubCalls(box.bin, "claude");
  expect(call!.argv).not.toContain("--plugin-dir");
  expect(row.workspace).toBe(call!.cwd);
  expect(readFileSync(join(row.workspace!, "src", "pipeline.py"), "utf8")).toBe("x");
});

test("a plugin error fails a with trial but not a baseline one; a failure keeps the run dir", async () => {
  installStub(box.bin, "claude", claudeRules({ prefix: ["-p"], stream: "A3-claude-plugin-error.jsonl" }));
  const w = await runTrial(spec());
  expect(w).toMatchObject({ passed: false, plugin_errors: [{ plugin: "eval-x", message: "boom" }], exit_code: 0, error: null });
  expect(w.workspace).toMatch(/\/ws$/);
  expect(existsSync(w.workspace!)).toBe(true);
  const b = await runTrial(spec({ config: "baseline", trial: 1 }));
  expect(b).toMatchObject({ passed: true, workspace: null });
});

test("the error field: stderr tail on non-zero exit, else the fold's error", async () => {
  installStub(box.bin, "claude", claudeRules({ prefix: ["-p"], stream: "A1-claude-api-error.jsonl", exit: 1 }));
  const r1 = await runTrial(spec());
  expect(r1).toMatchObject({ passed: false, exit_code: 1, error: "API Error: 400 The requested features are not available for HIPAA-configured organizations: context_management." });
  installStub(box.bin, "claude", claudeRules({ prefix: ["-p"], stream: "A1-claude-api-error.jsonl", stderr: "x".repeat(2500) + "TAIL\n", exit: 1 }));
  const r2 = await runTrial(spec({ trial: 1 }));
  expect(r2.error).toHaveLength(2000);
  expect(r2.error!.endsWith("TAIL")).toBe(true);
  installStub(box.bin, "claude", claudeRules({ prefix: ["-p"], stdout: "", exit: 7 }));
  expect((await runTrial(spec({ trial: 2 }))).error).toBe("exit 7");
});

test("a timeout records exit -1 and keeps the partial log", async () => {
  installStub(box.bin, "claude", claudeRules({ prefix: ["-p"], stdout: '{"type":"system","subtype":"init","plugins":[]}\n', hang: true }));
  const row = await runTrial(spec({ timeoutSec: 1 }));
  expect(row).toMatchObject({ passed: false, exit_code: -1, error: "timeout after 1s" });
  const log = readFileSync(join(box.root, "out", row.log_path!), "utf8");
  expect(log.split("\n")[1]).toBe('{"type":"system","subtype":"init","plugins":[]}');
}, 15000);

test("a missing executable records exit -1 and an empty log", async () => {
  const row = await runTrial(spec({ baseEnv: { PATH: join(box.root, "nothing") } }));
  expect(row).toMatchObject({ passed: false, exit_code: -1, error: "executable not found: claude", grader_model: null });
  const log = readFileSync(join(box.root, "out", row.log_path!), "utf8");
  expect(log.endsWith("}\n")).toBe(true);
  expect(log.split("\n")).toHaveLength(2);
});

test("a harness that cannot host the kind writes a skip row and runs nothing", async () => {
  installStub(box.bin, "opencode", [{ stream: "A4-opencode-captured.jsonl" }]);
  for (const config of ["with", "baseline"] as const) {
    const row = await runTrial(spec({ harness: "opencode", candidate: plugin(), config, cliVersion: "opencode v2.0.25" }));
    expect(Object.keys(row).sort()).toEqual(ROW_KEYS);
    expect(row).toMatchObject({
      passed: null, grader_model: null, checks: [], grades: [], skill_used: false, tool_names: [], plugin_errors: [], exit_code: null,
      error: "unsupported: opencode cannot host kind=plugin", cost_usd: null, duration_ms: null, num_turns: null, input_tokens: null,
      output_tokens: null, cache_read_tokens: null, cache_creation_tokens: null, workspace: null, log_path: null, kind: "plugin",
    });
    expect(row.preconditions.self_installs).toEqual([]);
  }
  expect(stubCalls(box.bin, "opencode")).toEqual([]);
  expect(readdirSync(tmp)).toEqual([]);
});

test("a failed codex plugin install writes an injection-failure row and keeps the run dir", async () => {
  installStub(box.bin, "codex", [
    { prefix: ["plugin", "marketplace", "add"], stream: "A10-codex-marketplace-add.json" },
    { prefix: ["plugin", "add"], stderr: "plugin not found\n", exit: 1 },
  ]);
  const row = await runTrial(spec({ harness: "codex", model: "gpt-6.1-sol", candidate: plugin(), kase: kase({ check: "/c.py", assertions: [{ id: "a1", text: "t" }] }) }));
  expect(row).toMatchObject({
    passed: false, plugin_errors: ["codex plugin install failed: plugin not found"], error: "codex plugin install failed: plugin not found",
    exit_code: 1, grader_model: null, checks: [], grades: [], log_path: null, tool_names: [],
  });
  expect(existsSync(row.workspace!)).toBe(true);
  expect(stubCalls(box.bin, "codex").map((c) => c.argv[1])).toEqual(["marketplace", "add"]);
});

test("cases with assertions are graded by claude even under codex, with wall-clock duration", async () => {
  installStub(box.bin, "codex", [{ prefix: ["exec"], stream: "A8-codex-skill-trial.jsonl" }]);
  installStub(box.bin, "claude", claudeRules({}));
  const row = await runTrial(spec({ harness: "codex", model: "gpt-6.1-sol", kase: kase({ assertions: [{ id: "a1-diagram-covers-all-services", text: "t" }] }) }));
  expect(row).toMatchObject({ passed: true, grader_model: "claude-haiku-4-5-20251001", skill_used: true, cost_usd: null, num_turns: null });
  expect(row.grades[0]!.id).toBe("a1-diagram-covers-all-services");
  expect(typeof row.duration_ms).toBe("number");
  const grader = stubCalls(box.bin, "claude")[0]!;
  expect(grader.argv).toContain("--bare");
  expect(grader.env.HOME).toMatch(/grader-home$/);
});

test("self_installs lists install lines trimmed, cut, deduplicated, sorted and capped", () => {
  const out = ["  npm install left-pad  ", "pip install x", "npm install left-pad", "nothing", `brew install ${"y".repeat(200)}`].join("\n");
  expect(selfInstalls(out)).toEqual([`brew install ${"y".repeat(107)}`, "npm install left-pad", "pip install x"]);
  expect(selfInstalls(Array.from({ length: 30 }, (_, i) => `go install p${String(i).padStart(2, "0")}`).join("\n"))).toHaveLength(20);
});

test("every child gets PWD set to its cwd: agent CLIs, the grader, check.py and the codex plugin install", async () => {
  const elsewhere = join(box.root, "invoked-from");
  mkdirSync(elsewhere);
  const base = { PATH: box.bin, ANTHROPIC_API_KEY: "sk-a", OPENAI_API_KEY: "sk-o", PWD: elsewhere };
  installStub(box.bin, "claude", claudeRules({ prefix: ["-p"], stream: "A2-claude-skill-trial.jsonl" }));
  installStub(box.bin, "opencode", [{ prefix: ["run"], stream: "A4-opencode-captured.jsonl" }]);
  installStub(box.bin, "codex", [{ prefix: ["plugin"], stdout: "{}" }, { prefix: ["exec"], stream: "A7-codex-captured.jsonl" }]);
  installStub(box.bin, "python3", [{ stdout: "[]" }]);
  const graded = kase({ check: "/c.py", assertions: [{ id: "a1-diagram-covers-all-services", text: "t" }] });
  await runTrial(spec({ baseEnv: base, kase: graded }));
  await runTrial(spec({ baseEnv: base, harness: "opencode", kase: graded }));
  await runTrial(spec({ baseEnv: base, harness: "codex", model: "gpt-6.1-sol", candidate: plugin(), kase: graded }));
  const calls = ["claude", "opencode", "codex", "python3"].flatMap((n) => stubCalls(box.bin, n).map((c) => ({ n, c })));
  expect(calls.map(({ n, c }) => `${n} ${c.argv.includes("--bare") ? "grader" : c.argv[0]}`).sort()).toEqual([
    "claude -p", "claude grader", "claude grader", "claude grader", "codex exec", "codex plugin", "codex plugin", "opencode run",
    "python3 /c.py", "python3 /c.py", "python3 /c.py",
  ]);
  for (const { c } of calls) expect(c.env.PWD).toBe(c.cwd);
});

test("an opencode that writes into $PWD lands its file in the trial workspace, and the trial passes", async () => {
  const elsewhere = join(box.root, "invoked-from");
  mkdirSync(elsewhere);
  installStub(box.bin, "opencode", [{ prefix: ["run"], stream: "A4-opencode-captured.jsonl", writeFiles: { "$PWD/HELLO.txt": "harness-ok" } }]);
  installStub(box.bin, "python3", [
    { ifExists: "HELLO.txt", stdout: '[{"id":"hello-file-exists","passed":true,"evidence":"HELLO.txt present"}]' },
    { stdout: '[{"id":"hello-file-exists","passed":false,"evidence":"HELLO.txt missing in workspace"}]' },
  ]);
  const row = await runTrial(
    spec({ harness: "opencode", keepWorkspaces: true, kase: kase({ check: "/c.py" }), baseEnv: { PATH: box.bin, ANTHROPIC_API_KEY: "k", PWD: elsewhere } }),
  );
  expect(row.passed).toBe(true);
  expect(readFileSync(join(row.workspace!, "HELLO.txt"), "utf8")).toBe("harness-ok");
  expect(existsSync(join(elsewhere, "HELLO.txt"))).toBe(false);
});
