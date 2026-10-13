import { afterEach, beforeEach, expect, test } from "bun:test";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { loadCandidate, parseAgent } from "../src/candidate.ts";
import { adapterFor, preflight } from "../src/harnesses.ts";
import { opencode, translateAgent } from "../src/opencode.ts";
import { installStub, sandbox, STREAMS } from "./helpers/stubs.ts";

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

const SCOUT = `---
name: scout
description: Read-only investigator. Use before changing unfamiliar code.
model: haiku
tools: Read, Grep, Glob
---
You are a scout. Report what you find with file paths and line numbers.
`;

const ctx = () => ({ runDir: join(box.root, "run"), ws: join(box.root, "run", "ws"), env: {} });

test("registered with its default model; preflight needs one of the six auth variables", () => {
  expect(adapterFor("opencode")).toBe(opencode);
  expect(opencode.defaultModel).toBe("claude-sonnet-4-5");
  installStub(box.bin, "opencode", [{}]);
  expect(preflight("opencode", { PATH: box.bin })).toBe(
    "opencode: no credentials — set one of ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, GOOGLE_GENERATIVE_AI_API_KEY, OPENROUTER_API_KEY, GROQ_API_KEY",
  );
  expect(preflight("opencode", { PATH: box.bin, OPENROUTER_API_KEY: "k" })).toBeNull();
  expect(preflight("opencode", { PATH: join(box.root, "none"), OPENROUTER_API_KEY: "k" })).toBe("opencode: CLI not found on PATH");
});

test("argv uses --standalone and prefixes anthropic/ only to ids without /", () => {
  expect(opencode.argv("do it", "claude-haiku-4-5", "/ws", [])).toEqual([
    "opencode", "run", "do it", "--format", "json", "--auto", "--standalone", "-m", "anthropic/claude-haiku-4-5",
  ]);
  expect(opencode.argv("p", "openrouter/x/y", "/ws", []).at(-1)).toBe("openrouter/x/y");
});

test("runEnv creates the per-run home and config root", () => {
  const run = join(box.root, "run");
  expect(opencode.runEnv(run, {})).toEqual({ HOME: join(run, "home"), OPENCODE_CONFIG_DIR: join(run, "oc-config") });
  expect(existsSync(join(run, "oc-config"))).toBe(true);
});

test("plugins and badly named skills cannot be hosted", () => {
  expect(opencode.canHost(loadCandidate("p", dir("p", { ".claude-plugin/plugin.json": "{}" })))).toBe(false);
  expect(opencode.canHost(loadCandidate("s", dir("good-skill-2", { "SKILL.md": "x" })))).toBe(true);
  expect(opencode.canHost(loadCandidate("s", dir("Bad_Skill", { "SKILL.md": "x" })))).toBe(false);
  expect(opencode.canHost(loadCandidate("s", dir("a".repeat(65), { "SKILL.md": "x" })))).toBe(false);
  expect(opencode.canHost(loadCandidate("a", dir("agents", { "a.md": "x" })))).toBe(true);
});

test("a skill is copied under oc-config/skills with a permission config", async () => {
  const c = loadCandidate("mermaid", dir("mermaid", { "SKILL.md": "skill" }));
  expect(await opencode.inject(c, ctx())).toEqual({ args: [] });
  const config = join(ctx().runDir, "oc-config");
  expect(readFileSync(join(config, "skills/mermaid/SKILL.md"), "utf8")).toBe("skill");
  expect(readFileSync(join(config, "opencode.json"), "utf8")).toBe(
    '{"$schema":"https://opencode.ai/config.json","permission":{"skill":{"mermaid":"allow"}}}',
  );
});

test("agents are translated into oc-config/agents with a bare config", async () => {
  const c = loadCandidate("a", dir("a", { "scout.md": SCOUT }));
  await opencode.inject(c, ctx());
  const config = join(ctx().runDir, "oc-config");
  expect(readFileSync(join(config, "agents/scout.md"), "utf8")).toBe(`---
description: "Read-only investigator. Use before changing unfamiliar code."
mode: subagent
permission:
  edit: deny
  bash: deny
  glob: allow
  grep: allow
  read: allow
---
You are a scout. Report what you find with file paths and line numbers.
`);
  expect(readFileSync(join(config, "opencode.json"), "utf8")).toBe('{"$schema":"https://opencode.ai/config.json"}');
});

test("agent translation: model rules and tool mapping", () => {
  const t = (fm: string) => translateAgent(parseAgent("x.md", `---\n${fm}\n---\nBody`));
  expect(t("model: claude-haiku-4-5")).toContain("\nmodel: anthropic/claude-haiku-4-5\n");
  expect(t("model: openrouter/qwen")).toContain("\nmodel: openrouter/qwen\n");
  for (const alias of ["haiku", "sonnet", "opus", "inherit"]) expect(t(`model: ${alias}`)).not.toContain("model:");
  expect(t("description: x")).not.toContain("permission:");
  expect(t("tools: Bash Write,WebFetch, Task")).toContain("permission:\n  bash: allow\n  edit: allow\n  webfetch: allow\n---");
  expect(t("tools: Task")).toContain("permission:\n  edit: deny\n  bash: deny\n---");
});

test("A4 folds the captured run", () => {
  const r = opencode.fold(stream("A4-opencode-captured.jsonl"));
  expect(r).toMatchObject({ result: "OK", num_turns: 1, tool_names: [], skill_used: false, cost_usd: null, input_tokens: null, output_tokens: null, cache_read_tokens: null, cache_creation_tokens: null, event_error: null, plugins: null, plugin_errors: [] });
  expect(opencode.succeeded(0, r)).toBe(true);
});

test("A5 sums step_finish cost and tokens", () => {
  const r = opencode.fold(stream("A5-opencode-skill-trial.jsonl"));
  expect(r).toMatchObject({
    tool_names: ["skill", "read"],
    skill_used: true,
    num_turns: 2,
    result: "Added the diagram.",
    cost_usd: 0.014100000000000001,
    input_tokens: 55,
    output_tokens: 354,
    cache_read_tokens: 32490,
    cache_creation_tokens: 14290,
  });
});

test("A6 yields the error event's message; exit 0 still succeeds", () => {
  const r = opencode.fold(stream("A6-opencode-error.jsonl"));
  expect(r.event_error).toBe("invalid x-api-key");
  expect(r.plugin_errors).toEqual([]);
  expect(opencode.succeeded(1, r)).toBe(false);
  expect(opencode.succeeded(0, r)).toBe(true);
  const fallbacks = [
    ['{"type":"error","error":{"message":"m1"}}', "m1"],
    ['{"type":"error","part":{"message":"m2"}}', "m2"],
    ['{"type":"error","message":"m3"}', "m3"],
    ['{"type":"error","error":{"name":"N"}}', "N"],
    ['{"type":"error","error":"plain"}', "plain"],
    ['{"type":"error"}', "opencode reported an error event"],
    ['{"type":"error","message":"first"}\n{"type":"error","message":"last"}', "last"],
  ];
  for (const [s, want] of fallbacks) expect(opencode.fold(s!).event_error).toBe(want!);
});
