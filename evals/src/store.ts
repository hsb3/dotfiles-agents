// The CLI's PocketBase access: one superuser connection, whole-collection reads,
// json coercion, idempotent diffing by natural key, the plan block and writes.
import PocketBase, { ClientResponseError } from "pocketbase";
import { canonicalJson } from "./canonical.ts";

export class CommandError extends Error {}

// Several problems found while validating input; nothing is written.
export class ValidationError extends Error {
  constructor(readonly problems: string[]) {
    super(problems.join("\n"));
  }
}

export type Rec = Record<string, unknown> & { id: string };
export type Body = Record<string, unknown>;

// How a field compares: text-like (text, one select, one relation), number,
// bool, json, multi (several selects or relations), file (never compared).
type Kind = "t" | "n" | "b" | "j" | "m" | "f";

const SCHEMA: Record<string, string> = {
  frameworks: "slug:t name:t source_org:t source_url:t kind:t applies_to:m summary:t status:t notes:t",
  sources:
    "slug:t name:t url:t publisher_kind:t publishes:m trust_tier:t publishes_evals:b maintenance:t license:t adoption_signal:t rationale:t evidence_url:t status:t notes:t",
  extenders:
    "slug:t name:t kind:t description:t origin:t upstream:t upstream_ref:t repo_path:t source:t shelf:t disposition:t requires:j assumes:j frontmatter:j body:t entry_file:t file_count:n total_bytes:n word_count:n notes:t retired:b",
  framework_elements: "framework:t slug:t name:t element_kind:t description:t criteria:t category:t sort_order:n",
  files: "extender:t relpath:t role:t content:t is_binary:b size_bytes:n sha256:t language:t",
  distributions: "slug:t kind:t version:t description:t members:m",
  frontmatter_dimensions: "key:t applies_to:t requirement:t description:t spec_framework:t observed_count:n",
  eval_runs: "slug:t kind:t method:t criteria_text:t frameworks:m status:t notes:t",
  eval_responses:
    "run:t role:t agent_type:t model:t prompt:t response_text:t response_json:j extenders:m tokens:n duration_ms:n measurement:j",
  assessments: "extender:t framework:t element:t eval_run:t verdict:t score:n evidence:t assessor:t",
  job_coverage: "job:t disposition:t status:t source:t rationale:t eval_run:t",
  relationships: "extender_a:t extender_b:t kind:t job:t evidence:t assessor:t eval_run:t",
  runs:
    "harness:t era:t campaign:t candidate:t case:t config:t kind:t trial:n model:t grader_model:t cli_version:t session_id:t passed:b skill_used:b exit_code:n num_turns:n cost_usd:n duration_ms:n input_tokens:n output_tokens:n cache_creation_tokens:n cache_read_tokens:n error:t workspace:t checks:j grades:j tool_names:j model_usage:j provenance:j measurement:j log_path:t ts:t",
  artifacts: "run:t kind:t mime:t blob:f sha256:t byte_size:n text_ref:t",
  run_events:
    "run:t seq:n ts:n vendor:t role:t event_type:t tool_name:t tool_call_id:t status:t is_error:b input_tokens:n output_tokens:n cache_read_tokens:n cache_write_tokens:n cost_usd:n wallclock_ms:n text:t payload:j artifact:t",
  tool_calls:
    "run:t tool_call_id:t tool_name:t input:j output:j status:t is_error:b wallclock_ms:n started_ts:n artifact:t",
};

const KINDS: Record<string, Record<string, Kind>> = {};
for (const [collection, spec] of Object.entries(SCHEMA)) {
  KINDS[collection] = {};
  for (const part of spec.split(" ")) {
    const [field, kind] = part.split(":") as [string, Kind];
    KINDS[collection]![field] = kind;
  }
}

function kindOf(collection: string, field: string): Kind {
  const kind = KINDS[collection]?.[field];
  if (!kind) throw new Error(`unknown field ${collection}.${field}`);
  return kind;
}

const JSON_FIRST = new Set(["{", "[", '"', "-", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "t", "f", "n"]);

// What PocketBase stores for a value sent to a json field: a string whose
// untrimmed first character can start JSON, and that parses whole, is stored parsed.
export function coerceJson(value: unknown): unknown {
  if (typeof value !== "string" || value === "" || !JSON_FIRST.has(value[0]!)) return value;
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

// Applies coerceJson to every json field of a body.
export function coerceBody(collection: string, body: Body): Body {
  const out: Body = {};
  for (const [field, value] of Object.entries(body)) {
    out[field] = kindOf(collection, field) === "j" ? coerceJson(value) : value;
  }
  return out;
}

// A value as text: missing and null are "".
export function textOf(v: unknown): string {
  return v === undefined || v === null ? "" : String(v);
}

function listOf(v: unknown): unknown[] {
  if (v === undefined || v === null || v === "") return [];
  return Array.isArray(v) ? v : [v];
}

// Whether a sent value equals the stored one under the idempotence rules.
export function sameValue(collection: string, field: string, sent: unknown, stored: unknown): boolean {
  switch (kindOf(collection, field)) {
    case "t":
      return textOf(sent) === textOf(stored);
    case "n":
      return Number(sent ?? 0) === Number(stored ?? 0);
    case "b":
      return (sent ?? false) === (stored ?? false);
    case "m": {
      const a = listOf(sent);
      const b = listOf(stored);
      return a.length === b.length && a.every((x, i) => textOf(x) === textOf(b[i]));
    }
    case "j":
      return canonicalJson(coerceJson(sent) ?? null) === canonicalJson(stored ?? null);
    case "f":
      return true;
  }
}

// A PocketBase record id, assigned client-side so a plan can link records
// that do not exist yet.
export function newId(): string {
  const alphabet = "abcdefghijklmnopqrstuvwxyz0123456789";
  const bytes = crypto.getRandomValues(new Uint8Array(15));
  let id = "";
  for (const b of bytes) id += alphabet[b % 36];
  return id;
}

export interface Desired {
  key: string; // the natural key, printed when a write fails
  body: Body;
}

export interface PlannedCreate {
  id: string;
  key: string;
  body: Body;
  files?: Record<string, File>; // multipart file fields
}

export interface PlannedUpdate {
  id: string;
  key: string;
  body: Body;
}

export interface CollectionPlan {
  collection: string;
  creates: PlannedCreate[];
  updates: PlannedUpdate[];
  unchanged: number;
  deletes: { id: string; key: string }[];
  retires: PlannedUpdate[];
  showDelete: boolean;
  showRetire: boolean;
  ids: Map<string, string>; // natural key -> record id, existing and planned
}

export function emptyPlan(collection: string, extra: { showDelete?: boolean; showRetire?: boolean } = {}): CollectionPlan {
  return {
    collection,
    creates: [],
    updates: [],
    unchanged: 0,
    deletes: [],
    retires: [],
    showDelete: extra.showDelete ?? false,
    showRetire: extra.showRetire ?? false,
    ids: new Map(),
  };
}

export interface DiffOptions {
  // Fields not to compare for one record (still sent).
  skip?: (field: string, desired: Desired, stored: Rec) => boolean;
  showDelete?: boolean;
  showRetire?: boolean;
}

// Compares desired records with stored ones by natural key: a missing record is
// a create (with a new id), a differing one an update, the rest unchanged.
// Stored records with no desired counterpart are left alone.
export function diff(
  collection: string,
  desired: Desired[],
  existing: Rec[],
  keyOf: (stored: Rec) => string,
  options: DiffOptions = {},
): CollectionPlan {
  const plan = emptyPlan(collection, options);
  const byKey = new Map<string, Rec>();
  for (const rec of existing) {
    const key = keyOf(rec);
    byKey.set(key, rec);
    plan.ids.set(key, rec.id);
  }
  for (const d of desired) {
    const stored = byKey.get(d.key);
    if (!stored) {
      const id = newId();
      plan.ids.set(d.key, id);
      plan.creates.push({ id, key: d.key, body: coerceBody(collection, d.body) });
      continue;
    }
    const changed = Object.keys(d.body).some(
      (field) => !options.skip?.(field, d, stored) && !sameValue(collection, field, d.body[field], stored[field]),
    );
    if (changed) plan.updates.push({ id: stored.id, key: d.key, body: coerceBody(collection, d.body) });
    else plan.unchanged++;
  }
  return plan;
}

export function formatPlan(plans: CollectionPlan[], mode: "dry-run" | "applied"): string[] {
  const lines = [mode === "dry-run" ? "[dry-run] plan (create / update / unchanged):" : "applied (create / update / unchanged):"];
  for (const p of plans) {
    let line = `  ${p.collection} ${p.creates.length} create / ${p.updates.length} update / ${p.unchanged} unchanged`;
    if (p.showDelete) line += ` / ${p.deletes.length} delete`;
    if (p.showRetire) line += ` / ${p.retires.length} retire`;
    lines.push(line);
  }
  if (mode === "dry-run") lines.push("  no writes made");
  return lines;
}

export function formatParseOnly(counts: [string, number][], warnings: string[]): string[] {
  const lines = ["[parse-only] planned records (no DB connection):"];
  for (const [collection, n] of counts) lines.push(`  ${collection}: ${n}`);
  lines.push(...formatWarnings(warnings));
  return lines;
}

export function formatWarnings(warnings: string[]): string[] {
  if (warnings.length === 0) return [];
  return [`warnings (${warnings.length}):`, ...warnings.map((w) => `  - ${w}`)];
}

function pbMessage(err: unknown): string {
  if (err instanceof ClientResponseError) {
    const data = err.response?.data as Record<string, { message?: string }> | undefined;
    const details = data
      ? Object.entries(data)
          .map(([field, v]) => `${field}: ${v?.message ?? JSON.stringify(v)}`)
          .join("; ")
      : "";
    return `${err.response?.message ?? err.message}${details ? ` (${details})` : ""}`;
  }
  return err instanceof Error ? err.message : String(err);
}

export interface Connection {
  pb: PocketBase;
  url: string;
}

// Reads PB_URL, PB_ADMIN_EMAIL and PB_ADMIN_PASSWORD and authenticates once as
// superuser, retrying a 429 after 1.5 s up to 3 times.
export async function connect(env: Record<string, string | undefined> = process.env): Promise<Connection> {
  const missing = ["PB_ADMIN_EMAIL", "PB_ADMIN_PASSWORD"].filter((name) => !env[name]);
  if (missing.length > 0) throw new CommandError(`missing environment variable${missing.length > 1 ? "s" : ""} ${missing.join(" and ")}`);
  const url = env.PB_URL || "http://127.0.0.1:8090";
  const pb = new PocketBase(url);
  pb.autoCancellation(false);
  for (let attempt = 0; ; attempt++) {
    try {
      await pb.collection("_superusers").authWithPassword(env.PB_ADMIN_EMAIL!, env.PB_ADMIN_PASSWORD!);
      return { pb, url };
    } catch (err) {
      if (err instanceof ClientResponseError && err.status === 429 && attempt < 3) {
        await Bun.sleep(1500);
        continue;
      }
      throw new CommandError(`cannot authenticate to ${url}: ${pbMessage(err)}`);
    }
  }
}

// Every record of a collection matching an optional filter.
export async function fetchAll(conn: Connection, collection: string, filter?: string): Promise<Rec[]> {
  try {
    return (await conn.pb.collection(collection).getFullList({ batch: 500, sort: "id", filter, skipTotal: true })) as Rec[];
  } catch (err) {
    throw new CommandError(`cannot read ${collection}: ${pbMessage(err)}`);
  }
}

// Records of a collection whose field equals one of the values, read in chunks
// so the filter stays short.
export async function fetchWhereIn(conn: Connection, collection: string, field: string, values: string[]): Promise<Rec[]> {
  const unique = [...new Set(values)];
  const out: Rec[] = [];
  for (let i = 0; i < unique.length; i += 40) {
    const params: Record<string, string> = {};
    const expr = unique.slice(i, i + 40).map((v, j) => {
      params[`v${j}`] = v;
      return `${field} = {:v${j}}`;
    });
    out.push(...(await fetchAll(conn, collection, conn.pb.filter(expr.join(" || "), params))));
  }
  return out;
}

const CONCURRENCY = 8;

async function runBounded<T>(items: T[], work: (item: T) => Promise<void>): Promise<void> {
  let next = 0;
  let failure: unknown = null;
  const worker = async () => {
    while (failure === null && next < items.length) {
      const item = items[next++]!;
      try {
        await work(item);
      } catch (err) {
        if (failure === null) failure = err;
      }
    }
  };
  await Promise.all(Array.from({ length: Math.min(CONCURRENCY, items.length) }, worker));
  if (failure !== null) throw failure;
}

function writeError(collection: string, key: string, err: unknown): CommandError {
  return new CommandError(`write failed in ${collection} for ${key}: ${pbMessage(err)}`);
}

// Writes each plan in order: creates, updates and retires, then deletes. The
// first failure stops the command naming the collection, key and message.
export async function applyPlans(conn: Connection, plans: CollectionPlan[]): Promise<void> {
  for (const plan of plans) {
    const records = conn.pb.collection(plan.collection);
    await runBounded(plan.creates, async (c) => {
      try {
        if (c.files) {
          const form = new FormData();
          form.set("id", c.id);
          for (const [field, value] of Object.entries(c.body)) {
            if (value === undefined || value === null) continue;
            form.set(field, typeof value === "string" ? value : JSON.stringify(value));
          }
          for (const [field, file] of Object.entries(c.files)) form.set(field, file);
          await records.create(form);
        } else {
          await records.create({ id: c.id, ...c.body });
        }
      } catch (err) {
        throw writeError(plan.collection, c.key, err);
      }
    });
    await runBounded([...plan.updates, ...plan.retires], async (u) => {
      try {
        await records.update(u.id, u.body);
      } catch (err) {
        throw writeError(plan.collection, u.key, err);
      }
    });
    await runBounded(plan.deletes, async (d) => {
      try {
        await records.delete(d.id);
      } catch (err) {
        throw writeError(plan.collection, d.key, err);
      }
    });
  }
}

// PocketBase's filter escaping for a literal value.
export function filterLiteral(conn: Connection, expr: string, params: Record<string, unknown>): string {
  return conn.pb.filter(expr, params);
}
