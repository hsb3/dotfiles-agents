// Parses `site build` and `site serve`, fills in the defaults, runs the
// build and prints its outcome.
import { dirname, isAbsolute, join, relative, resolve } from "node:path";
import { build } from "./build.ts";

/** The unit folder: the one holding `site.config.json`, `assets/` and `src/`. */
export const UNIT = resolve(import.meta.dir, "..");

export const USAGE = `usage: site build [--root DIR] [--config FILE] [--output DIR] [--ref REF]
       site serve [--root DIR] [--config FILE] [--output DIR] [--ref REF] [--port N]`;

/** Where `build` looks when an option is left out (the output and ref come from the config). */
export const DEFAULTS = {
  root: dirname(UNIT),
  config: join(UNIT, "site.config.json"),
  stylesheet: join(UNIT, "assets", "site.css"),
};

const BUILD_OPTIONS = ["root", "config", "output", "ref"];

/** Runs one command line; resolves to the exit code. */
export async function run(args: string[]): Promise<number> {
  const [command, ...rest] = args;
  if (command !== "build") return usage(command === undefined ? "missing command" : `unknown command: ${command}`);
  const parsed = parseOptions(rest, BUILD_OPTIONS);
  if (typeof parsed === "string") return usage(parsed);

  const result = await build({
    root: parsed.root ?? DEFAULTS.root,
    config: parsed.config ?? DEFAULTS.config,
    configLabel: parsed.config ?? configLabel(DEFAULTS.config),
    stylesheet: DEFAULTS.stylesheet,
    output: parsed.output,
    ref: parsed.ref,
  });
  if (!result.ok) {
    for (const problem of result.problems) console.error(problem);
    console.error(`build: ${result.problems.length} problems; nothing written`);
    return 1;
  }
  console.log(`${result.pages} pages built, links verified: ${result.output}`);
  return 0;
}

/** `--name value` or `--name=value` for each allowed name; a string is the reason the line is not valid. */
export function parseOptions(args: string[], allowed: string[]): Record<string, string> | string {
  const options: Record<string, string> = {};
  for (let i = 0; i < args.length; i++) {
    const arg = args[i]!;
    const match = /^--([a-z]+)(?:=(.*))?$/s.exec(arg);
    if (match === null || !allowed.includes(match[1]!)) return `unknown option: ${arg}`;
    const value = match[2] ?? args[++i];
    if (value === undefined || value === "" || (match[2] === undefined && value.startsWith("--"))) {
      return `option --${match[1]} needs a value`;
    }
    options[match[1]!] = value;
  }
  return options;
}

function usage(reason: string): number {
  console.error(`site: ${reason}`);
  console.error(USAGE);
  return 1;
}

/** The default config named relative to the working folder when it lies below it. */
function configLabel(path: string): string {
  const label = relative(process.cwd(), path);
  return label.startsWith("..") || isAbsolute(label) ? path : label;
}
