// Stub agent CLIs for the test suite. A stub is a Bun script (absolute
// shebang, so a version-manager shim on PATH is never involved) that records
// its argv, cwd and environment and replays the first rule its argv matches.
import { chmodSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

export const STREAMS = join(import.meta.dir, "..", "fixtures", "streams");

export interface StubRule {
  /** The argv after the executable starts with these. */
  prefix?: string[];
  /** The argv contains every one of these. */
  has?: string[];
  /** Replay this fixture (a file name under test/fixtures/streams) on stdout. */
  stream?: string;
  stdout?: string;
  stderr?: string;
  exit?: number;
  /** After printing, start a sleeping descendant, write its pid here, and hang. */
  sleeperPidFile?: string;
  /** After printing, hang until killed. */
  hang?: boolean;
  /** Files to write, keyed by path relative to the stub's cwd. */
  writeFiles?: Record<string, string>;
}

export interface StubCall {
  argv: string[];
  cwd: string;
  env: Record<string, string>;
}

const STUB_SOURCE = (rulesPath: string, callsPath: string, streams: string) => `
const fs = require("node:fs");
const path = require("node:path");
const args = process.argv.slice(2);
fs.appendFileSync(${JSON.stringify(callsPath)}, JSON.stringify({ argv: args, cwd: process.cwd(), env: process.env }) + "\\n");
const rules = JSON.parse(fs.readFileSync(${JSON.stringify(rulesPath)}, "utf8"));
const rule = rules.find((r) =>
  (!r.prefix || r.prefix.every((p, i) => args[i] === p)) &&
  (!r.has || r.has.every((h) => args.includes(h)))) || {};
for (const [rel, body] of Object.entries(rule.writeFiles || {})) {
  const target = path.resolve(process.cwd(), rel);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, body);
}
let out = rule.stdout || "";
if (rule.stream) out = fs.readFileSync(path.join(${JSON.stringify(streams)}, rule.stream), "utf8");
if (out) fs.writeSync(1, out);
if (rule.stderr) fs.writeSync(2, rule.stderr);
if (rule.sleeperPidFile) {
  const child = Bun.spawn(["sleep", "300"], { stdin: "ignore", stdout: "ignore", stderr: "ignore" });
  fs.writeFileSync(rule.sleeperPidFile, String(child.pid));
}
if (rule.hang || rule.sleeperPidFile) setInterval(() => {}, 1 << 30);
else process.exit(rule.exit || 0);
`;

/** Writes an executable stub `name` into `binDir` that follows `rules`. */
export function installStub(binDir: string, name: string, rules: StubRule[]): void {
  mkdirSync(binDir, { recursive: true });
  const rulesPath = join(binDir, `${name}.rules.json`);
  const callsPath = join(binDir, `${name}.calls.jsonl`);
  writeFileSync(rulesPath, JSON.stringify(rules));
  const script = join(binDir, name);
  writeFileSync(script, `#!${process.execPath}\n${STUB_SOURCE(rulesPath, callsPath, STREAMS)}`);
  chmodSync(script, 0o755);
}

/** Every recorded invocation of stub `name`, oldest first. */
export function stubCalls(binDir: string, name: string): StubCall[] {
  const path = join(binDir, `${name}.calls.jsonl`);
  if (!existsSync(path)) return [];
  return readFileSync(path, "utf8")
    .split("\n")
    .filter(Boolean)
    .map((line) => JSON.parse(line) as StubCall);
}

/** A scratch directory with a `bin/` for stubs, removed by `cleanup`. */
export function sandbox(): { root: string; bin: string; cleanup: () => void } {
  const root = mkdtempSync(join(tmpdir(), "ah-test-"));
  const bin = join(root, "bin");
  mkdirSync(bin);
  return { root, bin, cleanup: () => rmSync(root, { recursive: true, force: true }) };
}

/** PATH with the stub dir first, then the system dirs (no python3 stub unless installed). */
export function stubPath(bin: string, keepRealPath = true): string {
  return keepRealPath ? `${bin}:${process.env.PATH ?? ""}` : `${bin}:/usr/bin:/bin`;
}

