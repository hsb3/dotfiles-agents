import { afterEach, beforeEach, expect, test } from "bun:test";
import { mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { readRows } from "../src/ledger.ts";
import { runCli } from "./helpers/cli.ts";
import { installStub, sandbox, stubCalls, type StubRule } from "./helpers/stubs.ts";

let box: ReturnType<typeof sandbox>;
let env: Record<string, string>;
let skill: string;
let out: string;
beforeEach(() => {
  box = sandbox();
  mkdirSync(join(box.root, "home"));
  mkdirSync(join(box.root, "tmp"));
  env = { PATH: `${box.bin}:/usr/bin:/bin`, HOME: join(box.root, "home"), TMPDIR: join(box.root, "tmp"), ANTHROPIC_API_KEY: "sk-a" };
  skill = join(box.root, "cands", "demo-skill");
  mkdirSync(skill, { recursive: true });
  writeFileSync(join(skill, "SKILL.md"), "---\nname: demo-skill\n---\nSay OK.");
  out = join(box.root, "out");
});
afterEach(() => box.cleanup());

const SHIPPED = join(import.meta.dir, "..", "cases");

const claudeAgent = (extra: Partial<StubRule> = {}): StubRule[] => [
  { prefix: ["--version"], stdout: "2.1.296 (Claude Code)\n" },
  { has: ["--bare"], stream: "A11-grader-result.json" },
  { prefix: ["-p"], stream: "A2-claude-skill-trial.jsonl", writeFiles: { "HELLO.txt": "harness-ok" }, ...extra },
];

// The shipped smoke-echo check.py, answered by a stub python3 that inspects the workspace like the real one.
const pythonCheck: StubRule[] = [{ stdout: '[{"id":"hello-file-exists","passed":true,"evidence":"HELLO.txt present"}]' }];

const runArgs = (...extra: string[]) => [
  "smoke-echo", "--candidate-dir", skill, "--cases-dir", SHIPPED, "--results", join(out, "results.jsonl"), "--runs-dir", join(out, "runs"),
  "--trials", "1", ...extra,
];

test("runs the smoke-echo case under claude, prints the run lines and report, and resumes on rerun", async () => {
  installStub(box.bin, "claude", claudeAgent());
  installStub(box.bin, "python3", pythonCheck);
  const first = await runCli(runArgs(), env);
  expect(first.stderr).toBe("");
  expect(first.code).toBe(0);
  const lines = first.stdout.split("\n");
  expect(lines.slice(0, 6)).toEqual([
    "preconditions: harness=claude · cli=2.1.296 (Claude Code) · campaign=(none) · model=claude-sonnet-4-5 · grader=claude-haiku-4-5-20251001 · timeout=600s · auth_env=ANTHROPIC_API_KEY · network=assumed-available",
    "✓ claude create-file with trial 0",
    "✓ claude create-file baseline trial 0",
    "",
    `2 trial(s) run, 0 skipped (already in ${join(out, "results.jsonl")})`,
    "",
  ]);
  expect(lines[6]).toBe("smoke-echo — 2 trial row(s)");
  expect(lines[9]).toStartWith("-         claude   claude-sonnet-4-5  create-file  baseline  1  1.00  Y    Y    0.1977±0.0000  44168±0");
  expect(lines[11]).toBe("delta (with - baseline) [claude/claude-sonnet-4-5] create-file: +0.00");
  const rows = readRows(join(out, "results.jsonl"));
  expect(rows.map((r) => [r.config, r.trial, r.passed, r.kind, r.grader_model])).toEqual([
    ["with", 0, true, "skill", null],
    ["baseline", 0, true, "skill", null],
  ]);
  expect(readdirSync(join(out, "runs"))).toHaveLength(2);
  expect(readdirSync(join(box.root, "tmp")).filter((f) => f.startsWith("harness-"))).toEqual([]);
  // smoke-echo has no assertions, so no grader call: only the version and two agent runs.
  expect(stubCalls(box.bin, "claude").map((c) => c.argv[0])).toEqual(["--version", "-p", "-p"]);

  const again = await runCli(runArgs(), env);
  expect(again.code).toBe(0);
  expect(again.stdout.split("\n").slice(1, 4)).toEqual(["", `0 trial(s) run, 2 skipped (already in ${join(out, "results.jsonl")})`, ""]);
  expect(readRows(join(out, "results.jsonl"))).toHaveLength(2);
});

test("a relative --results is resolved against the cwd and shown as given", async () => {
  installStub(box.bin, "claude", claudeAgent());
  installStub(box.bin, "python3", pythonCheck);
  mkdirSync(out);
  const r = await runCli(["smoke-echo", "--candidate-dir", skill, "--cases-dir", SHIPPED, "--results", "r.jsonl", "--runs-dir", "runs", "--trials", "1", "--configs", "with"], env, out);
  expect(r.stdout).toContain("1 trial(s) run, 0 skipped (already in r.jsonl)");
  const [row] = readRows(join(out, "r.jsonl"));
  expect(row!.log_path).toMatch(/^runs\/claude-smoke-echo-create-file-with-0-/);
});

test("cells run harness-major across models; failed preflight cells are skipped with their reason", async () => {
  installStub(box.bin, "claude", claudeAgent());
  installStub(box.bin, "python3", pythonCheck);
  const r = await runCli(runArgs("--harness", "opencode,claude,codex", "--model", "m1,m2", "--configs", "with", "--campaign", "wk"), env);
  expect(r.code).toBe(0);
  expect(r.stderr.split("\n")).toEqual([
    "opencode: CLI not found on PATH",
    "opencode: CLI not found on PATH",
    "codex: CLI not found on PATH",
    "codex: CLI not found on PATH",
    "",
  ]);
  const pre = r.stdout.split("\n").filter((l) => l.startsWith("preconditions:"));
  expect(pre.map((l) => l.split(" · ")[3])).toEqual(["model=m1", "model=m2"]);
  expect(pre[0]).toContain("campaign=wk");
  const agentCalls = stubCalls(box.bin, "claude").filter((c) => c.argv[0] === "-p");
  expect(agentCalls.map((c) => c.argv.at(-1))).toEqual(["m1", "m2"]);
  expect(readRows(join(out, "results.jsonl")).map((r) => r.model)).toEqual(["m1", "m2"]);
});

test("exit 1 when no cell passes preflight", async () => {
  const r = await runCli(runArgs("--harness", "codex"), { ...env, OPENAI_API_KEY: "" });
  expect(r).toEqual({ code: 1, stdout: "", stderr: "codex: CLI not found on PATH\n" });
  installStub(box.bin, "codex", [{}]);
  const r2 = await runCli(runArgs("--harness", "codex"), env);
  expect(r2).toEqual({ code: 1, stdout: "", stderr: "codex: no credentials — set one of OPENAI_API_KEY\n" });
});

test("failing trials print ✗ and keep their workspace", async () => {
  installStub(box.bin, "claude", claudeAgent({ stream: "A1-claude-api-error.jsonl", exit: 1, writeFiles: {} }));
  installStub(box.bin, "python3", [{ stdout: '[{"id":"hello-file-exists","passed":false,"evidence":"HELLO.txt missing"}]' }]);
  const r = await runCli(runArgs("--configs", "with"), env);
  expect(r.code).toBe(0);
  expect(r.stdout.split("\n")[1]).toBe("✗ claude create-file with trial 0");
  const [row] = readRows(join(out, "results.jsonl"));
  expect(row!.workspace).toMatch(/\/ws$/);
});

test("--report prints the candidate's report without --candidate-dir", async () => {
  installStub(box.bin, "claude", claudeAgent());
  installStub(box.bin, "python3", pythonCheck);
  await runCli(runArgs(), env);
  const r = await runCli(["smoke-echo", "--report", "--results", join(out, "results.jsonl"), "--trials", "9"], env);
  expect(r.code).toBe(0);
  expect(r.stdout.split("\n")[1]).toBe("smoke-echo — 2 trial row(s)");
  const none = await runCli(["other", "--report", "--results", join(out, "missing.jsonl")], env);
  expect(none).toEqual({ code: 0, stdout: "no result rows for other\n", stderr: "" });
});

test("the shipped check.py runs under the real python3 when one is available", async () => {
  const python = Bun.which("python3", { PATH: process.env.PATH ?? "" });
  if (!python) return;
  installStub(box.bin, "claude", claudeAgent());
  const r = await runCli(runArgs("--configs", "with"), { ...env, PATH: `${box.bin}:${process.env.PATH}`, HOME: process.env.HOME ?? env.HOME! });
  expect(r.code).toBe(0);
  const [row] = readRows(join(out, "results.jsonl"));
  expect(row!.checks).toEqual([
    { id: "hello-file-exists", passed: true, evidence: "HELLO.txt present" },
    { id: "hello-content", passed: true, evidence: "HELLO.txt content='harness-ok' (want 'harness-ok')" },
  ]);
  expect(row!.passed).toBe(true);
});
