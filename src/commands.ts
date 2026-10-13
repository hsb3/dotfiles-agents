// Subcommand and flag parsing, usage, and dispatch for the evals binary.
import { CommandError, ValidationError } from "./store.ts";

type FlagKind = "bool" | "value" | "multi";

interface FlagSpec {
  kind: FlagKind;
  required?: boolean;
}

export interface ParsedArgs {
  flags: Record<string, string | string[] | boolean | undefined>;
  positionals: string[];
}

interface CommandSpec {
  usage: string;
  summary: string;
  flags: Record<string, FlagSpec>;
  positionals: { name: string; min: number; max: number };
  loader: boolean; // takes --parse-only and --dry-run
  run: (args: ParsedArgs) => Promise<number>;
}

const notYet = async (): Promise<number> => {
  console.error("evals: this command is not implemented yet");
  return 1;
};

const NONE = { name: "", min: 0, max: 0 };

const COMMANDS: Record<string, CommandSpec> = {
  ingest: {
    usage: "evals ingest --source-root <dir> [--parse-only | --dry-run]",
    summary: "Project a dotfiles-agents checkout into the catalog collections.",
    flags: { "source-root": { kind: "value", required: true } },
    positionals: NONE,
    loader: true,
    run: notYet,
  },
  "load-eval-run": {
    usage: "evals load-eval-run <manifest>... [--parse-only | --dry-run]",
    summary: "Load evaluation provenance into eval_runs and eval_responses.",
    flags: {},
    positionals: { name: "manifest", min: 1, max: Infinity },
    loader: true,
    run: notYet,
  },
  "load-verdicts": {
    usage: "evals load-verdicts <file>... [--extenders a,b] [--complete] [--parse-only | --dry-run]",
    summary: "Load verdict files into assessments.",
    flags: { extenders: { kind: "value" }, complete: { kind: "bool" } },
    positionals: { name: "file", min: 1, max: Infinity },
    loader: true,
    run: notYet,
  },
  "compare-verdicts": {
    usage: "evals compare-verdicts --left <file>... --right <file>...",
    summary: "Report offline agreement between two sets of verdict files.",
    flags: { left: { kind: "multi", required: true }, right: { kind: "multi", required: true } },
    positionals: NONE,
    loader: false,
    run: notYet,
  },
  "load-curation": {
    usage: "evals load-curation <file> [--parse-only | --dry-run]",
    summary: "Load job_coverage and relationships rows.",
    flags: {},
    positionals: { name: "file", min: 1, max: 1 },
    loader: true,
    run: notYet,
  },
  "load-runs": {
    usage:
      "evals load-runs --ledger <path> [--runs-dir <dir>] [--campaign <label>] [--candidate <id>] [--parse-only | --dry-run]",
    summary: "Load harness ledger rows and their logs into runs, artifacts, run_events and tool_calls.",
    flags: {
      ledger: { kind: "value", required: true },
      "runs-dir": { kind: "value" },
      campaign: { kind: "value" },
      candidate: { kind: "value" },
    },
    positionals: NONE,
    loader: true,
    run: notYet,
  },
  report: {
    usage: "evals report --out <dir> [--fixtures <dir>]",
    summary: "Render coverage-matrix.md and analysis.md.",
    flags: { out: { kind: "value", required: true }, fixtures: { kind: "value" } },
    positionals: NONE,
    loader: false,
    run: notYet,
  },
  package: {
    usage: "evals package --source-root <dir> --out <dir> [--ui-build <dir>]",
    summary: "Build a new deploy directory. Never deploys.",
    flags: {
      "source-root": { kind: "value", required: true },
      out: { kind: "value", required: true },
      "ui-build": { kind: "value" },
    },
    positionals: NONE,
    loader: false,
    run: notYet,
  },
  fixture: {
    usage: "evals fixture [--pocketbase <bin>] [--source-root <dir>]",
    summary: "Run a disposable seeded loopback PocketBase until interrupted.",
    flags: { pocketbase: { kind: "value" }, "source-root": { kind: "value" } },
    positionals: NONE,
    loader: false,
    run: notYet,
  },
};

const ENVIRONMENT = `Environment: PB_URL (default http://127.0.0.1:8090), PB_ADMIN_EMAIL, PB_ADMIN_PASSWORD.`;

export function generalUsage(): string {
  const lines = ["Usage: evals <command> [options]", "", "Commands:"];
  for (const spec of Object.values(COMMANDS)) lines.push(`  ${spec.usage}`, `      ${spec.summary}`);
  lines.push("", "Run `evals <command> --help` for one command.", ENVIRONMENT);
  return lines.join("\n");
}

function commandUsage(name: string): string {
  const spec = COMMANDS[name]!;
  const lines = [`Usage: ${spec.usage}`, "", spec.summary];
  if (spec.loader) {
    lines.push("", "  --parse-only  read and validate input only; never connects", "  --dry-run     plan against the database; writes nothing");
  }
  if (spec.loader || name === "report") lines.push("", ENVIRONMENT);
  return lines.join("\n");
}

class UsageError extends Error {}

// Parses the arguments after the subcommand. `--flag value` and `--flag=value`;
// a multi flag takes every following argument up to the next flag.
export function parseArgs(name: string, argv: string[]): ParsedArgs {
  const spec = COMMANDS[name]!;
  const flags: ParsedArgs["flags"] = {};
  const positionals: string[] = [];
  const allowed: Record<string, FlagSpec> = { ...spec.flags };
  if (spec.loader) {
    allowed["parse-only"] = { kind: "bool" };
    allowed["dry-run"] = { kind: "bool" };
  }
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i]!;
    if (!arg.startsWith("--") || arg === "--") {
      positionals.push(arg);
      continue;
    }
    const eq = arg.indexOf("=");
    const flag = eq >= 0 ? arg.slice(2, eq) : arg.slice(2);
    const inline = eq >= 0 ? arg.slice(eq + 1) : undefined;
    const fs = allowed[flag];
    if (!fs) throw new UsageError(`unknown flag --${flag}`);
    if (fs.kind === "bool") {
      if (inline !== undefined) throw new UsageError(`--${flag} takes no value`);
      flags[flag] = true;
    } else if (fs.kind === "value") {
      if (flags[flag] !== undefined) throw new UsageError(`--${flag} given twice`);
      let value = inline;
      if (value === undefined) {
        if (i + 1 >= argv.length || argv[i + 1]!.startsWith("--")) throw new UsageError(`--${flag} needs a value`);
        value = argv[++i]!;
      }
      flags[flag] = value;
    } else {
      const values = (flags[flag] as string[] | undefined) ?? [];
      if (inline !== undefined) values.push(inline);
      while (i + 1 < argv.length && !argv[i + 1]!.startsWith("--")) values.push(argv[++i]!);
      if (values.length === 0) throw new UsageError(`--${flag} needs at least one value`);
      flags[flag] = values;
    }
  }
  for (const [flag, fs] of Object.entries(spec.flags)) {
    if (fs.required && flags[flag] === undefined) throw new UsageError(`missing required flag --${flag}`);
  }
  if (flags["parse-only"] && flags["dry-run"]) throw new UsageError("--parse-only and --dry-run cannot be combined");
  const { name: pname, min, max } = spec.positionals;
  if (positionals.length < min) throw new UsageError(`missing <${pname}>`);
  if (positionals.length > max) throw new UsageError(max === 0 ? `unexpected argument ${positionals[max]}` : `too many arguments`);
  return { flags, positionals };
}

// Runs the evals binary on its arguments and returns the exit code.
export async function main(argv: string[]): Promise<number> {
  const [name, ...rest] = argv;
  if (name === "--help" || name === "-h" || name === "help") {
    console.log(generalUsage());
    return 0;
  }
  if (name === undefined || !Object.hasOwn(COMMANDS, name)) {
    if (name !== undefined) console.error(`evals: unknown command ${name}`);
    console.error(generalUsage());
    return 1;
  }
  if (rest.includes("--help") || rest.includes("-h")) {
    console.log(commandUsage(name));
    return 0;
  }
  let args: ParsedArgs;
  try {
    args = parseArgs(name, rest);
  } catch (err) {
    if (!(err instanceof UsageError)) throw err;
    console.error(`evals ${name}: ${err.message}`);
    console.error(commandUsage(name));
    return 1;
  }
  try {
    return await COMMANDS[name]!.run(args);
  } catch (err) {
    if (err instanceof ValidationError) {
      for (const problem of err.problems) console.error(`evals ${name}: ${problem}`);
      return 1;
    }
    if (err instanceof CommandError) {
      console.error(`evals ${name}: ${err.message}`);
      return 1;
    }
    console.error(`evals ${name}: ${err instanceof Error ? err.message : String(err)}`);
    return 1;
  }
}
