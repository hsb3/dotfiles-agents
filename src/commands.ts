// The command line: parsing, validation in the spec's order (unknown harness
// names exit 3 before any bad input exits 2), defaults, and dispatch.
import { join, resolve } from "node:path";
import { runCampaign } from "./campaign.ts";
import { runCandidate } from "./grid.ts";
import { parseHarnessList, UnknownHarness, type Harness } from "./harnesses.ts";
import { report } from "./report.ts";
import { runSmoke } from "./smoke.ts";
import type { Config } from "./trial.ts";

/** Where command output goes; the campaign also copies it to its log. */
export interface Io {
  out(line: string): void;
  err(line: string): void;
}

export const consoleIo: Io = {
  out: (line) => process.stdout.write(line + "\n"),
  err: (line) => process.stderr.write(line + "\n"),
};

/** The directory holding the harness's package.json; defaults never depend on the cwd. */
export const PKG_DIR = resolve(import.meta.dir, "..");

export const DEFAULT_GRADER_MODEL = "claude-haiku-4-5-20251001";

export interface RunOptions {
  candidate: string;
  candidateDir: string | null;
  harnesses: Harness[];
  /** Models as typed, or null for each harness's default. */
  models: string[] | null;
  caseId: string | undefined;
  configs: Config[];
  trials: number;
  campaign: string;
  graderModel: string;
  timeoutSec: number;
  keepWorkspaces: boolean;
  casesDir: string;
  /** The ledger path, absolute. */
  results: string;
  /** The ledger path as given (or the default), for the summary line. */
  resultsShown: string;
  runsDir: string;
}

export const USAGE = `usage:
  agent-harness <candidate> --candidate-dir <path> [run flags]
  agent-harness <candidate> --candidate-dir <path> --smoke [--harness <list>] [--model <list>] [--timeout <s>] [--runs-dir <dir>]
  agent-harness <candidate> --report [--results <file>]
  agent-harness campaign --cases-dir <dir> --candidates-root <dir> [run flags] [--dry-run]
  agent-harness --help

run flags:
  --harness <list>        comma-separated claude, opencode, codex (default claude; campaign: claude,opencode,codex)
  --model <list>          comma-separated model ids (default: each harness's default model)
  --case <id>             run only this case id
  --configs <list>        with, baseline (default with,baseline)
  --trials <n>            trials per case x config (default 3)
  --campaign <label>      first segment of the resume key (default ""; campaign: weekly-<YYYYMMDD>)
  --grader-model <id>     grader model (default ${DEFAULT_GRADER_MODEL})
  --timeout <s>           per agent run and per grader run (default 600)
  --keep-workspaces       keep the run dirs of passing trials too
  --cases-dir <dir>       case datasets (default <pkg>/cases)
  --results <file>        the ledger (default <pkg>/results.jsonl)
  --runs-dir <dir>        per-trial logs (default <pkg>/runs)`;

const VALUE_FLAGS = [
  "--candidate-dir", "--harness", "--model", "--case", "--configs", "--trials", "--campaign", "--grader-model",
  "--timeout", "--cases-dir", "--results", "--runs-dir", "--candidates-root",
];
const BOOL_FLAGS = ["--smoke", "--report", "--keep-workspaces", "--dry-run", "--help"];
const CAMPAIGN_ONLY = ["--candidates-root", "--dry-run"];
const CANDIDATE_ONLY = ["--candidate-dir", "--smoke", "--report"];

class BadInput extends Error {}

interface Parsed {
  positionals: string[];
  flags: Map<string, string>;
  /** The first usage error met while reading argv, reported after the harness check. */
  usageError: string | null;
}

function tokenize(argv: string[]): Parsed {
  const parsed: Parsed = { positionals: [], flags: new Map(), usageError: null };
  const fail = (msg: string) => (parsed.usageError ??= msg);
  for (let i = 0; i < argv.length; i++) {
    const token = argv[i]!;
    if (!token.startsWith("--")) {
      parsed.positionals.push(token);
      continue;
    }
    const eq = token.indexOf("=");
    const flag = eq === -1 ? token : token.slice(0, eq);
    if (BOOL_FLAGS.includes(flag)) {
      if (eq !== -1) fail(`${flag} takes no value`);
      parsed.flags.set(flag, "");
    } else if (VALUE_FLAGS.includes(flag)) {
      const value = eq === -1 ? argv[++i] : token.slice(eq + 1);
      if (value === undefined) fail(`${flag} needs a value`);
      else parsed.flags.set(flag, value);
    } else {
      fail(`unknown flag ${flag}`);
    }
  }
  return parsed;
}

function positiveInt(flag: string, value: string | undefined, fallback: number): number {
  if (value === undefined) return fallback;
  if (!/^\d+$/.test(value) || Number(value) < 1) throw new BadInput(`${flag} must be an integer of at least 1, got '${value}'`);
  return Number(value);
}

function list(value: string): string[] {
  const out: string[] = [];
  for (const v of value.split(",").map((s) => s.trim())) if (v && !out.includes(v)) out.push(v);
  return out;
}

function parseConfigs(value: string | undefined): Config[] {
  const configs = list(value ?? "with,baseline");
  for (const c of configs) {
    if (c !== "with" && c !== "baseline") throw new BadInput(`unknown config '${c}'; valid configs: with, baseline`);
  }
  return configs as Config[];
}

function localDate(d: Date): string {
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}`;
}

/** The options shared by a candidate run and a campaign. */
export function runOptions(flags: Map<string, string>, candidate: string, isCampaign: boolean): RunOptions {
  const results = flags.get("--results");
  const defaultResults = join(PKG_DIR, "results.jsonl");
  const model = flags.get("--model");
  return {
    candidate,
    candidateDir: flags.get("--candidate-dir") ?? null,
    harnesses: parseHarnessList(flags.get("--harness") ?? (isCampaign ? "claude,opencode,codex" : "claude")),
    models: model === undefined ? null : list(model),
    caseId: flags.get("--case"),
    configs: parseConfigs(flags.get("--configs")),
    trials: positiveInt("--trials", flags.get("--trials"), 3),
    campaign: flags.get("--campaign") ?? (isCampaign ? `weekly-${localDate(new Date())}` : ""),
    graderModel: flags.get("--grader-model") ?? DEFAULT_GRADER_MODEL,
    timeoutSec: positiveInt("--timeout", flags.get("--timeout"), 600),
    keepWorkspaces: flags.has("--keep-workspaces"),
    casesDir: resolve(flags.get("--cases-dir") ?? join(PKG_DIR, "cases")),
    results: resolve(results ?? defaultResults),
    resultsShown: results ?? defaultResults,
    runsDir: resolve(flags.get("--runs-dir") ?? join(PKG_DIR, "runs")),
  };
}

/** Runs the command line and returns the exit code. */
export async function main(argv: string[], io: Io): Promise<number> {
  if (argv.length === 0) {
    io.err(USAGE);
    return 2;
  }
  const parsed = tokenize(argv);
  const { flags, positionals } = parsed;
  if (flags.has("--help")) {
    io.out(USAGE);
    return 0;
  }
  try {
    // 1. Harness names first.
    parseHarnessList(flags.get("--harness") ?? "");
    // 2. Then bad input.
    if (parsed.usageError) throw new BadInput(parsed.usageError);
    const [name, ...extra] = positionals;
    if (name === undefined) throw new BadInput("no candidate name");
    if (extra.length > 0) throw new BadInput(`unexpected argument '${extra[0]}'`);
    const isCampaign = name === "campaign";
    for (const flag of flags.keys()) {
      if (isCampaign ? CANDIDATE_ONLY.includes(flag) : CAMPAIGN_ONLY.includes(flag)) {
        throw new BadInput(`${flag} is not valid ${isCampaign ? "for campaign" : "outside campaign"}`);
      }
    }
    if (isCampaign) {
      const root = flags.get("--candidates-root");
      if (!flags.has("--cases-dir") || root === undefined) throw new BadInput("campaign needs --cases-dir and --candidates-root");
      return await runCampaign(runOptions(flags, name, true), resolve(root), flags.has("--dry-run"), io);
    }
    if (flags.has("--smoke") && flags.has("--report")) throw new BadInput("--smoke and --report cannot be combined");
    const opts = runOptions(flags, name, false);
    if (flags.has("--report")) {
      io.out(report(opts.candidate, opts.results));
      return 0;
    }
    if (opts.candidateDir === null) throw new BadInput("--candidate-dir is required");
    return await (flags.has("--smoke") ? runSmoke(opts, io) : runCandidate(opts, io));
  } catch (e) {
    if (e instanceof UnknownHarness) {
      io.err(e.message);
      return 3;
    }
    if (e instanceof BadInput) {
      io.err(`agent-harness: ${e.message} (see agent-harness --help)`);
      return 2;
    }
    throw e;
  }
}
