import { afterEach, beforeEach, expect, test } from "bun:test";
import { mkdirSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { main, PKG_DIR, runOptions, USAGE } from "../src/commands.ts";
import { captureIo } from "./helpers/cli.ts";
import { installStub, sandbox, stubCalls } from "./helpers/stubs.ts";

let box: ReturnType<typeof sandbox>;
beforeEach(() => {
  box = sandbox();
});
afterEach(() => box.cleanup());

async function run(args: string[]) {
  const c = captureIo();
  const code = await main(args, c.io);
  return { code, out: c.out.join("\n"), err: c.err.join("\n") };
}

test("--help prints usage to stdout and exits 0; no arguments prints it to stderr and exits 2", async () => {
  expect(await run(["--help"])).toEqual({ code: 0, out: USAGE, err: "" });
  expect(await run([])).toEqual({ code: 2, out: "", err: USAGE });
});

test("unknown harness names exit 3 before any bad input", async () => {
  const msg = "unknown harness 'gemini'; valid harnesses: claude, codex, opencode";
  expect(await run(["--harness", "claude,gemini", "--bogus"])).toEqual({ code: 3, out: "", err: msg });
  expect(await run(["x", "--report", "--harness=gemini"])).toEqual({ code: 3, out: "", err: msg });
  expect((await run(["campaign", "--harness", "gemini"])).code).toBe(3);
});

test("usage errors, bad configs and a missing --candidate-dir exit 2", async () => {
  const cases: [string[], string][] = [
    [["--trials", "2"], "no candidate name"],
    [["x", "--candidate-dir", "d", "--bogus"], "unknown flag --bogus"],
    [["x", "--candidate-dir", "d", "--trials", "two"], "--trials must be an integer of at least 1, got 'two'"],
    [["x", "--candidate-dir", "d", "--trials", "0"], "--trials must be an integer of at least 1, got '0'"],
    [["x", "--candidate-dir", "d", "--timeout", "1.5"], "--timeout must be an integer of at least 1, got '1.5'"],
    [["x", "--candidate-dir", "d", "--configs", "with,treatment"], "unknown config 'treatment'; valid configs: with, baseline"],
    [["x"], "--candidate-dir is required"],
    [["x", "--candidate-dir"], "--candidate-dir needs a value"],
    [["x", "y", "--candidate-dir", "d"], "unexpected argument 'y'"],
    [["x", "--candidate-dir", "d", "--dry-run"], "--dry-run is not valid outside campaign"],
  ];
  for (const [args, msg] of cases) {
    expect(await run(args)).toEqual({ code: 2, out: "", err: `agent-harness: ${msg} (see agent-harness --help)` });
  }
});

test("candidate and dataset errors exit 2 before any agent CLI runs", async () => {
  installStub(box.bin, "claude", [{}]);
  const savedPath = process.env.PATH;
  process.env.PATH = box.bin;
  try {
    const missing = join(box.root, "nope");
    expect(await run(["x", "--candidate-dir", missing])).toEqual({ code: 2, out: "", err: `no such candidate path: ${missing}` });
    const skill = join(box.root, "skill");
    mkdirSync(skill);
    writeFileSync(join(skill, "SKILL.md"), "s");
    const cases = join(box.root, "cases");
    const r = await run(["mine", "--candidate-dir", skill, "--cases-dir", cases]);
    expect(r).toEqual({ code: 2, out: "", err: `no eval cases at ${join(cases, "mine")} — copy cases/_template to author some` });
    expect(stubCalls(box.bin, "claude")).toEqual([]);
  } finally {
    process.env.PATH = savedPath;
  }
});

test("defaults resolve against the package dir; relative paths against the cwd", () => {
  const d = runOptions(new Map(), "x", false);
  expect(d).toMatchObject({
    harnesses: ["claude"], models: null, configs: ["with", "baseline"], trials: 3, campaign: "", timeoutSec: 600,
    graderModel: "claude-haiku-4-5-20251001", keepWorkspaces: false, casesDir: join(PKG_DIR, "cases"),
    results: join(PKG_DIR, "results.jsonl"), runsDir: join(PKG_DIR, "runs"),
  });
  const r = runOptions(new Map([["--results", "out/r.jsonl"], ["--model", "a,b,a"], ["--harness", "codex,claude,codex"]]), "x", false);
  expect(r.results).toBe(resolve("out/r.jsonl"));
  expect(r.resultsShown).toBe("out/r.jsonl");
  expect(r.models).toEqual(["a", "b"]);
  expect(r.harnesses).toEqual(["codex", "claude"]);
  const c = runOptions(new Map(), "campaign", true);
  expect(c.harnesses).toEqual(["claude", "opencode", "codex"]);
  expect(c.campaign).toMatch(/^weekly-\d{8}$/);
});
