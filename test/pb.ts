// Disposable PocketBase servers for tests: a free loopback port, a temporary
// data directory, this repository's migrations and hooks, one superuser.
import { existsSync, mkdtempSync, rmSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { setDefaultTimeout } from "bun:test";

// Tests that spawn the CLI against a real server take seconds, not milliseconds.
setDefaultTimeout(60000);

export const REPO_ROOT = resolve(import.meta.dir, "..");
export const SUPERUSER_EMAIL = "test-admin@example.test";
export const SUPERUSER_PASSWORD = "TestAdminPassword123";

export function pocketbaseBinary(): string | null {
  const fromEnv = process.env.PB_BINARY;
  if (fromEnv) return existsSync(fromEnv) ? fromEnv : null;
  return Bun.which("pocketbase");
}

export const HAS_POCKETBASE = pocketbaseBinary() !== null;

export async function freePort(): Promise<number> {
  const server = Bun.listen({ hostname: "127.0.0.1", port: 0, socket: { data() {} } });
  const port = server.port;
  server.stop(true);
  return port;
}

function repoDir(name: string, fallback: string): string {
  const dir = join(REPO_ROOT, name);
  return existsSync(dir) ? dir : fallback;
}

export interface PbServer {
  url: string;
  dataDir: string;
  email: string;
  password: string;
  stop(): Promise<void>;
  restart(options?: { migrationsDir?: string; hooksDir?: string }): Promise<void>;
  superuserToken(): Promise<string>;
}

export interface PbOptions {
  migrationsDir?: string | null; // null = an empty migrations directory
  hooksDir?: string | null;
  dataDir?: string;
}

async function waitHealthy(url: string, proc: Bun.Subprocess, timeoutMs = 15000): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (proc.exitCode !== null) throw new Error(`pocketbase exited with ${proc.exitCode}`);
    try {
      const res = await fetch(`${url}/api/health`);
      if (res.ok) return;
    } catch {
      // not listening yet
    }
    await Bun.sleep(50);
  }
  throw new Error("pocketbase did not become healthy");
}

export async function startPocketBase(options: PbOptions = {}): Promise<PbServer> {
  const bin = pocketbaseBinary();
  if (!bin) throw new Error("no pocketbase binary");
  const root = mkdtempSync(join(tmpdir(), "evals-pb-"));
  const dataDir = options.dataDir ?? join(root, "pb_data");
  const emptyDir = join(root, "empty");
  mkdirSync(emptyDir, { recursive: true });
  let migrationsDir =
    options.migrationsDir === null ? emptyDir : (options.migrationsDir ?? repoDir("pb_migrations", emptyDir));
  let hooksDir = options.hooksDir === null ? emptyDir : (options.hooksDir ?? repoDir("pb_hooks", emptyDir));

  const upsert = Bun.spawnSync(
    [bin, "superuser", "upsert", SUPERUSER_EMAIL, SUPERUSER_PASSWORD, "--dir", dataDir, "--migrationsDir", migrationsDir, "--hooksDir", hooksDir],
    { stdout: "pipe", stderr: "pipe" },
  );
  if (upsert.exitCode !== 0) throw new Error(`superuser upsert failed: ${upsert.stderr.toString()}${upsert.stdout.toString()}`);

  let proc: Bun.Subprocess;
  let url = "";
  const launch = async () => {
    const port = await freePort();
    url = `http://127.0.0.1:${port}`;
    proc = Bun.spawn(
      [bin, "serve", `--http=127.0.0.1:${port}`, "--dir", dataDir, "--migrationsDir", migrationsDir, "--hooksDir", hooksDir, "--automigrate=false"],
      { stdout: "ignore", stderr: "pipe" },
    );
    await waitHealthy(url, proc);
    server.url = url;
  };
  const halt = async () => {
    if (proc && proc.exitCode === null) {
      proc.kill("SIGTERM");
      await proc.exited;
    }
  };
  let token: string | null = null;
  const server: PbServer = {
    url,
    dataDir,
    email: SUPERUSER_EMAIL,
    password: SUPERUSER_PASSWORD,
    async stop() {
      await halt();
      rmSync(root, { recursive: true, force: true });
    },
    async restart(next = {}) {
      await halt();
      if (next.migrationsDir) migrationsDir = next.migrationsDir;
      if (next.hooksDir) hooksDir = next.hooksDir;
      token = null;
      await launch();
    },
    async superuserToken() {
      if (token) return token;
      const res = await fetch(`${server.url}/api/collections/_superusers/auth-with-password`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ identity: SUPERUSER_EMAIL, password: SUPERUSER_PASSWORD }),
      });
      if (!res.ok) throw new Error(`superuser auth failed: ${res.status} ${await res.text()}`);
      token = ((await res.json()) as { token: string }).token;
      return token;
    },
  };
  await launch();
  return server;
}

// A JSON request against a test server; returns status and parsed body.
export async function api(
  server: PbServer,
  method: string,
  path: string,
  body?: unknown,
  token?: string | null,
): Promise<{ status: number; body: any }> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["content-type"] = "application/json";
  if (token) headers.authorization = token;
  const res = await fetch(`${server.url}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await res.text();
  let parsed: any = text;
  try {
    parsed = text ? JSON.parse(text) : null;
  } catch {
    // keep text
  }
  return { status: res.status, body: parsed };
}
