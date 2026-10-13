// The append-only results ledger: one JSON row per trial, serialized exactly as
// Python's json.dumps(row, sort_keys=True) would, which the evals loader expects.
import { appendFileSync, existsSync, mkdirSync, readFileSync } from "node:fs";
import { dirname } from "node:path";

export interface Entry {
  id: string;
  passed: boolean;
  evidence: string;
}

export interface Preconditions {
  auth_env_present: string[];
  campaign: string;
  cli_version: string;
  grader_model: string;
  harness: string;
  model: string;
  network_assumption: "assumed-available";
  self_installs: string[];
  timeout: number;
}

/** One ledger row: exactly these 29 fields. */
export interface Row {
  ts: string;
  campaign: string;
  harness: string;
  model: string;
  candidate: string;
  case: string;
  config: string;
  trial: number;
  kind: string;
  grader_model: string | null;
  passed: boolean | null;
  checks: Entry[];
  grades: Entry[];
  skill_used: boolean;
  tool_names: string[];
  plugin_errors: unknown[];
  exit_code: number | null;
  error: string | null;
  cost_usd: number | null;
  duration_ms: number | null;
  num_turns: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
  cache_read_tokens: number | null;
  cache_creation_tokens: number | null;
  workspace: string | null;
  log_path: string | null;
  cli_version: string;
  preconditions: Preconditions;
}

function compareCodePoints(a: string, b: string): number {
  const x = Array.from(a);
  const y = Array.from(b);
  for (let i = 0; i < Math.min(x.length, y.length); i++) {
    const d = x[i]!.codePointAt(0)! - y[i]!.codePointAt(0)!;
    if (d !== 0) return d;
  }
  return x.length - y.length;
}

function pyString(s: string): string {
  // JSON.stringify already escapes quotes, backslashes and control characters
  // the way Python does; Python (ensure_ascii) also escapes DEL and every
  // non-ASCII UTF-16 code unit as lowercase \uXXXX.
  return JSON.stringify(s).replace(/[^\x00-\x7e]/g, (c) => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0"));
}

/** Serializes a JSON value the way Python's json.dumps(value, sort_keys=True) does. */
export function pythonJson(value: unknown): string {
  if (value === null || value === undefined) return "null";
  if (typeof value === "string") return pyString(value);
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : "null";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (Array.isArray(value)) return "[" + value.map(pythonJson).join(", ") + "]";
  if (typeof value === "object") {
    const keys = Object.keys(value).sort(compareCodePoints);
    const obj = value as Record<string, unknown>;
    return "{" + keys.map((k) => pyString(k) + ": " + pythonJson(obj[k])).join(", ") + "}";
  }
  return "null";
}

/** Appends one row as a single write, creating the ledger and its directory on first use. */
export function appendRow(path: string, row: Row): void {
  mkdirSync(dirname(path), { recursive: true });
  appendFileSync(path, pythonJson(row) + "\n");
}

/** A row read back from the ledger; only the key fields are guaranteed. */
export type LedgerRow = Partial<Row> & Pick<Row, "campaign" | "harness" | "model" | "candidate" | "case" | "config" | "trial">;

function asLedgerRow(value: unknown): LedgerRow | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
  const r = value as Record<string, unknown>;
  for (const f of ["harness", "model", "candidate", "case", "config"]) {
    if (typeof r[f] !== "string") return null;
  }
  if (typeof r.trial !== "number" || !Number.isInteger(r.trial)) return null;
  if (r.campaign === undefined || r.campaign === null) r.campaign = "";
  if (typeof r.campaign !== "string") return null;
  return r as unknown as LedgerRow;
}

/** Every valid row of the ledger, in file order; other lines are skipped silently. */
export function readRows(path: string): LedgerRow[] {
  if (!existsSync(path)) return [];
  const rows: LedgerRow[] = [];
  for (const line of readFileSync(path, "utf8").split("\n")) {
    if (!line.trim()) continue;
    let parsed: unknown;
    try {
      parsed = JSON.parse(line);
    } catch {
      continue;
    }
    const row = asLedgerRow(parsed);
    if (row) rows.push(row);
  }
  return rows;
}

export interface KeyParts {
  campaign: string;
  harness: string;
  model: string;
  candidate: string;
  case: string;
  config: string;
  trial: number;
}

/** The resume key `<campaign>|<harness>|<model>|<candidate>|<case>|<config>|<trial>`. */
export function resumeKey(k: KeyParts): string {
  return [k.campaign, k.harness, k.model, k.candidate, k.case, k.config, String(k.trial)].join("|");
}

/** The resume keys already in the ledger, whatever their outcome. */
export function doneKeys(path: string): Set<string> {
  return new Set(readRows(path).map(resumeKey));
}
