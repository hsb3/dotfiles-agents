import { afterEach, beforeEach, expect, test } from "bun:test";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { grade, graderArgv, graderPrompt, parseGrades, workspaceDigest } from "../src/grader.ts";
import { installStub, sandbox, stubCalls } from "./helpers/stubs.ts";

let box: ReturnType<typeof sandbox>;
let ws: string;
beforeEach(() => {
  box = sandbox();
  ws = join(box.root, "run", "ws");
  mkdirSync(ws, { recursive: true });
});
afterEach(() => box.cleanup());

const SCHEMA =
  '{"type":"object","properties":{"grades":{"type":"array","items":{"type":"object","properties":{"id":{"type":"string"},"passed":{"type":"boolean"},"evidence":{"type":"string"}},"required":["id","passed","evidence"]}}},"required":["grades"]}';

const assertions = [{ id: "a1-diagram-covers-all-services", text: "The diagram covers every service." }];

test("argv is claude -p --bare with the compact schema", () => {
  expect(graderArgv("P", "claude-haiku-4-5-20251001")).toEqual([
    "claude", "-p", "P", "--bare", "--model", "claude-haiku-4-5-20251001", "--output-format", "json", "--json-schema", SCHEMA,
    "--allowedTools", "Read,Grep,Glob", "--setting-sources", "", "--strict-mcp-config",
  ]);
});

test("the digest lists files recursively, sorted, with sizes; empty and capped forms", () => {
  expect(workspaceDigest(ws)).toBe("(empty)");
  mkdirSync(join(ws, "src/deep"), { recursive: true });
  writeFileSync(join(ws, "src/deep/b.ts"), "12345");
  writeFileSync(join(ws, "README.md"), "");
  writeFileSync(join(ws, "a.txt"), "abc");
  expect(workspaceDigest(ws)).toBe("README.md (0B)\na.txt (3B)\nsrc/deep/b.ts (5B)");
  for (let i = 0; i < 90; i++) writeFileSync(join(ws, `f${String(i).padStart(2, "0")}`), "x");
  const lines = workspaceDigest(ws).split("\n");
  expect(lines).toHaveLength(81);
  expect(lines[80]).toBe("... and 13 more");
});

test("the prompt is verbatim with the truncated result and compact assertions", () => {
  const p = graderPrompt("a.txt (3B)", "r".repeat(3500), assertions);
  expect(p).toStartWith("You are an impartial grader for a coding-agent trial. Judge each assertion");
  expect(p).toContain("Do not give benefit of the doubt.\n\nWorkspace files:\na.txt (3B)\n\nAgent's final response (truncated):\n" + "r".repeat(3000) + "\n\nAssertions (JSON):\n");
  expect(p).toEndWith(`${JSON.stringify(assertions)}\n\nReturn JSON matching the schema: every assertion id exactly once.`);
  expect(graderPrompt("(empty)", null, [])).toContain("(truncated):\n\n\nAssertions");
});

test("grades come from structured_output.grades", async () => {
  installStub(box.bin, "claude", [{ has: ["--bare"], stream: "A11-grader-result.json" }]);
  const runDir = join(box.root, "run");
  const grades = await grade({
    runDir, ws, result: "done", assertions, model: "claude-haiku-4-5-20251001", timeoutSec: 10,
    baseEnv: { PATH: box.bin, ANTHROPIC_API_KEY: "k", CLAUDECODE: "1", CLAUDE_CONFIG_DIR: "/real", XDG_CACHE_HOME: "/x" },
  });
  expect(grades).toEqual([{ id: "a1-diagram-covers-all-services", passed: true, evidence: "README.md lines 7-17 contain a Mermaid flowchart with all six services" }]);
  const [call] = stubCalls(box.bin, "claude");
  expect(call!.cwd).toEndWith("/run/ws");
  expect(call!.env.HOME).toBe(join(runDir, "grader-home"));
  expect(call!.env.CLAUDE_CONFIG_DIR).toBe(join(runDir, "grader-config"));
  expect(call!.env.CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS).toBe("1");
  expect(call!.env.ANTHROPIC_API_KEY).toBe("k");
  expect(call!.env.CLAUDECODE).toBeUndefined();
  expect(call!.env.XDG_CACHE_HOME).toBeUndefined();
});

test("anything but a grades array gives grader-error for every assertion", async () => {
  const failed = [{ id: "a1-diagram-covers-all-services", passed: false, evidence: "grader-error" }];
  const req = { runDir: join(box.root, "run"), ws, result: "", assertions, model: "m", timeoutSec: 5, baseEnv: { PATH: box.bin } };
  expect(await grade(req)).toEqual(failed);
  installStub(box.bin, "claude", [{ stdout: "not json" }]);
  expect(await grade(req)).toEqual(failed);
  installStub(box.bin, "claude", [{ stdout: '{"type":"result","result":"x"}' }]);
  expect(await grade(req)).toEqual(failed);
  expect(parseGrades('{"structured_output":{"grades":"no"}}')).toBeNull();
});
