import { afterEach, beforeEach, expect, test } from "bun:test";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { loadCandidate } from "../src/candidate.ts";
import { codex } from "../src/codex.ts";
import { adapterFor, childEnv, preflight } from "../src/harnesses.ts";
import { installStub, sandbox, STREAMS, stubCalls, stubPath } from "./helpers/stubs.ts";

let box: ReturnType<typeof sandbox>;
beforeEach(() => {
  box = sandbox();
});
afterEach(() => box.cleanup());

const stream = (name: string) => readFileSync(join(STREAMS, name), "utf8");

function dir(name: string, files: Record<string, string>): string {
  const d = join(box.root, name);
  for (const [rel, body] of Object.entries(files)) {
    mkdirSync(join(d, rel, ".."), { recursive: true });
    writeFileSync(join(d, rel), body);
  }
  return d;
}

function ctx() {
  const runDir = join(box.root, "run");
  const ws = join(runDir, "ws");
  mkdirSync(ws, { recursive: true });
  return { runDir, ws, env: childEnv(codex, runDir, { PATH: stubPath(box.bin, false), OPENAI_API_KEY: "sk-test" }) };
}

test("registered with its default model; preflight needs OPENAI_API_KEY", () => {
  expect(adapterFor("codex")).toBe(codex);
  expect(codex.defaultModel).toBe("gpt-6.1-sol");
  installStub(box.bin, "codex", [{}]);
  expect(preflight("codex", { PATH: box.bin, OPENAI_API_KEY: "" })).toBe("codex: no credentials — set one of OPENAI_API_KEY");
  expect(preflight("codex", { PATH: box.bin, OPENAI_API_KEY: "k" })).toBeNull();
});

test("argv follows the spec and never ignores the user config", () => {
  const argv = codex.argv("do it", "gpt-6.1-sol", "/run/ws", []);
  expect(argv).toEqual([
    "codex", "exec", "--json", "--skip-git-repo-check", "--ephemeral", "--sandbox", "workspace-write",
    "-c", "sandbox_workspace_write.network_access=true", "--dangerously-bypass-hook-trust", "--disable", "shell_snapshot",
    "-C", "/run/ws", "-m", "gpt-6.1-sol", "do it",
  ]);
  expect(argv).not.toContain("--ignore-user-config");
});

test("the environment scrubs CODEX_*, passes OPENAI_API_KEY on as CODEX_API_KEY and withholds every provider key", () => {
  const run = join(box.root, "run");
  const keys = {
    ANTHROPIC_API_KEY: "a", OPENAI_API_KEY: "sk", GEMINI_API_KEY: "g", GOOGLE_GENERATIVE_AI_API_KEY: "gg", OPENROUTER_API_KEY: "o", GROQ_API_KEY: "q",
  };
  const env = childEnv(codex, run, { CODEX_HOME: "/real", CODEX_SANDBOX: "x", XDG_CONFIG_HOME: "/x", PATH: "/bin", ...keys });
  expect(env).toEqual({ PATH: "/bin", HOME: join(run, "home"), CODEX_HOME: join(run, "codex-home"), CODEX_API_KEY: "sk" });
  expect(existsSync(join(run, "codex-home"))).toBe(true);
});

test("a skill is copied under codex-home/skills", async () => {
  const c = loadCandidate("mermaid", dir("mermaid", { "SKILL.md": "skill" }));
  expect(await codex.inject(c, ctx())).toEqual({ args: [] });
  expect(readFileSync(join(box.root, "run/codex-home/skills/mermaid/SKILL.md"), "utf8")).toBe("skill");
});

test("agents become codex-home/agents/<name>.toml with exactly three JSON-literal keys", async () => {
  const c = loadCandidate("a", dir("a", { "scout.md": '---\nname: scout\ndescription: Says "hi".\nmodel: haiku\ntools: Read\n---\nLine 1\nLine 2' }));
  await codex.inject(c, ctx());
  expect(readFileSync(join(box.root, "run/codex-home/agents/scout.toml"), "utf8")).toBe(
    'name = "scout"\ndescription = "Says \\"hi\\"."\ndeveloper_instructions = "Line 1\\nLine 2"\n',
  );
});

test("a plugin is installed from a local marketplace with two codex plugin commands", async () => {
  installStub(box.bin, "codex", [
    { prefix: ["plugin", "marketplace", "add"], stream: "A10-codex-marketplace-add.json" },
    { prefix: ["plugin", "add"], stream: "A10-codex-plugin-add.json" },
  ]);
  const c = loadCandidate("demo", dir("demo", { ".claude-plugin/plugin.json": '{"name":"demo-plugin","version":"0.1.0"}', "skills/s/SKILL.md": "s" }));
  const x = ctx();
  expect(await codex.inject(c, x)).toEqual({ args: [] });
  const market = join(x.runDir, "codex-market");
  expect(readFileSync(join(market, ".claude-plugin/marketplace.json"), "utf8")).toBe(
    '{"name":"agent-harness","owner":{"name":"agent-harness"},"plugins":[{"name":"demo-plugin","source":"./plugins/demo-plugin","version":"0.1.0"}]}',
  );
  expect(readFileSync(join(market, "plugins/demo-plugin/skills/s/SKILL.md"), "utf8")).toBe("s");
  const calls = stubCalls(box.bin, "codex");
  expect(calls.map((c) => c.argv)).toEqual([
    ["plugin", "marketplace", "add", market, "--json", "--disable", "shell_snapshot"],
    ["plugin", "add", "demo-plugin@agent-harness", "--json", "--disable", "shell_snapshot"],
  ]);
  for (const call of calls) {
    expect(call.cwd).toEndWith("/run/ws");
    expect(call.env.CODEX_HOME).toBe(join(x.runDir, "codex-home"));
    expect(call.env.CODEX_API_KEY).toBe("sk-test");
    expect(call.env.OPENAI_API_KEY).toBeUndefined();
  }
});

test("a failing install step becomes the injection-failure message with its exit code", async () => {
  installStub(box.bin, "codex", [
    { prefix: ["plugin", "marketplace", "add"], stream: "A10-codex-marketplace-add.json" },
    { prefix: ["plugin", "add"], stderr: "plugin not found\n", exit: 1 },
  ]);
  const c = loadCandidate("demo", dir("demo", { ".claude-plugin/plugin.json": '{"name":"demo-plugin"}' }));
  expect(await codex.inject(c, ctx())).toEqual({ failure: "codex plugin install failed: plugin not found", exitCode: 1 });
});

test("a missing codex executable fails the install", async () => {
  const c = loadCandidate("demo", dir("demo", { ".claude-plugin/plugin.json": "{}" }));
  expect(await codex.inject(c, ctx())).toEqual({ failure: "codex plugin install failed: executable not found: codex", exitCode: -1 });
});

test("A7 folds the captured run, skipping notices", () => {
  const r = codex.fold(stream("A7-codex-captured.jsonl"));
  expect(r).toMatchObject({ result: "OK", tool_names: [], skill_used: false, input_tokens: 12868, output_tokens: 5, cache_read_tokens: 0, cache_creation_tokens: 12865, cost_usd: null, num_turns: null, event_error: null, plugin_errors: [] });
  expect(codex.succeeded(0, r)).toBe(true);
});

test("A8 records tool items and SKILL.md reads", () => {
  const r = codex.fold(stream("A8-codex-skill-trial.jsonl"));
  expect(r).toMatchObject({ tool_names: ["command_execution", "file_change"], skill_used: true, result: "Added the diagram to README.md.", input_tokens: 24310, output_tokens: 812, cache_read_tokens: 18944, cache_creation_tokens: 5120 });
});

test("A9: a failed turn is the event error; tokens stay null; not a success", () => {
  const r = codex.fold(stream("A9-codex-failed-turn.jsonl"));
  expect(r).toMatchObject({ result: "", input_tokens: null, output_tokens: null, cache_read_tokens: null, cache_creation_tokens: null, event_error: "unexpected status 401 Unauthorized: Incorrect API key provided" });
  expect(codex.succeeded(1, r)).toBe(false);
  expect(codex.succeeded(0, r)).toBe(false);
});

test("top-level error events count only when no turn ended", () => {
  expect(codex.fold('{"type":"error","message":"a"}\n{"type":"error","message":"b"}').event_error).toBe("b");
  expect(codex.fold('{"type":"error","message":"retry"}\n{"type":"turn.completed","usage":{}}').event_error).toBeNull();
});
