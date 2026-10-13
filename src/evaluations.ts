// Evaluation provenance, verdicts and curation: `load-eval-run`,
// `load-verdicts`, `load-curation`, and the offline `compare-verdicts`.
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { canonicalSha256, JsonNumber, JsonSyntaxError, parseJson, plain, sha256Hex } from "./canonical.ts";
import {
  applyPlans, CommandError, connect, diff, fetchAll, fetchWhereIn, formatParseOnly, formatPlan, ValidationError,
  type CollectionPlan, type Connection, type Desired, type Rec,
} from "./store.ts";

const RUN_KINDS = ["mechanical", "judged", "adversarial-review", "adjudication", "comparative", "experiment"];
const RUN_STATUSES = ["planned", "running", "complete", "abandoned"];
const VERDICTS = ["present", "partial", "absent", "not-applicable"];
const COVERAGE_STATUSES = ["covered", "partial", "gap"];
const DISPOSITIONS = ["author", "vendor", "reference", "compare"];
const RELATIONSHIP_KINDS = ["duplicative", "conflicting", "complementary", "precedes", "feeds-into"];
const MECHANICAL = "mechanical-v1";
const JOBS_FRAMEWORK = "hsb3-jobs-to-be-done";
const DATA_DIR = join(import.meta.dir, "..", "data");

export type Mode = "parse-only" | "dry-run" | "write";

type Obj = Record<string, unknown>;

// Collects validation problems, each prefixed by the file it came from.
class Problems {
  readonly list: string[] = [];
  add(where: string, what: string): void {
    this.list.push(`${where}: ${what}`);
  }
  throwIfAny(): void {
    if (this.list.length > 0) throw new ValidationError(this.list);
  }
}

function isObj(v: unknown): v is Obj {
  return v !== null && typeof v === "object" && !Array.isArray(v);
}

// Reads a JSON file keeping number lexemes; returns null after recording a problem.
function readJsonFile(path: string, problems: Problems): { value: unknown; bytes: Uint8Array } | null {
  let bytes: Uint8Array;
  try {
    bytes = new Uint8Array(readFileSync(path));
  } catch (err) {
    problems.add(path, `cannot read: ${err instanceof Error ? err.message : String(err)}`);
    return null;
  }
  try {
    return { value: parseJson(new TextDecoder().decode(bytes)), bytes };
  } catch (err) {
    problems.add(path, `invalid JSON: ${err instanceof Error ? err.message : String(err)}`);
    return null;
  }
}

function str(o: Obj, key: string): string | undefined {
  const v = o[key];
  return typeof v === "string" ? v : undefined;
}

function optionalString(o: Obj, key: string, where: string, problems: Problems, fallback = ""): string {
  const v = o[key];
  if (v === undefined || v === null) return fallback;
  if (typeof v !== "string") {
    problems.add(where, `${key} must be a string`);
    return fallback;
  }
  return v;
}

// Lookups the loaders share: eval runs by id or slug, extenders and elements by slug or name.
class Catalog {
  constructor(
    readonly evalRuns: Rec[],
    readonly frameworks: Rec[],
    readonly extenders: Rec[],
    readonly elements: Rec[],
  ) {}

  static async load(conn: Connection, parts: { elements?: boolean } = {}): Promise<Catalog> {
    return new Catalog(
      await fetchAll(conn, "eval_runs"),
      await fetchAll(conn, "frameworks"),
      await fetchAll(conn, "extenders"),
      parts.elements ? await fetchAll(conn, "framework_elements") : [],
    );
  }

  evalRun(ref: string): Rec | undefined {
    return this.evalRuns.find((r) => r.id === ref) ?? this.evalRuns.find((r) => r.slug === ref);
  }

  framework(slug: string): Rec | undefined {
    return this.frameworks.find((f) => f.slug === slug);
  }

  // An extender by slug, else by name; `problem` explains a miss.
  extender(ref: string): { rec?: Rec; problem?: "retired" | "missing" } {
    const rec = this.extenders.find((e) => e.slug === ref) ?? this.extenders.find((e) => e.name === ref);
    if (!rec) return { problem: "missing" };
    if (rec.retired === true) return { problem: "retired" };
    return { rec };
  }

  elementsOf(frameworkId: string): Rec[] {
    return this.elements.filter((e) => e.framework === frameworkId).sort((a, b) => Number(a.sort_order ?? 0) - Number(b.sort_order ?? 0));
  }

  element(frameworkId: string, ref: string): Rec | undefined {
    const own = this.elementsOf(frameworkId);
    return own.find((e) => e.slug === ref) ?? own.find((e) => e.name === ref);
  }
}

function printPlan(plans: CollectionPlan[], mode: "dry-run" | "applied"): void {
  console.log(formatPlan(plans, mode).join("\n"));
}

// Plans are written only in write mode; the plan block prints either way.
async function finish(conn: Connection, plans: CollectionPlan[], mode: Mode): Promise<number> {
  if (mode === "write") await applyPlans(conn, plans);
  printPlan(plans, mode === "write" ? "applied" : "dry-run");
  return 0;
}

// ---------------------------------------------------------------- load-eval-run

interface Metric {
  value: JsonNumber | number | null;
  available: boolean;
}

interface ResponseInput {
  role: string;
  agentType: string;
  model: string;
  prompt: string;
  responseText: string;
  responseJson: unknown;
  extenders: string[];
  tokens: Metric;
  durationMs: Metric;
}

interface ManifestInput {
  path: string;
  sha256: string;
  slug: string;
  kind: string;
  method: string;
  criteriaText: string;
  frameworks: string[];
  status: string;
  notes: string;
  responses: ResponseInput[];
  linkAssessor: string;
}

function readText(base: string, rel: string, where: string, problems: Problems): string {
  try {
    return readFileSync(resolve(base, rel), "utf8");
  } catch {
    problems.add(where, `cannot read ${rel}`);
    return "";
  }
}

function inlineOrFile(o: Obj, key: string, base: string, where: string, problems: Problems): string {
  const fileKey = `${key}_file`;
  if (o[key] !== undefined && o[key] !== null) return optionalString(o, key, where, problems);
  const rel = o[fileKey];
  if (rel === undefined || rel === null) return "";
  if (typeof rel !== "string") {
    problems.add(where, `${fileKey} must be a string`);
    return "";
  }
  return readText(base, rel, where, problems);
}

// criteria_text inline, else the text of criteria_file.
function criteriaText(run: Obj, base: string, where: string, problems: Problems): string {
  if (run.criteria_text !== undefined && run.criteria_text !== null) return optionalString(run, "criteria_text", where, problems);
  const rel = run.criteria_file;
  if (rel === undefined || rel === null) return "";
  if (typeof rel !== "string") {
    problems.add(where, "run.criteria_file must be a string");
    return "";
  }
  return readText(base, rel, where, problems);
}

function metric(o: Obj, key: string, where: string, problems: Problems): Metric {
  const v = o[key];
  if (v === undefined || v === null) return { value: null, available: false };
  const n = v instanceof JsonNumber ? v.value : typeof v === "number" ? v : NaN;
  if (!Number.isFinite(n) || n < 0) {
    problems.add(where, `${key} must be a finite non-negative number`);
    return { value: null, available: false };
  }
  return { value: v as JsonNumber, available: true };
}

const NON_FINITE = /(^|[^"\w])-?(NaN|Infinity)\b/;

function responseJson(o: Obj, base: string, where: string, problems: Problems): unknown {
  if (o.response_json !== undefined && o.response_json !== null) return o.response_json;
  const rel = o.response_json_file;
  if (rel === undefined || rel === null) return {};
  if (typeof rel !== "string") {
    problems.add(where, "response_json_file must be a string");
    return {};
  }
  const text = readText(base, rel, where, problems);
  try {
    return parseJson(text);
  } catch (err) {
    if (err instanceof JsonSyntaxError && NON_FINITE.test(text)) problems.add(where, "response_json holds NaN or Infinity");
    else problems.add(where, `${rel}: invalid JSON`);
    return {};
  }
}

function readManifest(path: string, problems: Problems): ManifestInput | null {
  const file = readJsonFile(path, problems);
  if (!file) return null;
  const doc = file.value;
  const base = dirname(path);
  if (!isObj(doc) || !isObj(doc.run)) {
    problems.add(path, "run must be an object");
    return null;
  }
  const run = doc.run;
  const slug = str(run, "slug") ?? "";
  const kind = str(run, "kind") ?? "";
  if (!slug) problems.add(path, "run.slug is required");
  if (!RUN_KINDS.includes(kind)) problems.add(path, `run.kind must be one of ${RUN_KINDS.join(", ")}`);
  const status = optionalString(run, "status", path, problems, "complete");
  if (!RUN_STATUSES.includes(status)) problems.add(path, `run.status must be one of ${RUN_STATUSES.join(", ")}`);
  const frameworks = run.frameworks ?? [];
  if (!Array.isArray(frameworks) || frameworks.some((f) => typeof f !== "string")) problems.add(path, "run.frameworks must be a list of slugs");
  const rawResponses = doc.responses ?? [];
  const responses: ResponseInput[] = [];
  if (!Array.isArray(rawResponses)) problems.add(path, "responses must be a list");
  else {
    const roles = new Set<string>();
    rawResponses.forEach((r, i) => {
      const where = `${path}: responses[${i}]`;
      if (!isObj(r)) {
        problems.add(where, "must be an object");
        return;
      }
      const role = str(r, "role") ?? "";
      if (!role) problems.add(where, "role is required");
      else if (roles.has(role)) problems.add(where, `duplicate role ${role}`);
      roles.add(role);
      const extenders = r.extenders ?? [];
      if (!Array.isArray(extenders) || extenders.some((e) => typeof e !== "string")) problems.add(where, "extenders must be a list of slugs");
      else if (extenders.length > 100) problems.add(where, `extenders lists ${extenders.length} slugs (at most 100)`);
      responses.push({
        role,
        agentType: optionalString(r, "agent_type", where, problems),
        model: optionalString(r, "model", where, problems),
        prompt: inlineOrFile(r, "prompt", base, where, problems),
        responseText: inlineOrFile(r, "response_text", base, where, problems),
        responseJson: responseJson(r, base, where, problems),
        extenders: Array.isArray(extenders) ? (extenders as string[]) : [],
        tokens: metric(r, "tokens", where, problems),
        durationMs: metric(r, "duration_ms", where, problems),
      });
    });
  }
  return {
    path,
    sha256: sha256Hex(file.bytes),
    slug,
    kind,
    method: optionalString(run, "method", path, problems),
    criteriaText: criteriaText(run, base, path, problems),
    frameworks: Array.isArray(frameworks) ? (frameworks as string[]) : [],
    status,
    notes: optionalString(run, "notes", path, problems),
    responses,
    linkAssessor: optionalString(doc, "link_assessor", path, problems),
  };
}

function metricValue(m: Metric): number | JsonNumber | null {
  return m.available ? m.value : null;
}

export function responseMeasurement(manifestSha: string, r: ResponseInput): Obj {
  const resolved = {
    role: r.role,
    agent_type: r.agentType,
    model: r.model,
    prompt: r.prompt,
    response_text: r.responseText,
    response_json: r.responseJson,
    extender_slugs: r.extenders,
    tokens: { value: metricValue(r.tokens), available: r.tokens.available },
    duration_ms: { value: metricValue(r.durationMs), available: r.durationMs.available },
  };
  return {
    version: 1,
    source: "eval-run-manifest",
    available: { tokens: r.tokens.available, duration_ms: r.durationMs.available },
    provenance: { tokens: r.tokens.available ? "manifest" : null, duration_ms: r.durationMs.available ? "manifest" : null },
    execution: { validity: "unknown", reason: "manifest does not attest execution validity", preconditions: null },
    source_identity: {
      manifest_file_sha256: manifestSha,
      resolved_response_sha256: canonicalSha256(resolved),
      resolved_response_canonicalization: "json-sorted-keys-utf8",
      revision: { value: null, available: false },
    },
  };
}

export async function loadEvalRun(paths: string[], mode: Mode, env?: Record<string, string | undefined>): Promise<number> {
  const problems = new Problems();
  const manifests = paths.map((p) => readManifest(p, problems)).filter((m): m is ManifestInput => m !== null);
  const slugs = new Map<string, string>();
  const linked = new Map<string, string>();
  for (const m of manifests) {
    if (m.slug && slugs.has(m.slug)) problems.add(m.path, `run ${m.slug} is also loaded by ${slugs.get(m.slug)}`);
    slugs.set(m.slug, m.path);
    if (m.linkAssessor) {
      if (linked.has(m.linkAssessor)) problems.add(m.path, `link_assessor ${m.linkAssessor} is also linked by ${linked.get(m.linkAssessor)}`);
      linked.set(m.linkAssessor, m.path);
    }
  }
  problems.throwIfAny();
  const responseCount = manifests.reduce((n, m) => n + m.responses.length, 0);
  if (mode === "parse-only") {
    console.log(formatParseOnly([["eval_runs", manifests.length], ["eval_responses", responseCount]], []).join("\n"));
    return 0;
  }

  const conn = await connect(env);
  const catalog = await Catalog.load(conn);
  for (const m of manifests) {
    for (const f of m.frameworks) if (!catalog.framework(f)) problems.add(m.path, `unknown framework ${f}`);
    m.responses.forEach((r, i) => {
      for (const slug of r.extenders) {
        const hit = catalog.extender(slug);
        if (hit.problem === "retired") problems.add(`${m.path}: responses[${i}]`, `${slug} (retired)`);
        if (hit.problem === "missing") problems.add(`${m.path}: responses[${i}]`, `${slug} (no such extender)`);
      }
    });
  }
  problems.throwIfAny();

  const runs = diff(
    "eval_runs",
    manifests.map((m) => ({
      key: m.slug,
      body: {
        slug: m.slug, kind: m.kind, method: m.method, criteria_text: m.criteriaText,
        frameworks: m.frameworks.map((f) => catalog.framework(f)!.id), status: m.status, notes: m.notes,
      },
    })),
    catalog.evalRuns,
    (r) => String(r.slug),
  );
  const runSlugOf = new Map(catalog.evalRuns.map((r) => [r.id, String(r.slug)]));
  const storedResponses = await fetchWhereIn(conn, "eval_responses", "run", manifests.map((m) => runs.ids.get(m.slug)!).filter((id) => runSlugOf.has(id)));
  const responseDesired: Desired[] = [];
  for (const m of manifests) {
    for (const r of m.responses) {
      responseDesired.push({
        key: `${m.slug}|${r.role}`,
        body: {
          run: runs.ids.get(m.slug)!, role: r.role, agent_type: r.agentType, model: r.model, prompt: r.prompt,
          response_text: r.responseText, response_json: plain(r.responseJson),
          extenders: r.extenders.map((s) => catalog.extender(s).rec!.id),
          tokens: r.tokens.available ? plain(r.tokens.value) : 0,
          duration_ms: r.durationMs.available ? plain(r.durationMs.value) : 0,
          measurement: plain(responseMeasurement(m.sha256, r)),
        },
      });
    }
  }
  const responses = diff("eval_responses", responseDesired, storedResponses, (r) => `${runSlugOf.get(String(r.run)) ?? r.run}|${r.role}`);
  const plans = [runs, responses];
  if (linked.size > 0) {
    const assessments = diff("assessments", [], [], () => "");
    for (const m of manifests) {
      if (!m.linkAssessor) continue;
      const runId = runs.ids.get(m.slug)!;
      for (const a of await fetchAll(conn, "assessments", conn.pb.filter("assessor = {:a}", { a: m.linkAssessor }))) {
        if (a.eval_run === runId) assessments.unchanged++;
        else assessments.updates.push({ id: a.id, key: `assessment ${a.id}`, body: { eval_run: runId } });
      }
    }
    plans.push(assessments);
  }
  return finish(conn, plans, mode);
}

// ---------------------------------------------------------------- verdict files

interface VerdictRow {
  element: string;
  verdict: string;
  evidence: string;
  score?: number;
}

interface VerdictFile {
  path: string;
  assessor: string;
  framework: string;
  evalRun: string;
  fill: string | null;
  extenders: { extender: string; verdicts: VerdictRow[] }[];
}

function readVerdictFile(path: string, problems: Problems, forLoad: boolean): VerdictFile | null {
  const file = readJsonFile(path, problems);
  if (!file) return null;
  const doc = plain(file.value);
  if (!isObj(doc)) {
    problems.add(path, "must be a JSON object");
    return null;
  }
  const assessor = str(doc, "assessor") ?? "";
  const framework = str(doc, "framework") ?? "";
  const evalRun = str(doc, "eval_run") ?? "";
  if (forLoad) {
    if (!assessor) problems.add(path, "assessor is required");
    else if (assessor === MECHANICAL) problems.add(path, `assessor ${MECHANICAL} is refused (ingest owns it)`);
    if (!evalRun) problems.add(path, "eval_run is required");
  }
  if (!framework) problems.add(path, "framework is required");
  let fill: string | null = null;
  if (doc.fill !== undefined && doc.fill !== null) {
    if (typeof doc.fill === "string" && VERDICTS.includes(doc.fill)) fill = doc.fill;
    else problems.add(path, `fill must be one of ${VERDICTS.join(", ")}`);
  }
  const extenders: VerdictFile["extenders"] = [];
  if (!Array.isArray(doc.extenders)) problems.add(path, "extenders must be a list");
  else {
    const seen = new Set<string>();
    doc.extenders.forEach((e, i) => {
      const where = `${path}: extenders[${i}]`;
      if (!isObj(e) || typeof e.extender !== "string" || !e.extender) {
        problems.add(where, "extender is required");
        return;
      }
      if (seen.has(e.extender)) problems.add(path, `duplicate extender ${e.extender}`);
      seen.add(e.extender);
      const rows: VerdictRow[] = [];
      const elements = new Set<string>();
      const verdicts = e.verdicts ?? [];
      if (!Array.isArray(verdicts)) problems.add(where, "verdicts must be a list");
      else
        verdicts.forEach((v, j) => {
          const at = `${where}.verdicts[${j}]`;
          if (!isObj(v) || typeof v.element !== "string" || !v.element) {
            problems.add(at, "element is required");
            return;
          }
          if (elements.has(v.element)) problems.add(path, `duplicate element ${v.element} for ${e.extender}`);
          elements.add(v.element);
          if (typeof v.verdict !== "string" || !VERDICTS.includes(v.verdict)) problems.add(at, `verdict must be one of ${VERDICTS.join(", ")}`);
          if (v.evidence !== undefined && v.evidence !== null && typeof v.evidence !== "string") problems.add(at, "evidence must be a string");
          if (v.score !== undefined && v.score !== null && (typeof v.score !== "number" || !Number.isFinite(v.score))) problems.add(at, "score must be a number");
          const row: VerdictRow = { element: v.element, verdict: String(v.verdict), evidence: typeof v.evidence === "string" ? v.evidence : "" };
          if (typeof v.score === "number") row.score = v.score;
          rows.push(row);
        });
      extenders.push({ extender: e.extender, verdicts: rows });
    });
  }
  return { path, assessor, framework, evalRun, fill, extenders };
}

function seedElementCount(framework: string): number | null {
  try {
    const seed = JSON.parse(readFileSync(join(DATA_DIR, "frameworks.json"), "utf8"));
    const fw = seed.frameworks.find((f: { slug: string }) => f.slug === framework);
    return fw ? fw.elements.length : null;
  } catch {
    return null;
  }
}

function sameSet(a: string[], b: string[]): { missing: string[]; extra: string[] } {
  const sa = new Set(a);
  const sb = new Set(b);
  return { missing: [...sb].filter((x) => !sa.has(x)).sort(), extra: [...sa].filter((x) => !sb.has(x)).sort() };
}

export interface VerdictOptions {
  extenders?: string[];
  complete?: boolean;
}

export async function loadVerdicts(paths: string[], options: VerdictOptions, mode: Mode, env?: Record<string, string | undefined>): Promise<number> {
  const problems = new Problems();
  const files = paths.map((p) => readVerdictFile(p, problems, true)).filter((f): f is VerdictFile => f !== null);
  problems.throwIfAny();
  const guard = (listed: string[]) => {
    if (!options.extenders) return;
    const { missing, extra } = sameSet(listed, options.extenders);
    for (const x of missing) problems.add("--extenders", `${x} is not in the verdict files`);
    for (const x of extra) problems.add("--extenders", `${x} is in the verdict files but not listed`);
  };

  if (mode === "parse-only") {
    guard([...new Set(files.flatMap((f) => f.extenders.map((e) => e.extender)))]);
    const keys = new Map<string, string>();
    let rows = 0;
    for (const f of files) {
      const perExtender = f.fill ? seedElementCount(f.framework) : null;
      for (const e of f.extenders) {
        rows += perExtender ?? e.verdicts.length;
        for (const v of e.verdicts) {
          const key = `${e.extender}|${f.framework}|${v.element}|${f.assessor}`;
          if (keys.has(key) && keys.get(key) !== f.path) problems.add(f.path, `${e.extender} ${v.element} is also given by ${keys.get(key)}`);
          keys.set(key, f.path);
        }
      }
    }
    problems.throwIfAny();
    console.log(formatParseOnly([["assessments", rows]], []).join("\n"));
    return 0;
  }

  const conn = await connect(env);
  const catalog = await Catalog.load(conn, { elements: true });
  const desired: Desired[] = [];
  const keys = new Map<string, string>();
  const listed = new Set<string>();
  for (const f of files) {
    const fw = catalog.framework(f.framework);
    const run = catalog.evalRun(f.evalRun);
    if (!fw) problems.add(f.path, `unknown framework ${f.framework}`);
    if (!run) problems.add(f.path, `unknown eval_run ${f.evalRun}`);
    for (const e of f.extenders) {
      const hit = catalog.extender(e.extender);
      if (hit.problem) {
        problems.add(f.path, `unknown extender ${e.extender} (${hit.problem === "retired" ? "retired" : "not in DB"})`);
        continue;
      }
      const ext = hit.rec!;
      listed.add(String(ext.slug));
      if (!fw || !run) continue;
      const given = new Map<string, VerdictRow>();
      for (const v of e.verdicts) {
        const el = catalog.element(fw.id, v.element);
        if (!el) problems.add(f.path, `element ${v.element} is not in framework ${f.framework}`);
        else given.set(el.id, v);
      }
      const elements = f.fill ? catalog.elementsOf(fw.id) : [...given.keys()].map((id) => catalog.elements.find((x) => x.id === id)!);
      for (const el of elements) {
        const v = given.get(el.id) ?? { element: String(el.slug), verdict: f.fill!, evidence: "" };
        const key = `${ext.slug}|${f.framework}|${el.slug}|${f.assessor}`;
        if (keys.has(key)) {
          if (keys.get(key) !== f.path) problems.add(f.path, `${ext.slug} ${el.slug} is also given by ${keys.get(key)}`);
          continue;
        }
        keys.set(key, f.path);
        const body: Obj = {
          extender: ext.id, framework: fw.id, element: el.id, eval_run: run.id, verdict: v.verdict, evidence: v.evidence, assessor: f.assessor,
        };
        if (v.score !== undefined) body.score = v.score;
        desired.push({ key, body });
      }
    }
  }
  guard([...listed]);
  if (options.complete) {
    for (const e of catalog.extenders) {
      if (e.retired !== true && !listed.has(String(e.slug))) problems.add("--complete", `extender ${e.slug} is not listed`);
    }
  }
  problems.throwIfAny();

  const assessors = [...new Set(files.map((f) => f.assessor))];
  const stored: Rec[] = [];
  for (const a of assessors) stored.push(...(await fetchAll(conn, "assessments", conn.pb.filter("assessor = {:a}", { a }))));
  const slugOf = new Map(catalog.extenders.map((e) => [e.id, String(e.slug)]));
  const fwSlugOf = new Map(catalog.frameworks.map((f) => [f.id, String(f.slug)]));
  const elSlugOf = new Map(catalog.elements.map((e) => [e.id, String(e.slug)]));
  const plan = diff(
    "assessments",
    desired,
    stored,
    (r) => `${slugOf.get(String(r.extender)) ?? r.extender}|${fwSlugOf.get(String(r.framework)) ?? r.framework}|${elSlugOf.get(String(r.element)) ?? r.element}|${r.assessor}`,
  );
  return finish(conn, [plan], mode);
}

// Python's round(): halves go to the even neighbour.
function roundHalfEven(x: number): number {
  const f = Math.floor(x);
  const diffToFloor = x - f;
  if (Math.abs(diffToFloor - 0.5) < 1e-9) return f % 2 === 0 ? f : f + 1;
  return Math.round(x);
}

interface Side {
  verdicts: Map<string, Map<string, string>>; // "framework extender" -> element -> verdict
  fills: Map<string, string | null>;
}

function expandSide(paths: string[], problems: Problems): Side {
  const side: Side = { verdicts: new Map(), fills: new Map() };
  for (const p of paths) {
    const f = readVerdictFile(p, problems, false);
    if (!f) continue;
    for (const e of f.extenders) {
      const key = `${f.framework} ${e.extender}`;
      if (side.verdicts.has(key)) {
        problems.add(p, `${f.framework} ${e.extender} is given twice on the same side`);
        continue;
      }
      side.verdicts.set(key, new Map(e.verdicts.map((v) => [v.element, v.verdict])));
      side.fills.set(key, f.fill);
    }
  }
  return side;
}

export function compareVerdicts(left: string[], right: string[]): number {
  const problems = new Problems();
  const l = expandSide(left, problems);
  const r = expandSide(right, problems);
  problems.throwIfAny();
  const shared = [...l.verdicts.keys()].filter((k) => r.verdicts.has(k));
  if (shared.length === 0) throw new CommandError("no overlapping extenders");
  const lines: string[] = [];
  let agree = 0;
  let total = 0;
  for (const key of shared) {
    const lv = l.verdicts.get(key)!;
    const rv = r.verdicts.get(key)!;
    for (const element of new Set([...lv.keys(), ...rv.keys()])) {
      const a = lv.get(element) ?? l.fills.get(key) ?? null;
      const b = rv.get(element) ?? r.fills.get(key) ?? null;
      if (a === null || b === null) continue;
      total++;
      if (a === b) agree++;
      else lines.push(`${key} ${element}: left=${a} right=${b}`);
    }
  }
  if (total === 0) throw new CommandError("no overlapping verdicts");
  lines.sort();
  lines.push(`verdict agreement: ${agree}/${total} (${roundHalfEven((100 * agree) / total)}%)`);
  console.log(lines.join("\n"));
  return 0;
}

// ---------------------------------------------------------------- curation

interface CoverageRow {
  job: string;
  status: string;
  disposition: string;
  source: string;
  rationale: string;
}
interface RelationshipRow {
  a: string;
  b: string;
  kind: string;
  job: string;
  evidence: string;
  assessor: string;
}

function readCuration(path: string, problems: Problems) {
  const file = readJsonFile(path, problems);
  if (!file) return null;
  const doc = plain(file.value);
  if (!isObj(doc)) {
    problems.add(path, "must be a JSON object");
    return null;
  }
  const evalRun = str(doc, "eval_run") ?? "";
  if (!evalRun) problems.add(path, "eval_run is required");
  const framework = optionalString(doc, "framework", path, problems, JOBS_FRAMEWORK) || JOBS_FRAMEWORK;
  const coverage: CoverageRow[] = [];
  const relationships: RelationshipRow[] = [];
  const seen = new Set<string>();
  const list = (key: string): unknown[] => {
    const v = doc[key] ?? [];
    if (!Array.isArray(v)) {
      problems.add(path, `${key} must be a list`);
      return [];
    }
    return v;
  };
  list("job_coverage").forEach((row, i) => {
    const where = `${path}: job_coverage[${i}]`;
    if (!isObj(row)) return problems.add(where, "must be an object");
    const r: CoverageRow = {
      job: optionalString(row, "job", where, problems),
      status: optionalString(row, "status", where, problems),
      disposition: optionalString(row, "disposition", where, problems),
      source: optionalString(row, "source", where, problems),
      rationale: optionalString(row, "rationale", where, problems),
    };
    if (!r.job) problems.add(where, "job is required");
    if (r.status && !COVERAGE_STATUSES.includes(r.status)) problems.add(where, `status must be one of ${COVERAGE_STATUSES.join(", ")}`);
    if (r.disposition && !DISPOSITIONS.includes(r.disposition)) problems.add(where, `disposition must be one of ${DISPOSITIONS.join(", ")}`);
    if (seen.has(`job ${r.job}`)) problems.add(where, `duplicate job ${r.job}`);
    seen.add(`job ${r.job}`);
    coverage.push(r);
  });
  list("relationships").forEach((row, i) => {
    const where = `${path}: relationships[${i}]`;
    if (!isObj(row)) return problems.add(where, "must be an object");
    const r: RelationshipRow = {
      a: optionalString(row, "extender_a", where, problems),
      b: optionalString(row, "extender_b", where, problems),
      kind: optionalString(row, "kind", where, problems),
      job: optionalString(row, "job", where, problems),
      evidence: optionalString(row, "evidence", where, problems),
      assessor: optionalString(row, "assessor", where, problems),
    };
    if (!r.a || !r.b) problems.add(where, "extender_a and extender_b are required");
    if (!RELATIONSHIP_KINDS.includes(r.kind)) problems.add(where, `kind must be one of ${RELATIONSHIP_KINDS.join(", ")}`);
    const key = `rel ${r.a}|${r.b}|${r.kind}|${r.job}`;
    if (seen.has(key)) problems.add(where, `duplicate relationship ${r.a} ${r.b} ${r.kind}${r.job ? ` ${r.job}` : ""}`);
    seen.add(key);
    relationships.push(r);
  });
  return { evalRun, framework, coverage, relationships };
}

export async function loadCuration(path: string, mode: Mode, env?: Record<string, string | undefined>): Promise<number> {
  const problems = new Problems();
  const cur = readCuration(path, problems);
  problems.throwIfAny();
  if (!cur) return 1;
  if (mode === "parse-only") {
    console.log(formatParseOnly([["job_coverage", cur.coverage.length], ["relationships", cur.relationships.length]], []).join("\n"));
    return 0;
  }
  const conn = await connect(env);
  const catalog = await Catalog.load(conn, { elements: true });
  const sources = await fetchAll(conn, "sources");
  const run = catalog.evalRun(cur.evalRun);
  const fw = catalog.framework(cur.framework);
  if (!run) problems.add(path, `unknown eval_run ${cur.evalRun}`);
  if (!fw) problems.add(path, `unknown framework ${cur.framework}`);
  const job = (slug: string, where: string): Rec | undefined => {
    if (!fw) return undefined;
    const el = catalog.elementsOf(fw.id).find((e) => e.slug === slug);
    if (!el) problems.add(where, `job ${slug} is not in framework ${cur.framework}`);
    return el;
  };
  const extender = (ref: string, where: string): Rec | undefined => {
    const hit = catalog.extender(ref);
    if (hit.problem) problems.add(where, `unknown extender ${ref} (${hit.problem === "retired" ? "retired" : "not in DB"})`);
    return hit.rec;
  };
  const coverage: Desired[] = [];
  cur.coverage.forEach((r, i) => {
    const where = `${path}: job_coverage[${i}]`;
    const el = job(r.job, where);
    const source = r.source ? sources.find((s) => s.slug === r.source) : undefined;
    if (r.source && !source) problems.add(where, `unknown source ${r.source}`);
    if (el && run) {
      coverage.push({
        key: r.job,
        body: { job: el.id, status: r.status, disposition: r.disposition, source: source?.id ?? "", rationale: r.rationale, eval_run: run.id },
      });
    }
  });
  const relationships: Desired[] = [];
  cur.relationships.forEach((r, i) => {
    const where = `${path}: relationships[${i}]`;
    const a = extender(r.a, where);
    const b = extender(r.b, where);
    const el = r.job ? job(r.job, where) : undefined;
    if (a && b && run && (!r.job || el)) {
      relationships.push({
        key: `${a.id}|${b.id}|${r.kind}|${el?.id ?? ""}`,
        body: { extender_a: a.id, extender_b: b.id, kind: r.kind, job: el?.id ?? "", evidence: r.evidence, assessor: r.assessor, eval_run: run.id },
      });
    }
  });
  problems.throwIfAny();

  const storedCoverage = await fetchWhereIn(conn, "job_coverage", "job", coverage.map((d) => String(d.body.job)));
  const jobSlugOf = new Map(catalog.elements.map((e) => [e.id, String(e.slug)]));
  const coveragePlan = diff("job_coverage", coverage, storedCoverage, (r) => jobSlugOf.get(String(r.job)) ?? String(r.job));
  const storedRelationships = (await fetchWhereIn(conn, "relationships", "extender_a", relationships.map((d) => String(d.body.extender_a)))).filter((r) =>
    relationships.some((d) => d.key === `${r.extender_a}|${r.extender_b}|${r.kind}|${r.job ?? ""}`),
  );
  const relationshipPlan = diff("relationships", relationships, storedRelationships, (r) => `${r.extender_a}|${r.extender_b}|${r.kind}|${r.job ?? ""}`);
  return finish(conn, [coveragePlan, relationshipPlan], mode);
}
