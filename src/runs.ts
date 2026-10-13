// `evals load-runs`: harness ledger rows and their logs into runs, artifacts,
// run_events and tool_calls, each run carrying its `measurement` v1 envelope.
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { basename, dirname, join } from "node:path";
import { canonicalSha256, compareCodePoints, parseJson, plain, sha256Hex } from "./canonical.ts";
import { parseLog, type EventRow, type Harness, type LogArtifact, type ParsedLog, type ToolCallRow } from "./logs.ts";
import {
  applyPlans, CommandError, connect, diff, fetchAll, fetchWhereIn, formatPlan, formatWarnings, newId, ValidationError,
  type Body, type CollectionPlan, type Connection, type Desired, type Rec,
} from "./store.ts";

export const MEASUREMENT_FIELDS = [
  "passed", "skill_used", "exit_code", "num_turns", "cost_usd", "duration_ms",
  "input_tokens", "output_tokens", "cache_creation_tokens", "cache_read_tokens",
] as const;
const ROLLUP_FIELDS = ["cost_usd", "duration_ms", "input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens"] as const;
const NUMERIC_FIELDS = ["num_turns", "cost_usd", "duration_ms", "input_tokens", "output_tokens", "cache_creation_tokens", "cache_read_tokens"];
const VERBATIM = [
  "harness", "model", "candidate", "case", "config", "trial", "kind", "grader_model", ...MEASUREMENT_FIELDS,
  "error", "workspace", "checks", "grades", "tool_names", "ts", "cli_version",
];
const HARNESSES = ["claude", "opencode", "codex"];

type Obj = Record<string, unknown>;

export interface LedgerRow {
  line: number; // 1-based line in the ledger
  key: string;
  row: Obj; // plain values
  recordSha256: string;
}

export function rowKey(row: Obj): string {
  const text = (v: unknown) => (v === undefined || v === null ? "" : String(v));
  return ["campaign", "harness", "model", "candidate", "case", "config", "trial"].map((k) => text(row[k])).join("|");
}

// Reads the ledger: blank lines ignored, a line that is not a JSON object skipped
// with a warning, a later row with the same key replacing an earlier one.
export function readLedger(text: string, warnings: string[]): LedgerRow[] {
  const byKey = new Map<string, LedgerRow>();
  text.split("\n").forEach((raw, i) => {
    const line = raw.replace(/\r$/, "");
    if (line.trim() === "") return;
    let parsed: unknown;
    try {
      parsed = parseJson(line.trim());
    } catch {
      parsed = null;
    }
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
      warnings.push(`ledger line ${i + 1} skipped: not a JSON object`);
      return;
    }
    const row = plain(parsed) as Obj;
    const key = rowKey(row);
    byKey.set(key, { line: i + 1, key, row, recordSha256: canonicalSha256(parsed) });
  });
  return [...byKey.values()];
}

export function validateRow(r: LedgerRow): string[] {
  const problems: string[] = [];
  const bad = (field: string, what: string) => problems.push(`${r.key}: ${field} must be ${what}`);
  const { row } = r;
  for (const f of ["passed", "skill_used"]) if (row[f] !== undefined && row[f] !== null && typeof row[f] !== "boolean") bad(f, "a boolean or null");
  if (row.exit_code !== undefined && row.exit_code !== null && !(typeof row.exit_code === "number" && Number.isInteger(row.exit_code))) bad("exit_code", "an integer or null");
  for (const f of NUMERIC_FIELDS) {
    const v = row[f];
    if (v === undefined || v === null) continue;
    if (typeof v !== "number" || !Number.isFinite(v) || v < 0) bad(f, "a finite non-negative number or null");
  }
  if (!HARNESSES.includes(String(row.harness))) bad("harness", `one of ${HARNESSES.join(", ")}`);
  if (row.config !== "with" && row.config !== "baseline") bad("config", "with or baseline");
  if (typeof row.candidate !== "string" || !row.candidate) bad("candidate", "a non-empty string");
  if (typeof row.case !== "string" || !row.case) bad("case", "a non-empty string");
  if (typeof row.trial !== "number" || !Number.isInteger(row.trial) || row.trial < 0) bad("trial", "a non-negative integer");
  return problems;
}

function isSkipRow(row: Obj): boolean {
  return row.passed === null && typeof row.error === "string" && row.error.startsWith("unsupported:");
}

function isStringList(v: unknown): boolean {
  return Array.isArray(v) && v.every((x) => typeof x === "string");
}

export function validPreconditions(p: unknown): boolean {
  if (p === null || typeof p !== "object" || Array.isArray(p) || Object.keys(p).length === 0) return false;
  const o = p as Obj;
  for (const k of ["harness", "cli_version", "model", "campaign", "network_assumption"]) if (typeof o[k] !== "string") return false;
  if (!("grader_model" in o) || !(o.grader_model === null || typeof o.grader_model === "string")) return false;
  if (typeof o.timeout !== "number" || !Number.isFinite(o.timeout) || o.timeout < 0) return false;
  return isStringList(o.auth_env_present) && isStringList(o.self_installs);
}

export function execution(row: Obj): { validity: string; reason: string } {
  const exit = row.exit_code ?? null;
  const pluginErrors = row.plugin_errors;
  const error = row.error;
  if (exit !== null && exit !== 0) return { validity: "invalid", reason: "producer exit_code was nonzero" };
  if (Array.isArray(pluginErrors) && pluginErrors.length > 0) return { validity: "invalid", reason: "producer recorded plugin_errors" };
  if (isSkipRow(row)) return { validity: "skipped", reason: "explicit unsupported producer row" };
  if (typeof error === "string" && error !== "") return { validity: "invalid", reason: "producer recorded error" };
  if (typeof row.passed !== "boolean") return { validity: "unknown", reason: "passed was not an explicit boolean" };
  if (exit !== 0) return { validity: "unknown", reason: "exit_code was not explicitly zero" };
  if (!Array.isArray(pluginErrors)) return { validity: "unknown", reason: "plugin_errors were not recorded" };
  if (!validPreconditions(row.preconditions)) return { validity: "unknown", reason: "preconditions were missing or malformed" };
  return { validity: "valid", reason: "producer recorded completed run evidence" };
}

export interface LogLink {
  path: string | null; // the log file read, null when unobserved
  logPath: string | null; // the value stored in runs.log_path
}

export interface BuiltRun {
  key: string;
  body: Body;
  log: ParsedLog | null;
  logPath: string | null;
}

// The run row of one ledger row, its measurement included. `stored` is the
// existing run with that key, for the logless re-run rule.
export function buildRun(r: LedgerRow, link: LogLink, logBytes: Uint8Array | null, stored?: Rec): BuiltRun {
  const row = r.row;
  const harness = String(row.harness);
  const log = logBytes ? parseLog(harness as Harness, logBytes) : null;
  const body: Body = { campaign: row.campaign ?? "" };
  for (const f of VERBATIM) body[f] = row[f] ?? null;
  if (link.logPath !== null) body.log_path = link.logPath;
  const provenance: Obj = {};
  const fromRollup = new Set<string>();
  const era = log ? log.era : harness === "claude" ? null : "na";
  if (era !== null) body.era = era;
  body.session_id = log ? log.sessionId : "";
  if (log) {
    body.model_usage = log.modelUsage;
    body.provenance = log.provenance;
  }
  if (era === "na" && log?.rollup) {
    for (const f of ROLLUP_FIELDS) {
      if (body[f] === null && log.rollup[f] !== null && log.rollup[f] !== undefined) {
        body[f] = log.rollup[f];
        fromRollup.add(f);
      }
    }
  }
  const observation = logBytes ? "observed" : isSkipRow(row) ? "absent" : "unobserved-local";
  let logSha: string | null = logBytes ? sha256Hex(logBytes) : null;
  const available: Obj = {};
  for (const f of MEASUREMENT_FIELDS) {
    available[f] = body[f] !== null;
    provenance[f] = row[f] !== undefined && row[f] !== null ? "ledger" : fromRollup.has(f) ? "log-rollup" : null;
  }
  let logObservation = observation;
  if (stored && observation === "unobserved-local") {
    const sm = (stored.measurement ?? {}) as Obj;
    const sAvail = (sm.available ?? {}) as Obj;
    const sProv = (sm.provenance ?? {}) as Obj;
    const sIdentity = (sm.source_identity ?? {}) as Obj;
    if (typeof stored.session_id === "string" && stored.session_id !== "") body.session_id = stored.session_id;
    if (typeof stored.era === "string" && stored.era !== "") body.era = stored.era;
    for (const f of MEASUREMENT_FIELDS) {
      if (body[f] !== null || stored[f] === undefined || stored[f] === null) continue;
      body[f] = stored[f];
      if (sAvail[f] === true && sProv[f] === "log-rollup") {
        available[f] = true;
        provenance[f] = "log-rollup";
      }
    }
    if (sIdentity.log_observation === "observed" && typeof sIdentity.log_sha256 === "string") {
      logSha = sIdentity.log_sha256;
      logObservation = "observed";
    }
  }
  body.measurement = {
    version: 1,
    source: "harness-ledger",
    available,
    provenance,
    execution: {
      ...execution(row),
      preconditions: row.preconditions !== null && typeof row.preconditions === "object" && !Array.isArray(row.preconditions) ? row.preconditions : null,
      plugin_errors: row.plugin_errors ?? null,
    },
    source_identity: {
      record_sha256: r.recordSha256,
      record_canonicalization: "json-sorted-keys-utf8",
      log_sha256: logSha,
      log_available: logSha !== null,
      log_observation: logObservation,
      revision: { value: null, available: false },
    },
  };
  for (const [k, v] of Object.entries(body)) {
    if (v === null && !(MEASUREMENT_FIELDS as readonly string[]).includes(k)) delete body[k];
  }
  return { key: r.key, body, log, logPath: link.logPath };
}

// ---------------------------------------------------------------- linkage

function logPrefix(row: Obj): string {
  return `${row.harness}-${row.candidate}-${row.case}-${row.config}-${row.trial}-`;
}

export function linkLogs(rows: LedgerRow[], ledgerDir: string, runsDir: string, warnings: (row: LedgerRow, text: string) => void): Map<string, LogLink> {
  const available = existsSync(runsDir) && statSync(runsDir).isDirectory()
    ? readdirSync(runsDir).filter((n) => n.endsWith(".log")).sort(compareCodePoints)
    : [];
  const claimed = new Set<string>();
  const links = new Map<string, LogLink>();
  for (const r of rows) {
    const lp = r.row.log_path;
    if (typeof lp !== "string" || lp === "") continue;
    const name = basename(lp);
    claimed.add(name);
    const direct = join(ledgerDir, lp);
    const fallback = join(runsDir, name);
    const path = existsSync(direct) ? direct : existsSync(fallback) ? fallback : null;
    links.set(r.key, { path, logPath: lp });
  }
  for (const r of rows) {
    if (links.has(r.key)) continue;
    const prefix = logPrefix(r.row);
    const candidates = available.filter((n) => n.startsWith(prefix) && !claimed.has(n));
    if (candidates.length === 0) {
      warnings(r, `no log matches prefix '${prefix}' (run ingested with empty log fields)`);
      links.set(r.key, { path: null, logPath: null });
      continue;
    }
    const pick = candidates[0]!;
    if (candidates.length > 1) warnings(r, `ambiguous link for '${prefix}': ${candidates.length} candidates, picked earliest '${pick}'`);
    claimed.add(pick);
    links.set(r.key, { path: join(runsDir, pick), logPath: `harness/runs/${pick}` });
  }
  return links;
}

// ---------------------------------------------------------------- children

const EVENT_FIELDS = ["seq", "ts", "vendor", "role", "event_type", "tool_name", "tool_call_id", "status", "is_error", "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens", "cost_usd", "wallclock_ms", "text", "payload"];
const TOOL_CALL_FIELDS = ["tool_call_id", "tool_name", "input", "output", "status", "is_error", "wallclock_ms", "started_ts"];

// A run_events or tool_calls body: the named fields that are not null, the run,
// and the first of its artifacts.
function childBody(row: EventRow | ToolCallRow, fields: string[], runId: string, artifactIds: Map<string, string>): Body {
  const body: Body = {};
  for (const f of fields) {
    const v = (row as unknown as Obj)[f];
    if (v !== undefined && v !== null) body[f] = v;
  }
  body.run = runId;
  if (row.artifacts.length > 0) body.artifact = artifactIds.get(row.artifacts[0]!)!;
  return body;
}

// ---------------------------------------------------------------- the command

export interface LoadRunsOptions {
  ledger: string;
  runsDir?: string;
  campaign?: string;
  candidate?: string;
  mode: "parse-only" | "dry-run" | "write";
  env?: Record<string, string | undefined>;
}

function inScope(row: Obj, o: LoadRunsOptions): boolean {
  if (o.campaign !== undefined && String(row.campaign ?? "") !== o.campaign) return false;
  if (o.candidate !== undefined && row.candidate !== o.candidate) return false;
  return true;
}

function scopeFilter(conn: Connection, o: LoadRunsOptions): string | undefined {
  const parts: string[] = [];
  const params: Record<string, string> = {};
  if (o.campaign !== undefined) {
    parts.push("campaign = {:campaign}");
    params.campaign = o.campaign;
  }
  if (o.candidate !== undefined) {
    parts.push("candidate = {:candidate}");
    params.candidate = o.candidate;
  }
  return parts.length > 0 ? conn.pb.filter(parts.join(" && "), params) : undefined;
}

export async function loadRuns(o: LoadRunsOptions): Promise<number> {
  let text: string;
  try {
    text = readFileSync(o.ledger, "utf8");
  } catch (err) {
    throw new CommandError(`cannot read ledger ${o.ledger}: ${err instanceof Error ? err.message : String(err)}`);
  }
  const ledgerDir = dirname(o.ledger);
  const runsDir = o.runsDir ?? join(ledgerDir, "runs");
  const ledgerWarnings: string[] = [];
  const all = readLedger(text, ledgerWarnings);
  const warnings: string[] = [];
  const problems = all.flatMap(validateRow);
  if (problems.length > 0) throw new ValidationError(problems);
  const rows = all.filter((r) => inScope(r.row, o));
  if (rows.length === 0) {
    if (ledgerWarnings.length > 0) console.log(formatWarnings(ledgerWarnings).join("\n"));
    console.log("no ledger rows in scope; nothing to do");
    return 0;
  }
  const scoped = new Set(rows.map((r) => r.key));
  const links = linkLogs(all, ledgerDir, runsDir, (r, w) => {
    if (scoped.has(r.key)) warnings.push(w);
  });
  const logBytes = new Map<string, Uint8Array>();
  for (const r of rows) {
    const path = links.get(r.key)!.path;
    if (path) logBytes.set(r.key, new Uint8Array(readFileSync(path)));
  }

  if (o.mode === "parse-only") {
    const built = rows.map((r) => buildRun(r, links.get(r.key)!, logBytes.get(r.key) ?? null));
    const artifacts = new Map<string, LogArtifact>();
    let events = 0;
    let calls = 0;
    const era = { legacy: 0, post: 0, na: 0 };
    for (const b of built) {
      if (!b.log) continue;
      events += b.log.events.length;
      calls += b.log.toolCalls.length;
      era[b.log.era]++;
      for (const a of b.log.artifacts) if (!artifacts.has(a.sha256)) artifacts.set(a.sha256, a);
    }
    const screenshots = [...artifacts.values()].filter((a) => a.kind === "screenshot").length;
    const n = rows.length;
    const lines = [
      "[parse-only] planned records (no DB connection):",
      `  runs:        ${n}`,
      `  run_events:  ${events}`,
      `  tool_calls:  ${calls}`,
      `  artifacts:   ${artifacts.size} post-dedup (${screenshots} screenshot, ${artifacts.size - screenshots} text)`,
      `  runs with log reference: ${built.filter((b) => b.body.log_path !== undefined).length}/${n}`,
      `  runs with observed log bytes: ${logBytes.size}/${n}`,
      `  era split:   legacy=${era.legacy}, post=${era.post}, na=${era.na}`,
      ...(ledgerWarnings.length + warnings.length === 0
        ? ["  warnings:    none"]
        : [`  warnings (${ledgerWarnings.length + warnings.length}):`, ...[...ledgerWarnings, ...warnings].map((w) => `    - ${w}`)]),
    ];
    console.log(lines.join("\n"));
    return 0;
  }

  const conn = await connect(o.env);
  const storedRuns = await fetchAll(conn, "runs", scopeFilter(conn, o));
  const storedByKey = new Map(storedRuns.map((r) => [rowKey(r), r]));
  const built = rows.map((r) => buildRun(r, links.get(r.key)!, logBytes.get(r.key) ?? null, storedByKey.get(r.key)));
  const runs = diff(
    "runs",
    built.map((b) => ({ key: b.key, body: b.body })),
    storedRuns,
    rowKey,
    {
      skip: (field, d) => {
        const available = ((d.body.measurement as Obj).available ?? {}) as Obj;
        return (MEASUREMENT_FIELDS as readonly string[]).includes(field) && available[field] === false;
      },
    },
  );

  // Artifacts: deduplicated across the load, owned by the first run in ledger order.
  const owners = new Map<string, { artifact: LogArtifact; runKey: string }>();
  for (const b of built) for (const a of b.log?.artifacts ?? []) if (!owners.has(a.sha256)) owners.set(a.sha256, { artifact: a, runKey: b.key });
  const storedArtifacts = await fetchWhereIn(conn, "artifacts", "sha256", [...owners.keys()]);
  const artifactPlan = diff("artifacts", [], storedArtifacts, (r) => String(r.sha256));
  artifactPlan.unchanged = storedArtifacts.length;
  for (const [sha, { artifact, runKey }] of owners) {
    if (artifactPlan.ids.has(sha)) continue;
    const id = newId();
    artifactPlan.ids.set(sha, id);
    const body: Body = { run: runs.ids.get(runKey)!, kind: artifact.kind, mime: artifact.mime, sha256: sha, byte_size: artifact.bytes.length };
    if (artifact.textRef !== null) body.text_ref = artifact.textRef;
    artifactPlan.creates.push({ id, key: sha, body, files: { blob: new File([new Uint8Array(artifact.bytes)], artifact.filename, { type: artifact.mime }) } });
  }

  // Children, read only for the existing runs in scope that have a parsed log.
  const existingWithLogs = built.filter((b) => b.log && storedByKey.has(b.key)).map((b) => storedByKey.get(b.key)!.id);
  const storedEvents = await fetchWhereIn(conn, "run_events", "run", existingWithLogs);
  const storedCalls = await fetchWhereIn(conn, "tool_calls", "run", existingWithLogs);
  const eventDesired: Desired[] = [];
  const callDesired: Desired[] = [];
  for (const b of built) {
    if (!b.log) continue;
    const runId = runs.ids.get(b.key)!;
    for (const e of b.log.events) eventDesired.push({ key: `${runId}|${e.seq}`, body: childBody(e, EVENT_FIELDS, runId, artifactPlan.ids) });
    for (const t of b.log.toolCalls) callDesired.push({ key: `${runId}|${t.tool_call_id}`, body: childBody(t, TOOL_CALL_FIELDS, runId, artifactPlan.ids) });
  }
  const events = diff("run_events", eventDesired, storedEvents, (r) => `${r.run}|${r.seq}`);
  const calls = diff("tool_calls", callDesired, storedCalls, (r) => `${r.run}|${r.tool_call_id}`);

  const plans: CollectionPlan[] = [runs, artifactPlan, events, calls];
  const lines: string[] = formatWarnings(ledgerWarnings);
  if (warnings.length > 0) lines.push(`linkage warnings (${warnings.length}):`, ...warnings.map((w) => `  - ${w}`));
  if (o.mode === "write") await applyPlans(conn, plans);
  lines.push(...formatPlan(plans, o.mode === "write" ? "applied" : "dry-run"));
  console.log(lines.join("\n"));
  return 0;
}
