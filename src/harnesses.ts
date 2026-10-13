// The three harnesses: their names, default models, preflight, CLI version,
// the scrubbed child environment, and the adapter each one runs through.
import type { Candidate } from "./candidate.ts";
import { claude } from "./claude.ts";
import { codex } from "./codex.ts";
import { opencode } from "./opencode.ts";
import { findExecutable, runProcess, type Env } from "./subprocess.ts";

export type Harness = "claude" | "opencode" | "codex";

export const HARNESS_NAMES: readonly Harness[] = ["claude", "codex", "opencode"];

export const AUTH_ENV_NAMES = [
  "ANTHROPIC_API_KEY",
  "OPENAI_API_KEY",
  "GEMINI_API_KEY",
  "GOOGLE_GENERATIVE_AI_API_KEY",
  "OPENROUTER_API_KEY",
  "GROQ_API_KEY",
] as const;

const XDG_VARS = ["XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"];

/** What a fold makes of an agent's stdout. */
export interface TrialRecord {
  result: string | null;
  tool_names: string[];
  skill_used: boolean;
  /** Loaded plugins, as the CLI reports them (claude only). */
  plugins: unknown[] | null;
  plugin_errors: unknown[];
  cost_usd: number | null;
  duration_ms: number | null;
  num_turns: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
  cache_read_tokens: number | null;
  cache_creation_tokens: number | null;
  event_error: string | null;
}

export function emptyRecord(): TrialRecord {
  return {
    result: null,
    tool_names: [],
    skill_used: false,
    plugins: null,
    plugin_errors: [],
    cost_usd: null,
    duration_ms: null,
    num_turns: null,
    input_tokens: null,
    output_tokens: null,
    cache_read_tokens: null,
    cache_creation_tokens: null,
    event_error: null,
  };
}

/** Where injection writes and what it may run. */
export interface InjectContext {
  runDir: string;
  ws: string;
  env: Env;
}

export type Injection = { args: string[] } | { failure: string; exitCode: number };

/** How the harness runs one agent CLI: argv, isolation, injection and fold. */
export interface Adapter {
  harness: Harness;
  exe: string;
  defaultModel: string;
  /** Variables whose names start with this are removed from the child env. */
  scrubPrefix: string;
  /** Whether the CLI reports which plugins it loaded (smoke output). */
  reportsPlugins: boolean;
  /** Whether duration_ms is the harness's wall-clock time rather than the CLI's own. */
  wallClockDuration: boolean;
  canHost(candidate: Candidate): boolean;
  /** Creates the per-run homes and returns the per-run variables. */
  runEnv(runDir: string, base: Env): Env;
  /** Injects the candidate for a `with` run; returns the extra argv. */
  inject(candidate: Candidate, ctx: InjectContext): Promise<Injection>;
  argv(prompt: string, model: string, ws: string, injected: string[]): string[];
  fold(stdout: string): TrialRecord;
  succeeded(exitCode: number, record: TrialRecord): boolean;
}

export class UnknownHarness extends Error {}

export function isHarness(name: string): name is Harness {
  return (HARNESS_NAMES as readonly string[]).includes(name);
}

/** Splits a comma-separated harness list, keeping order and dropping duplicates and empty entries. */
export function parseHarnessList(value: string): Harness[] {
  const out: Harness[] = [];
  for (const raw of value.split(",")) {
    const name = raw.trim();
    if (name === "") continue;
    if (!isHarness(name)) {
      throw new UnknownHarness(`unknown harness '${name}'; valid harnesses: ${HARNESS_NAMES.join(", ")}`);
    }
    if (!out.includes(name)) out.push(name);
  }
  return out;
}

export function adapterFor(harness: Harness): Adapter {
  // Resolved at call time: the adapters import this module's helpers, so a
  // table built at load time could see an adapter before it is initialised.
  switch (harness) {
    case "claude":
      return claude;
    case "opencode":
      return opencode;
    case "codex":
      return codex;
  }
}

/** Names, never values, of the auth variables that are set and non-empty, sorted. */
export function authEnvPresent(env: Env | NodeJS.ProcessEnv): string[] {
  return AUTH_ENV_NAMES.filter((n) => !!env[n]).sort();
}

/** The harness's environment minus `prefix*` (when given) and the four XDG variables. */
export function scrubEnv(base: Env | NodeJS.ProcessEnv, prefix: string | null): Env {
  const env: Env = {};
  for (const [k, v] of Object.entries(base)) {
    if (v === undefined || (prefix !== null && k.startsWith(prefix)) || XDG_VARS.includes(k)) continue;
    env[k] = v;
  }
  return env;
}

/** The environment a CLI of this harness runs with inside `runDir`. */
export function childEnv(adapter: Adapter, runDir: string, base: Env | NodeJS.ProcessEnv): Env {
  const scrubbed = scrubEnv(base, adapter.scrubPrefix);
  return { ...scrubbed, ...adapter.runEnv(runDir, scrubbed) };
}

/** Why the cell cannot run, or null when it can. */
export function preflight(harness: Harness, env: Env | NodeJS.ProcessEnv): string | null {
  const adapter = adapterFor(harness);
  if (findExecutable(adapter.exe, { PATH: env.PATH ?? "" }) === null) return `${harness}: CLI not found on PATH`;
  if (harness === "opencode" && authEnvPresent(env).length === 0) {
    return `${harness}: no credentials — set one of ${AUTH_ENV_NAMES.join(", ")}`;
  }
  if (harness === "codex" && !env.OPENAI_API_KEY) return `${harness}: no credentials — set one of OPENAI_API_KEY`;
  return null;
}

/** Trimmed `<exe> --version` stdout; `unknown` when empty, `unavailable` when missing or slower than 30 s. */
export async function cliVersion(harness: Harness, env: Env | NodeJS.ProcessEnv): Promise<string> {
  const adapter = adapterFor(harness);
  const r = await runProcess([adapter.exe, "--version"], {
    cwd: process.cwd(),
    env: scrubEnv(env, adapter.scrubPrefix),
    timeoutSec: 30,
  });
  if (r.notFound || r.timedOut) return "unavailable";
  return r.stdout.trim() || "unknown";
}

/** The JSON objects of a JSONL stream; other lines are skipped. */
export function jsonLines(stdout: string): Record<string, any>[] {
  const events: Record<string, any>[] = [];
  for (const line of stdout.split("\n")) {
    if (!line.trim()) continue;
    try {
      const v = JSON.parse(line);
      if (typeof v === "object" && v !== null && !Array.isArray(v)) events.push(v);
    } catch {
      // Not an event line.
    }
  }
  return events;
}

/** The number at `value`, or null. */
export function num(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}
