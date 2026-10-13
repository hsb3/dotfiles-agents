import { afterEach, beforeEach, expect, test } from "bun:test";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { claude } from "../src/claude.ts";
import { loadCandidate } from "../src/candidate.ts";
import { sandbox, STREAMS } from "./helpers/stubs.ts";

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

const ctx = () => ({ runDir: join(box.root, "run"), ws: join(box.root, "run", "ws"), env: {} });

test("argv follows the spec, with injection flags before --model and no --bare", () => {
  const argv = claude.argv("do it", "claude-sonnet-4-5", "/ws", ["--plugin-dir", "/p"]);
  expect(argv).toEqual([
    "claude", "-p", "do it", "--output-format", "stream-json", "--verbose", "--permission-mode", "acceptEdits",
    "--allowedTools", "Skill,Task,Bash,Edit,Read,Write,Grep,Glob", "--setting-sources", "", "--strict-mcp-config",
    "--plugin-dir", "/p", "--model", "claude-sonnet-4-5",
  ]);
  expect(argv).not.toContain("--bare");
});

test("runEnv creates the per-run home and config dir and sets the betas variable", () => {
  const run = join(box.root, "run");
  expect(claude.runEnv(run, {})).toEqual({ HOME: join(run, "home"), CLAUDE_CONFIG_DIR: join(run, "claude-config"), CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS: "1" });
  expect(existsSync(join(run, "home"))).toBe(true);
  expect(existsSync(join(run, "claude-config"))).toBe(true);
});

test("a plugin is injected with --plugin-dir on the candidate dir", async () => {
  const c = loadCandidate("p", dir("p", { ".claude-plugin/plugin.json": "{}" }));
  expect(await claude.inject(c, ctx())).toEqual({ args: ["--plugin-dir", c.dir] });
});

test("a skill is wrapped in a synthetic eval-<skill> plugin", async () => {
  const c = loadCandidate("mermaid", dir("mermaid", { "SKILL.md": "skill", "ref/x.md": "r" }));
  const plugin = join(ctx().runDir, "plugin");
  expect(await claude.inject(c, ctx())).toEqual({ args: ["--plugin-dir", plugin] });
  expect(readFileSync(join(plugin, ".claude-plugin/plugin.json"), "utf8")).toBe(
    '{"name":"eval-mermaid","version":"0.0.0","description":"eval-harness wrapper for skill candidate mermaid"}',
  );
  expect(readFileSync(join(plugin, "skills/mermaid/SKILL.md"), "utf8")).toBe("skill");
  expect(readFileSync(join(plugin, "skills/mermaid/ref/x.md"), "utf8")).toBe("r");
});

test("agents are injected as --agents JSON, one entry per file", async () => {
  const c = loadCandidate("a", dir("a", { "scout.md": "---\nname: scout\ndescription: Looks.\n---\nYou scout.", "b.md": "Body B" }));
  expect(await claude.inject(c, ctx())).toEqual({
    args: ["--agents", '{"b":{"description":"Body B","prompt":"Body B"},"scout":{"description":"Looks.","prompt":"You scout."}}'],
  });
});

test("A1 folds to an API error with two plugins and zero metrics", () => {
  const r = claude.fold(stream("A1-claude-api-error.jsonl"));
  expect((r.plugins as { name: string }[]).map((p) => p.name)).toEqual(["eval-demo-skill", "cc-plugin-agents-md"]);
  expect(r).toMatchObject({ plugin_errors: [], tool_names: [], skill_used: false, cost_usd: 0, duration_ms: 407, num_turns: 1 });
  expect([r.input_tokens, r.output_tokens, r.cache_read_tokens, r.cache_creation_tokens]).toEqual([0, 0, 0, 0]);
  expect(r.event_error).toBe("API Error: 400 The requested features are not available for HIPAA-configured organizations: context_management.");
  expect(claude.succeeded(1, r)).toBe(false);
});

test("A2 folds to a successful skill trial", () => {
  const r = claude.fold(stream("A2-claude-skill-trial.jsonl"));
  expect(r).toMatchObject({
    tool_names: ["Read", "Skill", "Edit"],
    skill_used: true,
    result: "Added the diagram to README.md.",
    cost_usd: 0.19766235,
    duration_ms: 44168,
    num_turns: 12,
    input_tokens: 36,
    output_tokens: 1964,
    cache_read_tokens: 105942,
    cache_creation_tokens: 36157,
    plugin_errors: [],
    event_error: null,
  });
  expect(claude.succeeded(0, r)).toBe(true);
});

test("A3 carries the plugin error verbatim", () => {
  const r = claude.fold(stream("A3-claude-plugin-error.jsonl"));
  expect(r.plugin_errors).toEqual([{ plugin: "eval-x", message: "boom" }]);
  expect(r.plugins).toEqual([]);
  expect(claude.succeeded(0, r)).toBe(true);
});
