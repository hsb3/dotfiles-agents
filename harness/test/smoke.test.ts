import { afterEach, beforeEach, expect, test } from "bun:test";
import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { runCli } from "./helpers/cli.ts";
import { installStub, sandbox, STREAMS, stubCalls } from "./helpers/stubs.ts";

let box: ReturnType<typeof sandbox>;
let env: Record<string, string>;
let skill: string;
let plugin: string;
let runs: string;
beforeEach(() => {
  box = sandbox();
  mkdirSync(join(box.root, "home"));
  mkdirSync(join(box.root, "tmp"));
  env = { PATH: `${box.bin}:/usr/bin:/bin`, HOME: join(box.root, "home"), TMPDIR: join(box.root, "tmp"), ANTHROPIC_API_KEY: "a", OPENAI_API_KEY: "o" };
  skill = join(box.root, "demo-skill");
  mkdirSync(skill);
  writeFileSync(join(skill, "SKILL.md"), "Say OK.");
  plugin = join(box.root, "demo-plugin");
  mkdirSync(join(plugin, ".claude-plugin"), { recursive: true });
  writeFileSync(join(plugin, ".claude-plugin", "plugin.json"), '{"name":"demo-plugin","version":"0.1.0"}');
  runs = join(box.root, "runs");
});
afterEach(() => box.cleanup());

const smoke = (dir: string, ...extra: string[]) => ["demo", "--candidate-dir", dir, "--smoke", "--runs-dir", runs, ...extra];

test("A1: claude lists its plugins, the exit line and FAILED; the raw stdout is logged; no ledger row", async () => {
  installStub(box.bin, "claude", [{ prefix: ["--version"], stdout: "2.1.296 (Claude Code)" }, { prefix: ["-p"], stream: "A1-claude-api-error.jsonl", exit: 1 }]);
  const r = await runCli([...smoke(skill), "--model", "claude-haiku-4-5", "--results", join(box.root, "results.jsonl")], env);
  expect(r.code).toBe(1);
  expect(r.stdout).toBe(
    [
      "harness: claude",
      "kind: skill",
      "plugins loaded: eval-demo-skill, cc-plugin-agents-md",
      "✗ exit 1: API Error: 400 The requested features are not available for HIPAA-configured organizations: context_management.",
      "✗ loadability FAILED",
      "",
    ].join("\n"),
  );
  const [log] = readdirSync(runs);
  expect(log).toMatch(/^claude-smoke-demo-\d{8}-\d{6}-[0-9a-f]{32}\.log$/);
  expect(readFileSync(join(runs, log!), "utf8")).toBe(readFileSync(join(STREAMS, "A1-claude-api-error.jsonl"), "utf8"));
  expect(existsSync(join(box.root, "results.jsonl"))).toBe(false);
  expect(readdirSync(join(box.root, "tmp")).filter((f) => f.startsWith("harness-"))).toEqual([]);
  // Same injection, argv and isolation as a with trial, with the smoke prompt and the cell's model.
  const call = stubCalls(box.bin, "claude").find((c) => c.argv[0] === "-p")!;
  expect(call.argv[1]).toBe("Reply with exactly: OK");
  expect(call.argv).toContain("--plugin-dir");
  expect(call.argv.at(-1)).toBe("claude-haiku-4-5");
  expect(call.env.HOME).toMatch(/\/home$/);
});

test("A3: a plugin error fails the cell even with exit 0", async () => {
  installStub(box.bin, "claude", [{ prefix: ["-p"], stream: "A3-claude-plugin-error.jsonl" }]);
  const r = await runCli(smoke(plugin), env);
  expect(r.code).toBe(1);
  expect(r.stdout.split("\n")).toEqual([
    "harness: claude",
    "kind: plugin",
    "plugins loaded: (none)",
    '✗ plugin_error: {"plugin":"eval-x","message":"boom"}',
    "✗ loadability FAILED",
    "",
  ]);
});

test("A4 under opencode passes with plugins not reported; a missing CLI cell does not run", async () => {
  installStub(box.bin, "opencode", [{ prefix: ["run"], stream: "A4-opencode-captured.jsonl" }]);
  const r = await runCli(smoke(skill, "--harness", "opencode,codex"), env);
  expect(r.code).toBe(0);
  expect(r.stderr).toBe("codex: CLI not found on PATH\n");
  expect(r.stdout).toBe("harness: opencode\nkind: skill\nplugins loaded: (not reported)\n✓ loadability OK\n");
});

test("an unhostable kind prints the skip line and fails the cell; blocks are separated by a blank line", async () => {
  installStub(box.bin, "opencode", [{ prefix: ["run"], stream: "A4-opencode-captured.jsonl" }]);
  installStub(box.bin, "claude", [{ prefix: ["-p"], stream: "A2-claude-skill-trial.jsonl" }]);
  const r = await runCli(smoke(plugin, "--harness", "claude,opencode"), env);
  expect(r.code).toBe(1);
  expect(r.stdout).toBe(
    "harness: claude\nkind: plugin\nplugins loaded: eval-mermaid\n✓ loadability OK\n\nharness: opencode\nkind: plugin\n∅ opencode cannot host kind=plugin — skip\n",
  );
  expect(stubCalls(box.bin, "opencode")).toEqual([]);
});

test("a failed codex plugin install prints as a plugin_error line", async () => {
  installStub(box.bin, "codex", [
    { prefix: ["plugin", "marketplace", "add"], stream: "A10-codex-marketplace-add.json" },
    { prefix: ["plugin", "add"], stderr: "plugin not found", exit: 1 },
  ]);
  const r = await runCli(smoke(plugin, "--harness", "codex"), env);
  expect(r.code).toBe(1);
  expect(r.stdout.split("\n")).toEqual([
    "harness: codex",
    "kind: plugin",
    "plugins loaded: (not reported)",
    "✗ plugin_error: codex plugin install failed: plugin not found",
    "✗ exit 1: codex plugin install failed: plugin not found",
    "✗ loadability FAILED",
    "",
  ]);
});

test("exit 1 when no cell ran; exit 2 on a bad candidate", async () => {
  expect(await runCli(smoke(skill), env)).toEqual({ code: 1, stdout: "", stderr: "claude: CLI not found on PATH\n" });
  expect((await runCli(smoke(join(box.root, "missing")), env)).code).toBe(2);
});
