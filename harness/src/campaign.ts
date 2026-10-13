// The weekly campaign: every cased candidate runs the grid under one dated
// label, then each gets its report. Everything printed is also appended to
// the campaign log.
import { appendFileSync, mkdirSync, readdirSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import type { Io, RunOptions } from "./commands.ts";
import { runCandidate } from "./grid.ts";
import { report } from "./report.ts";
import { localTs } from "./trial.ts";

const NOT_CANDIDATES = ["_template", "smoke-echo"];

/** The kind of entry at `path` (following symlinks), or null when there is none. */
function entryKind(path: string): "dir" | "file" | "other" | null {
  const st = statSync(path, { throwIfNoEntry: false });
  if (!st) return null;
  return st.isDirectory() ? "dir" : st.isFile() ? "file" : "other";
}

function subdirs(dir: string): string[] {
  if (entryKind(dir) !== "dir") return [];
  return readdirSync(dir)
    .filter((name) => entryKind(join(dir, name)) === "dir")
    .sort();
}

/** The candidates: subdirectory names of the cases dir, sorted, minus the shipped ones. */
export function discoverCandidates(casesDir: string): string[] {
  return subdirs(casesDir).filter((name) => !NOT_CANDIDATES.includes(name));
}

/** The first `<root>/*\/<name>/` directory in sorted order, else `<root>/agents/<name>.md`, else null. */
export function resolveCandidatePath(root: string, name: string): string | null {
  for (const group of subdirs(root)) {
    const dir = join(root, group, name);
    if (entryKind(dir) === "dir") return dir;
  }
  const flat = join(root, "agents", `${name}.md`);
  return entryKind(flat) === "file" ? flat : null;
}

/** An Io that also appends every line to the campaign log. */
function teeIo(io: Io, logPath: string): Io {
  mkdirSync(dirname(logPath), { recursive: true });
  const log = (line: string) => appendFileSync(logPath, line + "\n");
  return {
    out: (line) => {
      io.out(line);
      log(line);
    },
    err: (line) => {
      io.err(line);
      log(line);
    },
  };
}

function dryRunLine(opts: RunOptions, name: string, path: string): string {
  const model = opts.models ? ` --model ${opts.models.join(",")}` : "";
  return (
    `DRYRUN: agent-harness ${name} --candidate-dir ${path} --cases-dir ${opts.casesDir} --harness ${opts.harnesses.join(",")}` +
    ` --configs ${opts.configs.join(",")} --trials ${opts.trials} --campaign ${opts.campaign}${model}`
  );
}

/** Runs the campaign; 0 when every candidate's run exited 0, else 1. */
export async function runCampaign(opts: RunOptions, candidatesRoot: string, dryRun: boolean, io: Io): Promise<number> {
  const names = discoverCandidates(opts.casesDir);
  if (names.length === 0) {
    io.err(`no candidates discovered under ${opts.casesDir}`);
    return 1;
  }
  const label = opts.campaign;
  const logPath = join(dirname(opts.results), "campaign-logs", `${label}.log`);
  const tee = dryRun ? io : teeIo(io, logPath);
  tee.out(`=== campaign ${label} @ ${localTs(new Date()).replace("T", " ")} ===`);
  tee.out(`candidates: ${names.join(" ")}`);
  let failed = 0;
  for (const name of names) {
    const path = resolveCandidatePath(candidatesRoot, name);
    if (path === null) {
      tee.err(`WARN: no candidate named '${name}' under ${candidatesRoot}`);
      failed++;
      continue;
    }
    if (dryRun) {
      tee.out(dryRunLine(opts, name, path));
      tee.out(`DRYRUN: agent-harness ${name} --report`);
      continue;
    }
    const code = await runCandidate({ ...opts, candidate: name, candidateDir: path }, tee);
    if (code !== 0) {
      tee.err(`FAILED: candidate '${name}' exited ${code}`);
      failed++;
    }
  }
  if (!dryRun) {
    for (const name of names) {
      tee.out(`=== report: ${name} ===`);
      tee.out(report(name, opts.results));
    }
  }
  const outcome = failed === 0 ? "ok" : `${failed} failed`;
  tee.out(`campaign '${label}' complete: ${outcome}${dryRun ? "" : ` (log: ${logPath})`}`);
  return failed === 0 ? 0 : 1;
}
