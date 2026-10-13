// The loadability check: inject the candidate into an empty workspace, ask for
// `OK`, and report what the CLI loaded. No cases, no grading, no ledger row.
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { loadCandidate, type Candidate } from "./candidate.ts";
import type { Io, RunOptions } from "./commands.ts";
import { cells } from "./grid.ts";
import { adapterFor, preflight, type Harness } from "./harnesses.ts";
import { errorField, logStamp, makeRunDir, randomHex, runAgent } from "./trial.ts";

export const SMOKE_PROMPT = "Reply with exactly: OK";

const compact = (v: unknown) => (typeof v === "string" ? v : JSON.stringify(v));

function pluginNames(plugins: unknown[] | null): string {
  if (!plugins || plugins.length === 0) return "(none)";
  return plugins
    .map((p) => (typeof p === "object" && p !== null && typeof (p as { name?: unknown }).name === "string" ? (p as { name: string }).name : compact(p)))
    .join(", ");
}

/** Runs one smoke cell, printing its block; returns whether it passed. */
async function smokeCell(opts: RunOptions, candidate: Candidate, harness: Harness, model: string, io: Io): Promise<boolean> {
  const adapter = adapterFor(harness);
  io.out(`harness: ${harness}`);
  io.out(`kind: ${candidate.kind}`);
  if (!adapter.canHost(candidate)) {
    io.out(`∅ ${harness} cannot host kind=${candidate.kind} — skip`);
    return false;
  }
  const { runDir, ws } = makeRunDir(`${harness}-${candidate.name}-smoke`, null);
  try {
    const started = new Date();
    const agent = await runAgent({
      adapter,
      candidate,
      runDir,
      ws,
      prompt: SMOKE_PROMPT,
      model,
      timeoutSec: opts.timeoutSec,
      baseEnv: process.env,
    });
    let pluginErrors: unknown[];
    let exitCode: number;
    let error: string | null;
    if (agent.kind === "injection-failure") {
      io.out("plugins loaded: (not reported)");
      pluginErrors = [agent.failure];
      exitCode = agent.exitCode;
      error = agent.failure;
    } else {
      mkdirSync(opts.runsDir, { recursive: true });
      const log = join(opts.runsDir, `${harness}-smoke-${candidate.name}-${logStamp(started)}-${randomHex()}.log`);
      writeFileSync(log, agent.run.stdout);
      io.out(`plugins loaded: ${adapter.reportsPlugins ? pluginNames(agent.record.plugins) : "(not reported)"}`);
      pluginErrors = agent.record.plugin_errors;
      exitCode = agent.run.exitCode;
      error = errorField(adapter, agent.run, agent.record, opts.timeoutSec);
    }
    for (const e of pluginErrors) io.out(`✗ plugin_error: ${compact(e)}`);
    if (exitCode !== 0) io.out(`✗ exit ${exitCode}: ${(error ?? "").slice(0, 400)}`);
    const ok = pluginErrors.length === 0 && exitCode === 0;
    io.out(ok ? "✓ loadability OK" : "✗ loadability FAILED");
    return ok;
  } finally {
    rmSync(runDir, { recursive: true, force: true });
  }
}

/** Smoke-checks the candidate in every cell; 0 when at least one cell ran and all that ran passed. */
export async function runSmoke(opts: RunOptions, io: Io): Promise<number> {
  let candidate: Candidate;
  try {
    candidate = loadCandidate(opts.candidate, opts.candidateDir ?? "");
  } catch (e) {
    io.err((e as Error).message);
    return 2;
  }
  let ran = 0;
  let failed = 0;
  try {
    for (const { harness, model } of cells(opts)) {
      const why = preflight(harness, process.env);
      if (why) {
        io.err(why);
        continue;
      }
      if (ran > 0) io.out("");
      ran++;
      if (!(await smokeCell(opts, candidate, harness, model, io))) failed++;
    }
  } finally {
    candidate.cleanup();
  }
  return ran > 0 && failed === 0 ? 0 : 1;
}
