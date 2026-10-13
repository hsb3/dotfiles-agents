// Runs the agent-harness CLI (src/cli.ts) under the test's Bun, never `bun` from PATH.
import { join } from "node:path";

export const CLI = join(import.meta.dir, "..", "..", "src", "cli.ts");

export interface CliResult {
  code: number;
  stdout: string;
  stderr: string;
}

export async function runCli(args: string[], env: Record<string, string>, cwd?: string): Promise<CliResult> {
  const proc = Bun.spawn([process.execPath, CLI, ...args], { env, cwd, stdin: "ignore", stdout: "pipe", stderr: "pipe" });
  const [stdout, stderr, code] = await Promise.all([new Response(proc.stdout).text(), new Response(proc.stderr).text(), proc.exited]);
  return { code, stdout, stderr };
}

/** A capturing Io for calling main() in-process. */
export function captureIo(): { out: string[]; err: string[]; io: { out(l: string): void; err(l: string): void } } {
  const out: string[] = [];
  const err: string[] = [];
  return { out, err, io: { out: (l) => out.push(l), err: (l) => err.push(l) } };
}
