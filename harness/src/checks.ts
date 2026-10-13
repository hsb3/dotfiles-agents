// A case's deterministic check.py, run in the final workspace. Whatever goes
// wrong becomes one failed `check.py` entry rather than an error.
import type { Entry } from "./ledger.ts";
import { runProcess, type Env } from "./subprocess.ts";

const CHECK_TIMEOUT_SEC = 120;

function checkError(reason: string): Entry[] {
  return [{ id: "check.py", passed: false, evidence: `check-error: ${reason}` }];
}

function isEntry(v: unknown): v is Entry {
  if (typeof v !== "object" || v === null) return false;
  const e = v as Record<string, unknown>;
  return typeof e.id === "string" && typeof e.passed === "boolean" && typeof e.evidence === "string";
}

/** Runs `python3 <check>` with cwd = the workspace and returns its checks. */
export async function runChecks(check: string, ws: string, env: Env): Promise<Entry[]> {
  const r = await runProcess(["python3", check], { cwd: ws, env, timeoutSec: CHECK_TIMEOUT_SEC });
  if (r.notFound) return checkError("executable not found: python3");
  if (r.timedOut) return checkError(`timeout after ${CHECK_TIMEOUT_SEC}s`);
  let parsed: unknown;
  try {
    parsed = JSON.parse(r.stdout);
  } catch {
    return checkError("stdout is not JSON");
  }
  if (!Array.isArray(parsed)) return checkError("stdout is not a JSON array");
  if (!parsed.every(isEntry)) return checkError("entries must be {id, passed, evidence}");
  return parsed.map((e) => ({ id: e.id, passed: e.passed, evidence: e.evidence }));
}
