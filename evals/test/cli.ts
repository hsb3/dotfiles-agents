// Runs the evals CLI as a child process (async, so a stub or server in this
// process keeps answering).
import { join } from "node:path";
import { REPO_ROOT } from "./pb.ts";

export interface CliResult {
  code: number;
  stdout: string;
  stderr: string;
}

export async function runCli(args: string[], env: Record<string, string | undefined> = {}, cwd = REPO_ROOT): Promise<CliResult> {
  const fullEnv: Record<string, string> = {};
  for (const [k, v] of Object.entries({ ...process.env, PB_URL: undefined, PB_ADMIN_EMAIL: undefined, PB_ADMIN_PASSWORD: undefined, ...env })) {
    if (v !== undefined) fullEnv[k] = v;
  }
  const proc = Bun.spawn([process.execPath, join(REPO_ROOT, "src/cli.ts"), ...args], {
    cwd,
    env: fullEnv,
    stdout: "pipe",
    stderr: "pipe",
  });
  const [stdout, stderr, code] = await Promise.all([new Response(proc.stdout).text(), new Response(proc.stderr).text(), proc.exited]);
  return { code, stdout, stderr };
}
