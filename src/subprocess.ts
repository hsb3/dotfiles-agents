// Every child process the harness starts goes through runProcess: a list-form
// argv (never a shell), stdin from /dev/null, its own process group, and a
// timeout that SIGKILLs the whole group while keeping the stdout read so far.

export type Env = Record<string, string>;

export interface RunOptions {
  cwd: string;
  env: Env;
  timeoutSec: number;
}

export interface RunResult {
  stdout: string;
  stderr: string;
  /** The child's exit code; -1 on a timeout or a missing executable. */
  exitCode: number;
  timedOut: boolean;
  notFound: boolean;
  durationMs: number;
}

/** Resolves a bare executable name on the PATH of the given environment. */
export function findExecutable(name: string, env: Env): string | null {
  return Bun.which(name, { PATH: env.PATH ?? "" });
}

async function collect(stream: ReadableStream<Uint8Array>, chunks: Uint8Array[]): Promise<void> {
  const reader = stream.getReader();
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) return;
      chunks.push(value);
    }
  } catch {
    // A stream torn down by the group kill ends the capture; what was read stays.
  }
}

function decode(chunks: Uint8Array[]): string {
  return new TextDecoder().decode(Buffer.concat(chunks));
}

function killGroup(pid: number): void {
  try {
    process.kill(-pid, "SIGKILL");
  } catch {
    // The group is already gone.
  }
}

export async function runProcess(argv: string[], opts: RunOptions): Promise<RunResult> {
  const started = performance.now();
  const name = argv[0] ?? "";
  const exe = findExecutable(name, opts.env);
  if (exe === null) {
    return { stdout: "", stderr: "", exitCode: -1, timedOut: false, notFound: true, durationMs: 0 };
  }
  let child: Bun.Subprocess<"ignore", "pipe", "pipe">;
  try {
    child = Bun.spawn([exe, ...argv.slice(1)], {
      cwd: opts.cwd,
      env: opts.env,
      stdin: "ignore",
      stdout: "pipe",
      stderr: "pipe",
      detached: true,
    });
  } catch {
    return { stdout: "", stderr: "", exitCode: -1, timedOut: false, notFound: true, durationMs: 0 };
  }
  const out: Uint8Array[] = [];
  const err: Uint8Array[] = [];
  const reading = Promise.all([collect(child.stdout, out), collect(child.stderr, err)]);
  let timer: ReturnType<typeof setTimeout> | undefined;
  const expired = new Promise<"timeout">((resolve) => {
    timer = setTimeout(() => resolve("timeout"), opts.timeoutSec * 1000);
  });
  const finished = child.exited.then(() => "done" as const);
  const timedOut = (await Promise.race([finished, expired])) === "timeout";
  clearTimeout(timer);
  // Kill whatever is left of the group: on a timeout the whole tree, otherwise
  // stragglers the CLI left behind, which could hold the pipes open. Then let
  // the pipes drain; a process that escaped the group cannot stall the run.
  killGroup(child.pid);
  const code = await child.exited;
  await Promise.race([reading, Bun.sleep(2000)]);
  return {
    stdout: decode(out),
    stderr: decode(err),
    exitCode: timedOut ? -1 : code,
    timedOut,
    notFound: false,
    durationMs: Math.round(performance.now() - started),
  };
}
