import { afterEach, beforeEach, expect, test } from "bun:test";
import { chmodSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { adapterFor, authEnvPresent, childEnv, cliVersion, jsonLines, parseHarnessList, preflight, scrubEnv, UnknownHarness } from "../src/harnesses.ts";
import { installStub, sandbox } from "./helpers/stubs.ts";

let box: ReturnType<typeof sandbox>;
beforeEach(() => {
  box = sandbox();
});
afterEach(() => box.cleanup());

test("harness lists keep order and drop duplicates; unknown names fail with the spec message", () => {
  expect(parseHarnessList("codex,claude,codex,opencode")).toEqual(["codex", "claude", "opencode"]);
  expect(() => parseHarnessList("claude,gemini")).toThrow(new UnknownHarness("unknown harness 'gemini'; valid harnesses: claude, codex, opencode"));
});

test("the claude adapter's default model and executable", () => {
  expect(adapterFor("claude")).toMatchObject({ exe: "claude", defaultModel: "claude-sonnet-4-5" });
});

test("auth env lists sorted names of set, non-empty variables only", () => {
  expect(authEnvPresent({ OPENAI_API_KEY: "x", ANTHROPIC_API_KEY: "y", GROQ_API_KEY: "", OTHER_KEY: "z" })).toEqual([
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
  ]);
});

test("scrubbing removes the prefix and the four XDG variables only", () => {
  const env = scrubEnv(
    { CLAUDECODE: "1", CLAUDE_CODE_SSE_PORT: "1", CLAUDE_CONFIG_DIR: "/real", XDG_CONFIG_HOME: "x", XDG_DATA_HOME: "x", XDG_CACHE_HOME: "x", XDG_STATE_HOME: "x", XDG_RUNTIME_DIR: "keep", ANTHROPIC_API_KEY: "k", PATH: "/bin" },
    "CLAUDE",
  );
  expect(env).toEqual({ XDG_RUNTIME_DIR: "keep", ANTHROPIC_API_KEY: "k", PATH: "/bin" });
});

test("childEnv overlays the adapter's per-run values on the scrubbed environment", () => {
  const run = join(box.root, "run");
  const env = childEnv(adapterFor("claude"), run, { HOME: "/Users/real", CLAUDE_CONFIG_DIR: "/real", PATH: "/bin" });
  expect(env).toEqual({ HOME: join(run, "home"), CLAUDE_CONFIG_DIR: join(run, "claude-config"), CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS: "1", PATH: "/bin" });
});

test("preflight reports a missing CLI", () => {
  expect(preflight("claude", { PATH: box.bin })).toBe("claude: CLI not found on PATH");
  installStub(box.bin, "claude", [{}]);
  expect(preflight("claude", { PATH: box.bin })).toBeNull();
});

test("cliVersion trims stdout, says unknown when empty and unavailable when missing", async () => {
  installStub(box.bin, "claude", [{ prefix: ["--version"], stdout: "  2.1.296 (Claude Code)\n" }]);
  expect(await cliVersion("claude", { PATH: box.bin })).toBe("2.1.296 (Claude Code)");
  installStub(box.bin, "claude", [{ prefix: ["--version"], stdout: "\n" }]);
  expect(await cliVersion("claude", { PATH: box.bin })).toBe("unknown");
  expect(await cliVersion("claude", { PATH: join(box.root, "nothing") })).toBe("unavailable");
});

test("jsonLines keeps JSON objects and skips every other line", () => {
  expect(jsonLines('{"a":1}\nnot json\n[1]\n"s"\n\n{"b":2}')).toEqual([{ a: 1 }, { b: 2 }]);
});
