// `evals report`: renders coverage-matrix.md and analysis.md from the database
// or from JSON dumps of its collections, deterministically.
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { compareCodePoints } from "./canonical.ts";
import { CommandError, connect, fetchAll, textOf as text, type Rec } from "./store.ts";

const COLLECTIONS = ["frameworks", "framework_elements", "extenders", "sources", "job_coverage", "relationships", "assessments", "eval_runs"] as const;
type Collection = (typeof COLLECTIONS)[number];
type Data = Record<Collection, Rec[]>;

const JOBS = "hsb3-jobs-to-be-done";
const COVERAGE = "coverage-v1";
const ASSESSORS = ["mechanical-v1", "judged-v1", "coverage-v1"];
const LISTED_KINDS = ["duplicative", "conflicting", "precedes", "feeds-into"];

const byText = (a: string, b: string) => compareCodePoints(a, b);

// A table cell: `|` escaped, newlines as spaces.
function cell(v: unknown): string {
  return text(v).replace(/\r\n|\r|\n/g, " ").replace(/\|/g, "\\|");
}

function oneLine(v: unknown): string {
  return text(v).replace(/\r\n|\r|\n/g, " ");
}

function compareTuples(a: string[], b: string[]): number {
  for (let i = 0; i < Math.min(a.length, b.length); i++) {
    const c = byText(a[i]!, b[i]!);
    if (c !== 0) return c;
  }
  return a.length - b.length;
}

async function loadData(fixtures: string | undefined, env?: Record<string, string | undefined>): Promise<Data> {
  const data = {} as Data;
  if (fixtures !== undefined) {
    for (const c of COLLECTIONS) {
      const path = join(fixtures, `${c}.json`);
      if (!existsSync(path)) throw new CommandError(`missing fixture ${path}`);
      let parsed: unknown;
      try {
        parsed = JSON.parse(readFileSync(path, "utf8"));
      } catch (err) {
        throw new CommandError(`${path}: invalid JSON: ${err instanceof Error ? err.message : String(err)}`);
      }
      if (!Array.isArray(parsed)) throw new CommandError(`${path}: not a JSON array`);
      data[c] = parsed as Rec[];
    }
    return data;
  }
  const conn = await connect(env);
  for (const c of COLLECTIONS) data[c] = await fetchAll(conn, c);
  return data;
}

interface Model {
  jobs: Rec[];
  families: string[];
  live: Rec[]; // live extenders, by slug
  liveIds: Set<string>;
  slugOf: Map<string, string>;
  retired: number;
  assessments: Rec[]; // live
  suppressedAssessments: number;
  relationships: Rec[]; // live
  suppressedRelationships: number;
  coverageRows: Rec[];
  coverageByJob: Map<string, Rec>;
  runSlugOf: Map<string, string>;
  sourceSlugOf: Map<string, string>;
}

function buildModel(d: Data): Model {
  const framework = d.frameworks.find((f) => f.slug === JOBS);
  if (!framework) throw new CommandError(`framework ${JOBS} is missing`);
  const jobs = d.framework_elements
    .filter((e) => e.framework === framework.id)
    .sort((a, b) => Number(a.sort_order ?? 0) - Number(b.sort_order ?? 0) || byText(text(a.slug), text(b.slug)));
  const live = d.extenders.filter((e) => e.retired !== true).sort((a, b) => byText(text(a.slug), text(b.slug)));
  const liveIds = new Set(live.map((e) => e.id));
  const assessments = d.assessments.filter((a) => liveIds.has(text(a.extender)));
  const relationships = d.relationships.filter((r) => liveIds.has(text(r.extender_a)) && liveIds.has(text(r.extender_b)));
  const jobIds = new Set(jobs.map((j) => j.id));
  return {
    jobs,
    families: [...new Set(jobs.map((j) => text(j.category)))].sort(byText),
    live,
    liveIds,
    slugOf: new Map(d.extenders.map((e) => [e.id, text(e.slug)])),
    retired: d.extenders.length - live.length,
    assessments,
    suppressedAssessments: d.assessments.length - assessments.length,
    relationships,
    suppressedRelationships: d.relationships.length - relationships.length,
    coverageRows: assessments.filter((a) => a.assessor === COVERAGE && a.framework === framework.id && jobIds.has(text(a.element))),
    coverageByJob: new Map(d.job_coverage.map((c) => [text(c.job), c])),
    runSlugOf: new Map(d.eval_runs.map((r) => [r.id, text(r.slug)])),
    sourceSlugOf: new Map(d.sources.map((s) => [s.id, text(s.slug)])),
  };
}

function scopeParagraph(m: Model): string {
  return (
    `Retired units excluded: **${m.retired}**. Suppressed rows: **${m.suppressedAssessments} assessments**, **${m.suppressedRelationships} relationships**. ` +
    "Counts cover all fetched rows, before section-specific filtering. Assessments and relationships referencing retired or missing extenders are excluded; " +
    "each relationship counts once even if both endpoints are excluded. Stored history is retained; eval-run linked-row counts reflect this active projection."
  );
}

function slugs(m: Model, ids: string[]): string[] {
  return [...new Set(ids.map((id) => m.slugOf.get(id) ?? id))].sort(byText);
}

function slugList(m: Model, ids: string[]): string {
  const list = slugs(m, ids);
  return list.length > 0 ? list.join(", ") : "—";
}

function pair(m: Model, r: Rec): [string, string] {
  return [m.slugOf.get(text(r.extender_a)) ?? text(r.extender_a), m.slugOf.get(text(r.extender_b)) ?? text(r.extender_b)];
}

function coverageMatrix(d: Data, m: Model): { body: string; gaps: number; partial: number } {
  const lines: string[] = [];
  const provenance = new Set<string>();
  for (const r of [...m.coverageRows, ...d.job_coverage, ...m.relationships]) {
    const slug = m.runSlugOf.get(text(r.eval_run));
    if (slug) provenance.add(slug);
  }
  const prov = [...provenance].sort(byText).map((s) => `\`${s}\``);
  lines.push(
    "# Extender coverage matrix — jobs-to-be-done",
    "",
    "_Generated by `evals report` — do not hand-edit. Truth lives in the database",
    "(assessor `coverage-v1` assessments + `job_coverage` + `relationships`);",
    "this file is a rendered snapshot for reading and diff review._",
    "",
    `Framework: \`${JOBS}\` (${m.jobs.length} jobs, ${m.families.length} families) x ${m.live.length} extenders.`,
    `Provenance: eval_runs ${prov.length > 0 ? prov.join(", ") : "none"}.`,
    "",
    scopeParagraph(m),
    "",
    "## Matrix",
    "",
    "| Job | Family | Status | Present | Partial | Disposition | Source |",
    "|---|---|---|---|---|---|---|",
  );
  let gaps = 0;
  let partial = 0;
  const gapLines: string[] = [];
  for (const job of m.jobs) {
    const jc = m.coverageByJob.get(job.id);
    const rows = m.coverageRows.filter((a) => a.element === job.id);
    const present = rows.filter((a) => a.verdict === "present").map((a) => text(a.extender));
    const part = rows.filter((a) => a.verdict === "partial").map((a) => text(a.extender));
    const status = text(jc?.status);
    const disposition = text(jc?.disposition) || "?";
    const source = m.sourceSlugOf.get(text(jc?.source)) ?? "";
    lines.push(
      `| \`${cell(job.slug)}\` | ${cell(job.category)} | **${cell(status || "?")}** | ${cell(slugList(m, present))} | ${cell(slugList(m, part))} | ${cell(disposition)} | ${cell(source || "—")} |`,
    );
    if (status === "gap") gaps++;
    if (status === "partial") partial++;
    if (status === "gap" || status === "partial") gapLines.push(`- **\`${text(job.slug)}\`** (${status}, disposition ${disposition}): ${oneLine(jc?.rationale)}`);
  }
  lines.push("", "## Gaps and partial coverage", "");
  lines.push(...(gapLines.length > 0 ? gapLines : ["_None._"]));
  lines.push("", "## Relationships", "", "| Kind | Count |", "|---|---|");
  const counts = new Map<string, number>();
  for (const r of m.relationships) counts.set(text(r.kind), (counts.get(text(r.kind)) ?? 0) + 1);
  for (const kind of [...counts.keys()].sort(byText)) lines.push(`| ${cell(kind)} | ${counts.get(kind)} |`);
  const section = (kind: string, title: string, sep: string) => {
    const pairs = m.relationships
      .filter((r) => r.kind === kind)
      .map((r) => ({ p: pair(m, r), evidence: oneLine(r.evidence) }))
      .sort((x, y) => compareTuples(x.p, y.p));
    if (pairs.length === 0) return;
    lines.push("", `### ${title}`, "", ...pairs.map(({ p, evidence }) => `- ${p[0]} ${sep} ${p[1]}: ${evidence}`));
  };
  section("duplicative", "Duplicative pairs (M3 coalesce candidates)", "=");
  section("conflicting", "Conflicting pairs", "x");
  const directed = m.relationships
    .filter((r) => r.kind === "precedes" || r.kind === "feeds-into")
    .map((r) => {
      const [a, b] = pair(m, r);
      return { a, b, kind: text(r.kind) };
    })
    .sort((x, y) => compareTuples([x.a, x.kind, x.b], [y.a, y.kind, y.b]));
  lines.push("", "### Directed hand-off links (composition-planner substrate, EDB-22)", "");
  lines.push(...(directed.length > 0 ? directed.map((r) => `- ${r.a} ${r.kind === "precedes" ? "->" : "=>"} ${r.b} (${r.kind})`) : ["_None._"]));
  return { body: lines.join("\n") + "\n", gaps, partial };
}

function analysis(d: Data, m: Model): string {
  const lines: string[] = [
    "# Extender-DB analysis",
    "",
    "_Generated by `evals report` — do not hand-edit. Companion to `coverage-matrix.md`;",
    "covers the DB's other cross-cutting answers: per-extender profiles, duplicative/conflicting/directed relationships, an assessor comparison, and the",
    "eval-runs provenance index._",
    "",
    scopeParagraph(m),
    "",
    "## Extender profiles",
    "",
    "| Extender | Kind | Jobs present | Jobs partial | Relationship degree |",
    "|---|---|---|---|---|",
  ];
  for (const e of m.live) {
    const rows = m.coverageRows.filter((a) => a.extender === e.id);
    const distinct = (verdict: string) => new Set(rows.filter((a) => a.verdict === verdict).map((a) => text(a.element))).size;
    const degree = m.relationships.filter((r) => r.extender_a === e.id || r.extender_b === e.id).length;
    lines.push(`| \`${cell(e.slug)}\` | ${cell(e.kind)} | ${distinct("present")} | ${distinct("partial")} | ${degree} |`);
  }
  lines.push(
    "",
    "## Duplicative, conflicting, and directed relationships",
    "",
    "_Pairs that need a resolution (`duplicative`/`conflicting`) or carry an ordering",
    "decision (`precedes`/`feeds-into`, the composition-planner substrate, EDB-22)._",
    "`complementary` pairs are informational and excluded — see the kind-count table",
    "in `coverage-matrix.md`.",
    "",
    "| Kind | A | B | Status | Evidence |",
    "|---|---|---|---|---|",
  );
  const listed = m.relationships
    .filter((r) => LISTED_KINDS.includes(text(r.kind)))
    .map((r) => {
      const [a, b] = pair(m, r);
      return { kind: text(r.kind), a, b, evidence: text(r.evidence) };
    })
    .sort((x, y) => compareTuples([x.kind, x.a, x.b], [y.kind, y.a, y.b]));
  for (const r of listed) {
    lines.push(`| ${cell(r.kind)} | \`${cell(r.a)}\` | \`${cell(r.b)}\` | ${r.evidence.includes("RESOLVED") ? "resolved" : "open"} | ${cell(r.evidence)} |`);
  }
  lines.push(
    "",
    "## Assessor comparison",
    "",
    "_Present/partial/absent verdict counts per extender, per assessor. `—` = the",
    "assessor never assessed that extender (not the same as an all-absent triple)._",
    "",
    `| Extender | Kind | ${ASSESSORS.map((a) => `${a} (P/Pa/Ab)`).join(" | ")} |`,
    `|---|---|${ASSESSORS.map(() => "---|").join("")}`,
  );
  for (const e of m.live) {
    const cells = ASSESSORS.map((assessor) => {
      const rows = m.assessments.filter((a) => a.extender === e.id && a.assessor === assessor);
      if (rows.length === 0) return "—";
      const n = (v: string) => rows.filter((a) => a.verdict === v).length;
      return `${n("present")}/${n("partial")}/${n("absent")}`;
    });
    lines.push(`| \`${cell(e.slug)}\` | ${cell(e.kind)} | ${cells.join(" | ")} |`);
  }
  lines.push(
    "",
    "## Eval-run provenance index",
    "",
    "| Slug | Kind | Status | assessments | job_coverage | relationships | Total |",
    "|---|---|---|---|---|---|---|",
  );
  for (const run of [...d.eval_runs].sort((a, b) => byText(text(a.slug), text(b.slug)))) {
    const a = m.assessments.filter((x) => x.eval_run === run.id).length;
    const j = d.job_coverage.filter((x) => x.eval_run === run.id).length;
    const r = m.relationships.filter((x) => x.eval_run === run.id).length;
    lines.push(`| \`${cell(run.slug)}\` | ${cell(run.kind)} | ${cell(run.status)} | ${a} | ${j} | ${r} | ${a + j + r} |`);
  }
  return lines.join("\n") + "\n";
}

export interface ReportOptions {
  out: string;
  fixtures?: string;
  env?: Record<string, string | undefined>;
}

export async function report(o: ReportOptions): Promise<number> {
  const data = await loadData(o.fixtures, o.env);
  const m = buildModel(data);
  const matrix = coverageMatrix(data, m);
  const analysisText = analysis(data, m);
  mkdirSync(o.out, { recursive: true });
  const matrixPath = join(o.out, "coverage-matrix.md");
  const analysisPath = join(o.out, "analysis.md");
  writeFileSync(matrixPath, matrix.body);
  writeFileSync(analysisPath, analysisText);
  console.log(`wrote ${matrixPath}: ${m.jobs.length} jobs (${matrix.gaps} gap, ${matrix.partial} partial), ${m.relationships.length} relationships`);
  console.log(`wrote ${analysisPath}: ${m.live.length} extenders, ${data.eval_runs.length} eval_runs`);
  return 0;
}
