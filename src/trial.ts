// One trial: run dir and workspace, injection, the agent run and its log, the
// fold, check.py and the grader, the pass rule, and the ledger row. The agent
// run itself is shared with the smoke check.
import { cpSync, mkdirSync, mkdtempSync, realpathSync, rmSync, writeFileSync } from "node:fs";
import { randomBytes } from "node:crypto";
import { tmpdir } from "node:os";
import { dirname, join, relative, resolve, sep } from "node:path";
import type { Candidate } from "./candidate.ts";
import type { Case } from "./cases.ts";
import { runChecks } from "./checks.ts";
import { grade } from "./grader.ts";
import { adapterFor, authEnvPresent, childEnv, type Adapter, type Harness, type TrialRecord } from "./harnesses.ts";
import { appendRow, pythonJson, type Entry, type Preconditions, type Row } from "./ledger.ts";
import { runProcess, type Env, type RunResult } from "./subprocess.ts";

export type Config = "with" | "baseline";

const pad = (n: number, w = 2) => String(n).padStart(w, "0");

/** Local time as `YYYY-MM-DDTHH:MM:SS`. */
export function localTs(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

/** Local time as `YYYYMMDD-HHMMSS`, for log names. */
export function logStamp(d: Date): string {
  return localTs(d).replace(/-/g, "").replace("T", "-").replace(/:/g, "");
}

/** 32 random lowercase hex characters. */
export function randomHex(): string {
  return randomBytes(16).toString("hex");
}

/** A fresh run dir `<tmp>/harness-<label>-<random>/` with `ws/` copied from the fixture or empty. */
export function makeRunDir(label: string, fixture: string | null): { runDir: string; ws: string } {
  // Real path, so the recorded workspace is the directory the agent sees as its cwd.
  const runDir = realpathSync(mkdtempSync(join(tmpdir(), `harness-${label}-`)));
  const ws = join(runDir, "ws");
  if (fixture) cpSync(fixture, ws, { recursive: true });
  else mkdirSync(ws);
  return { runDir, ws };
}

export interface AgentRunRequest {
  adapter: Adapter;
  /** The candidate to inject, or null for a baseline run. */
  candidate: Candidate | null;
  runDir: string;
  ws: string;
  prompt: string;
  model: string;
  timeoutSec: number;
  baseEnv: Env | NodeJS.ProcessEnv;
}

export type AgentRun =
  | { kind: "injection-failure"; failure: string; exitCode: number }
  | { kind: "ran"; env: Env; run: RunResult; record: TrialRecord };

/** Injects (for a candidate) and runs the agent CLI in the workspace, then folds its stdout. */
export async function runAgent(req: AgentRunRequest): Promise<AgentRun> {
  const { adapter } = req;
  const env = childEnv(adapter, req.runDir, req.baseEnv);
  let injected: string[] = [];
  if (req.candidate) {
    const injection = await adapter.inject(req.candidate, { runDir: req.runDir, ws: req.ws, env });
    if ("failure" in injection) return { kind: "injection-failure", failure: injection.failure, exitCode: injection.exitCode };
    injected = injection.args;
  }
  const argv = adapter.argv(req.prompt, req.model, req.ws, injected);
  const run = await runProcess(argv, { cwd: req.ws, env, timeoutSec: req.timeoutSec });
  const record = adapter.fold(run.stdout);
  if (adapter.wallClockDuration) record.duration_ms = run.durationMs;
  return { kind: "ran", env, run, record };
}

/** The row's `error` for an agent run. */
export function errorField(adapter: Adapter, run: RunResult, record: TrialRecord, timeoutSec: number): string | null {
  if (run.timedOut) return `timeout after ${timeoutSec}s`;
  if (run.notFound) return `executable not found: ${adapter.exe}`;
  if (run.exitCode !== 0) {
    const stderr = run.stderr.trimEnd();
    if (stderr) return stderr.slice(-2000);
    return record.event_error ?? `exit ${run.exitCode}`;
  }
  return record.event_error;
}

const INSTALL_PATTERNS = [
  "npm install", "npm i ", "npx playwright install", "playwright install", "pnpm add", "yarn add", "bun add",
  "pip install", "pip3 install", "uv add", "uv pip install", "brew install", "apt-get install", "cargo install", "go install",
];

/** Stdout lines that look like the agent installing something, trimmed, cut, deduplicated, sorted, capped. */
export function selfInstalls(stdout: string): string[] {
  const found = new Set<string>();
  for (const line of stdout.split("\n")) {
    if (INSTALL_PATTERNS.some((p) => line.includes(p))) found.add(line.trim().slice(0, 120));
  }
  return [...found].sort().slice(0, 20);
}

export interface TrialSpec {
  harness: Harness;
  model: string;
  candidate: Candidate;
  kase: Case;
  config: Config;
  trial: number;
  campaign: string;
  graderModel: string;
  timeoutSec: number;
  keepWorkspaces: boolean;
  resultsPath: string;
  runsDir: string;
  cliVersion: string;
  baseEnv: Env | NodeJS.ProcessEnv;
}

function preconditions(spec: TrialSpec, installs: string[]): Preconditions {
  return {
    auth_env_present: authEnvPresent(spec.baseEnv),
    campaign: spec.campaign,
    cli_version: spec.cliVersion,
    grader_model: spec.graderModel,
    harness: spec.harness,
    model: spec.model,
    network_assumption: "assumed-available",
    self_installs: installs,
    timeout: spec.timeoutSec,
  };
}

function baseRow(spec: TrialSpec, ts: string): Row {
  return {
    ts,
    campaign: spec.campaign,
    harness: spec.harness,
    model: spec.model,
    candidate: spec.candidate.name,
    case: spec.kase.id,
    config: spec.config,
    trial: spec.trial,
    kind: spec.candidate.kind,
    grader_model: null,
    passed: null,
    checks: [],
    grades: [],
    skill_used: false,
    tool_names: [],
    plugin_errors: [],
    exit_code: null,
    error: null,
    cost_usd: null,
    duration_ms: null,
    num_turns: null,
    input_tokens: null,
    output_tokens: null,
    cache_read_tokens: null,
    cache_creation_tokens: null,
    workspace: null,
    log_path: null,
    cli_version: spec.cliVersion,
    preconditions: preconditions(spec, []),
  };
}

function writeLog(spec: TrialSpec, started: Date, header: Preconditions, stdout: string): string {
  mkdirSync(spec.runsDir, { recursive: true });
  const name = `${spec.harness}-${spec.candidate.name}-${spec.kase.id}-${spec.config}-${spec.trial}-${logStamp(started)}-${randomHex()}.log`;
  const path = join(spec.runsDir, name);
  writeFileSync(path, `# preconditions: ${pythonJson(header)}\n${stdout}`);
  return path;
}

/** The log path relative to the ledger's directory, `/`-separated. */
export function ledgerRelative(resultsPath: string, logPath: string): string {
  return relative(dirname(resolve(resultsPath)), resolve(logPath)).split(sep).join("/");
}

/** Runs one trial, appends its row to the ledger and returns the row. */
export async function runTrial(spec: TrialSpec): Promise<Row> {
  const started = new Date();
  const adapter = adapterFor(spec.harness);
  const row = baseRow(spec, localTs(started));
  const label = `${spec.harness}-${spec.candidate.name}-${spec.kase.id}-${spec.config}-${spec.trial}`;
  const { runDir, ws } = makeRunDir(label, spec.kase.fixture);
  const finish = (r: Row, keep: boolean): Row => {
    if (keep) r.workspace = ws;
    else rmSync(runDir, { recursive: true, force: true });
    appendRow(spec.resultsPath, r);
    return r;
  };

  if (!adapter.canHost(spec.candidate)) {
    row.error = `unsupported: ${spec.harness} cannot host kind=${spec.candidate.kind}`;
    return finish(row, false);
  }

  const agent = await runAgent({
    adapter,
    candidate: spec.config === "with" ? spec.candidate : null,
    runDir,
    ws,
    prompt: spec.kase.prompt,
    model: spec.model,
    timeoutSec: spec.timeoutSec,
    baseEnv: spec.baseEnv,
  });
  if (agent.kind === "injection-failure") {
    Object.assign(row, { passed: false, plugin_errors: [agent.failure], error: agent.failure, exit_code: agent.exitCode });
    return finish(row, true);
  }

  const { run, record, env } = agent;
  const pre = preconditions(spec, selfInstalls(run.stdout));
  const logPath = writeLog(spec, started, pre, run.stdout);
  const checks: Entry[] = spec.kase.check ? await runChecks(spec.kase.check, ws, env) : [];
  const hasAssertions = spec.kase.assertions.length > 0;
  const grades: Entry[] = hasAssertions
    ? await grade({
        runDir,
        ws,
        result: record.result,
        assertions: spec.kase.assertions,
        model: spec.graderModel,
        timeoutSec: spec.timeoutSec,
        baseEnv: spec.baseEnv,
      })
    : [];
  const passed =
    adapter.succeeded(run.exitCode, record) &&
    !(spec.config === "with" && record.plugin_errors.length > 0) &&
    [...checks, ...grades].every((e) => e.passed === true);
  Object.assign(row, {
    grader_model: hasAssertions ? spec.graderModel : null,
    passed,
    checks,
    grades,
    skill_used: record.skill_used,
    tool_names: record.tool_names,
    plugin_errors: record.plugin_errors,
    exit_code: run.exitCode,
    error: errorField(adapter, run, record, spec.timeoutSec),
    cost_usd: record.cost_usd,
    duration_ms: record.duration_ms,
    num_turns: record.num_turns,
    input_tokens: record.input_tokens,
    output_tokens: record.output_tokens,
    cache_read_tokens: record.cache_read_tokens,
    cache_creation_tokens: record.cache_creation_tokens,
    log_path: ledgerRelative(spec.resultsPath, logPath),
    preconditions: pre,
  });
  return finish(row, !passed || spec.keepWorkspaces);
}
