import { afterEach, beforeEach, expect, test } from "bun:test";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { discoverCandidates, resolveCandidatePath } from "../src/campaign.ts";
import { readRows } from "../src/ledger.ts";
import { runCli } from "./helpers/cli.ts";
import { installStub, sandbox, stubCalls } from "./helpers/stubs.ts";

let box: ReturnType<typeof sandbox>;
let env: Record<string, string>;
let cases: string;
let root: string;
let out: string;

function write(path: string, body: string): void {
  mkdirSync(join(path, ".."), { recursive: true });
  writeFileSync(path, body);
}

beforeEach(() => {
  box = sandbox();
  mkdirSync(join(box.root, "home"));
  mkdirSync(join(box.root, "tmp"));
  env = { PATH: `${box.bin}:/usr/bin:/bin`, HOME: join(box.root, "home"), TMPDIR: join(box.root, "tmp"), ANTHROPIC_API_KEY: "a" };
  cases = join(box.root, "cases");
  root = join(box.root, "primitives");
  out = join(box.root, "out");
  for (const name of ["_template", "smoke-echo", "mermaid", "scout", "ghost"]) {
    write(join(cases, name, "c1", "case.json"), '{"prompt":"Do the thing"}');
  }
  write(join(root, "skills", "mermaid", "SKILL.md"), "skill");
  write(join(root, "agents", "scout.md"), "---\nname: scout\n---\nScout.");
  installStub(box.bin, "claude", [
    { prefix: ["--version"], stdout: "2.1.296 (Claude Code)" },
    { prefix: ["-p"], stream: "A2-claude-skill-trial.jsonl" },
  ]);
});
afterEach(() => box.cleanup());

const args = (...extra: string[]) => [
  "campaign", "--cases-dir", cases, "--candidates-root", root, "--results", join(out, "results.jsonl"), "--runs-dir", join(out, "runs"),
  "--harness", "claude", "--trials", "1", ...extra,
];

test("candidates are the sorted case subdirs minus _template and smoke-echo; paths resolve dirs first, then agents/<name>.md", () => {
  expect(discoverCandidates(cases)).toEqual(["ghost", "mermaid", "scout"]);
  expect(discoverCandidates(join(box.root, "none"))).toEqual([]);
  write(join(root, "aaa", "scout", "x.md"), "x");
  expect(resolveCandidatePath(root, "scout")).toBe(join(root, "aaa", "scout"));
  expect(resolveCandidatePath(root, "mermaid")).toBe(join(root, "skills", "mermaid"));
  expect(resolveCandidatePath(root, "ghost")).toBeNull();
});

test("runs every candidate with the dated label, warns on a missing one, prints reports, and logs everything", async () => {
  const r = await runCli(args(), env);
  expect(r.code).toBe(1);
  const lines = r.stdout.split("\n");
  const label = lines[0]!.match(/^=== campaign (weekly-\d{8}) @ \d{4}-\d\d-\d\d \d\d:\d\d:\d\d ===$/)![1]!;
  expect(lines[1]).toBe("candidates: ghost mermaid scout");
  expect(r.stderr).toBe(`WARN: no candidate named 'ghost' under ${root}\n`);
  expect(lines.filter((l) => l.startsWith("preconditions:"))).toHaveLength(2);
  expect(lines.filter((l) => l.startsWith("✓ claude c1"))).toEqual(["✓ claude c1 with trial 0", "✓ claude c1 baseline trial 0", "✓ claude c1 with trial 0", "✓ claude c1 baseline trial 0"]);
  const reports = lines.filter((l) => l.startsWith("=== report:"));
  expect(reports).toEqual(["=== report: ghost ===", "=== report: mermaid ===", "=== report: scout ==="]);
  expect(lines[lines.indexOf("=== report: ghost ===") + 1]).toBe("no result rows for ghost");
  const logPath = join(out, "campaign-logs", `${label}.log`);
  expect(lines.at(-2)).toBe(`campaign '${label}' complete: 1 failed (log: ${logPath})`);
  const rows = readRows(join(out, "results.jsonl"));
  expect(rows.map((r) => [r.candidate, r.campaign, r.kind])).toEqual([
    ["mermaid", label, "skill"], ["mermaid", label, "skill"], ["scout", label, "agent"], ["scout", label, "agent"],
  ]);
  // The log holds everything printed, stdout and stderr, in order.
  const log = readFileSync(logPath, "utf8");
  expect(log).toContain(`WARN: no candidate named 'ghost' under ${root}\n`);
  expect(log.endsWith(`campaign '${label}' complete: 1 failed (log: ${logPath})\n`)).toBe(true);
  expect(log.split("\n").length).toBe(lines.length + 1);

  // A same-day rerun reuses the label, resumes, and appends to the same log.
  const again = await runCli(args(), env);
  expect(again.stdout).toContain(`0 trial(s) run, 2 skipped (already in ${join(out, "results.jsonl")})`);
  expect(readRows(join(out, "results.jsonl"))).toHaveLength(4);
  expect(readFileSync(logPath, "utf8").length).toBeGreaterThan(log.length);
});

test("a candidate whose run exits non-zero prints FAILED and the campaign continues", async () => {
  write(join(root, "skills", "ghost", "notes.txt"), "not a candidate");
  const r = await runCli(args(), env);
  expect(r.code).toBe(1);
  expect(r.stderr).toBe(`${join(root, "skills", "ghost")}: not recognizable as skill / agent / plugin\nFAILED: candidate 'ghost' exited 2\n`);
  expect(r.stdout).toContain("campaign '");
  expect(readRows(join(out, "results.jsonl"))).toHaveLength(4);
});

test("all candidates exiting 0 completes ok and exits 0", async () => {
  write(join(root, "skills", "ghost", "SKILL.md"), "skill");
  const r = await runCli(args("--campaign", "wk1"), env);
  expect(r.code).toBe(0);
  expect(r.stdout.split("\n").at(-2)).toBe(`campaign 'wk1' complete: ok (log: ${join(out, "campaign-logs", "wk1.log")})`);
});

test("--dry-run prints the commands, runs nothing and writes nothing", async () => {
  const r = await runCli(args("--campaign", "wk2", "--model", "m1,m2", "--configs", "with"), { ...env });
  const d = await runCli(args("--campaign", "wk3", "--dry-run"), env);
  expect(d.code).toBe(1);
  expect(d.stdout.split("\n")).toEqual([
    expect.stringMatching(/^=== campaign wk3 @ /),
    "candidates: ghost mermaid scout",
    `DRYRUN: agent-harness mermaid --candidate-dir ${join(root, "skills", "mermaid")} --cases-dir ${cases} --harness claude --configs with,baseline --trials 1 --campaign wk3`,
    "DRYRUN: agent-harness mermaid --report",
    `DRYRUN: agent-harness scout --candidate-dir ${join(root, "agents", "scout.md")} --cases-dir ${cases} --harness claude --configs with,baseline --trials 1 --campaign wk3`,
    "DRYRUN: agent-harness scout --report",
    "campaign 'wk3' complete: 1 failed",
    "",
  ]);
  expect(d.stderr).toBe(`WARN: no candidate named 'ghost' under ${root}\n`);
  expect(existsSync(join(out, "campaign-logs", "wk3.log"))).toBe(false);
  const calls = stubCalls(box.bin, "claude").length;
  const d2 = await runCli(args("--campaign", "wk3", "--dry-run", "--model", "m1"), env);
  expect(d2.stdout).toContain("--trials 1 --campaign wk3 --model m1\n");
  expect(stubCalls(box.bin, "claude").length).toBe(calls);
  expect(r.code).toBe(1);
});

test("missing campaign inputs exit 2; no candidates exit 1", async () => {
  const noRoot = await runCli(["campaign", "--cases-dir", cases], env);
  expect(noRoot).toEqual({ code: 2, stdout: "", stderr: "agent-harness: campaign needs --cases-dir and --candidates-root (see agent-harness --help)\n" });
  const empty = join(box.root, "empty");
  mkdirSync(empty);
  const none = await runCli(["campaign", "--cases-dir", empty, "--candidates-root", root], env);
  expect(none).toEqual({ code: 1, stdout: "", stderr: `no candidates discovered under ${empty}\n` });
});
