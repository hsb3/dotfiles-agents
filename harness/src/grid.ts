// The grid for one candidate: every (harness, model) cell that passes
// preflight runs every case × config × trial not already in the ledger.
import { loadCandidate, type Candidate } from "./candidate.ts";
import { loadCases, type Case } from "./cases.ts";
import type { Io, RunOptions } from "./commands.ts";
import { adapterFor, authEnvPresent, cliVersion, preflight, type Harness } from "./harnesses.ts";
import { doneKeys, resumeKey } from "./ledger.ts";
import { report } from "./report.ts";
import { runTrial } from "./trial.ts";

/** The (harness, model) cells, harness-major, with each harness's default model when none is given. */
export function cells(opts: RunOptions): { harness: Harness; model: string }[] {
  return opts.harnesses.flatMap((harness) =>
    (opts.models ?? [adapterFor(harness).defaultModel]).map((model) => ({ harness, model })),
  );
}

export function preconditionsLine(opts: RunOptions, harness: Harness, model: string, version: string): string {
  const auth = authEnvPresent(process.env);
  return [
    `preconditions: harness=${harness}`,
    `cli=${version}`,
    `campaign=${opts.campaign || "(none)"}`,
    `model=${model}`,
    `grader=${opts.graderModel}`,
    `timeout=${opts.timeoutSec}s`,
    `auth_env=${auth.length ? auth.join(",") : "(none)"}`,
    "network=assumed-available",
  ].join(" · ");
}

const MARKS = { true: "✓", false: "✗", null: "∅" } as const;

async function runCell(opts: RunOptions, candidate: Candidate, cases: Case[], harness: Harness, model: string, io: Io): Promise<void> {
  const version = await cliVersion(harness, process.env);
  io.out(preconditionsLine(opts, harness, model, version));
  const done = doneKeys(opts.results);
  let ran = 0;
  let skipped = 0;
  for (const kase of cases) {
    for (const config of opts.configs) {
      for (let trial = 0; trial < opts.trials; trial++) {
        const key = { campaign: opts.campaign, harness, model, candidate: candidate.name, case: kase.id, config, trial };
        if (done.has(resumeKey(key))) {
          skipped++;
          continue;
        }
        const row = await runTrial({
          harness,
          model,
          candidate,
          kase,
          config,
          trial,
          campaign: opts.campaign,
          graderModel: opts.graderModel,
          timeoutSec: opts.timeoutSec,
          keepWorkspaces: opts.keepWorkspaces,
          resultsPath: opts.results,
          runsDir: opts.runsDir,
          cliVersion: version,
          baseEnv: process.env,
        });
        ran++;
        io.out(`${MARKS[String(row.passed) as keyof typeof MARKS]} ${harness} ${kase.id} ${config} trial ${trial}`);
      }
    }
  }
  io.out("");
  io.out(`${ran} trial(s) run, ${skipped} skipped (already in ${opts.resultsShown})`);
  io.out(report(candidate.name, opts.results));
}

/** Loads the candidate and its cases, then runs every cell; returns the exit code. */
export async function runCandidate(opts: RunOptions, io: Io): Promise<number> {
  let candidate: Candidate;
  let cases: Case[];
  try {
    candidate = loadCandidate(opts.candidate, opts.candidateDir ?? "");
  } catch (e) {
    io.err((e as Error).message);
    return 2;
  }
  try {
    cases = loadCases(opts.casesDir, opts.candidate, opts.caseId);
  } catch (e) {
    candidate.cleanup();
    io.err((e as Error).message);
    return 2;
  }
  let anyPassed = false;
  try {
    for (const { harness, model } of cells(opts)) {
      const why = preflight(harness, process.env);
      if (why) {
        io.err(why);
        continue;
      }
      anyPassed = true;
      await runCell(opts, candidate, cases, harness, model, io);
    }
  } finally {
    candidate.cleanup();
  }
  return anyPassed ? 0 : 1;
}
