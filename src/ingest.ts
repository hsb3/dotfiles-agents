// `evals ingest`: projects a dotfiles-agents checkout and the seed data into
// the catalog collections, then retires extenders that left the checkout.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import {
  CheckoutError, normaliseSource, readAssembly, readExternals, readMarketplace, readRoster, readUnit,
  type Assembly, type ExternalEntry, type MarketplacePlugin, type RosterEntry, type Unit,
} from "./checkout.ts";
import { compareCodePoints } from "./canonical.ts";
import {
  applyPlans, connect, diff, emptyPlan, fetchAll, formatParseOnly, formatPlan, formatWarnings, ValidationError,
  type Body, type CollectionPlan, type Connection, type Desired, type Rec,
} from "./store.ts";

const DATA_DIR = join(import.meta.dir, "..", "data");
const MECHANICAL = "mechanical-v1";

interface SeedElement {
  slug: string;
  name: string;
  element_kind: string;
  description?: string;
  criteria?: string;
  category?: string;
}
interface SeedFramework {
  slug: string;
  name: string;
  source_org?: string;
  source_url?: string;
  kind: string;
  applies_to?: string[];
  status?: string;
  summary?: string;
  elements: SeedElement[];
}
interface SeedKey {
  applies_to: string;
  key: string;
  requirement: string;
  description: string;
  spec_framework: string;
}

interface Seed {
  frameworks: SeedFramework[];
  sources: Record<string, unknown>[];
  upstreamPrefixes: { prefix: string; source: string }[];
  frontmatterKeys: SeedKey[];
  stdlib: Set<string>;
}

export function readSeed(dir = DATA_DIR): Seed {
  const load = (name: string) => JSON.parse(readFileSync(join(dir, name), "utf8"));
  const fw = load("frameworks.json");
  const src = load("sources.json");
  const fm = load("frontmatter-spec.json");
  const std = load("python-stdlib.json");
  return {
    frameworks: fw.frameworks,
    sources: src.sources,
    upstreamPrefixes: src.upstream_prefixes ?? [],
    frontmatterKeys: fm.keys,
    stdlib: new Set(std.modules),
  };
}

interface RosterUnit {
  entry: RosterEntry;
  unit: Unit;
}

export interface IngestInput {
  seed: Seed;
  roster: RosterUnit[];
  externals: ExternalEntry[]; // without those also in the roster
  plugins: { plugin: MarketplacePlugin; assembly: Assembly }[];
  warnings: string[];
}

// Phase 1: every input, read and validated without the database.
export function readInput(sourceRoot: string): IngestInput {
  const warnings: string[] = [];
  const problems: string[] = [];
  const attempt = <T>(read: () => T): T | null => {
    try {
      return read();
    } catch (err) {
      if (err instanceof CheckoutError) {
        problems.push(...err.problems);
        return null;
      }
      throw err;
    }
  };
  const rosterEntries = attempt(() => readRoster(sourceRoot));
  const externalEntries = attempt(() => readExternals(sourceRoot));
  const plugins = attempt(() => readMarketplace(sourceRoot));
  if (problems.length > 0 || !rosterEntries || !externalEntries || !plugins) throw new ValidationError(problems);
  const seed = readSeed();
  const rosterIds = new Set(rosterEntries.map((e) => e.id));
  const externals = externalEntries.filter((e) => {
    if (!rosterIds.has(e.id)) return true;
    warnings.push(`external ${e.id} skipped: also a roster entry`);
    return false;
  });
  const roster = rosterEntries.map((entry) => ({ entry, unit: readUnit(sourceRoot, entry, warnings) }));
  return {
    seed,
    roster,
    externals,
    plugins: plugins.map((plugin) => ({ plugin, assembly: readAssembly(sourceRoot, plugin.name) })),
    warnings,
  };
}

function textOf(v: unknown): string {
  if (v === undefined || v === null) return "";
  if (typeof v === "string") return v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return JSON.stringify(v);
}

// Set unless missing, null, false, 0, "", [] or {}.
function isSet(v: unknown): boolean {
  if (v === undefined || v === null || v === false || v === 0 || v === "") return false;
  if (Array.isArray(v)) return v.length > 0;
  if (typeof v === "object") return Object.keys(v as object).length > 0;
  return true;
}

const json = (v: unknown): string => (v === undefined ? "null" : JSON.stringify(v));
const chars = (s: string): number => [...s].length;
const words = (s: string): number => s.split(/\s+/).filter((w) => w !== "").length;

interface Verdict {
  framework: string;
  element: string;
  verdict: string;
  evidence: string;
}

// The top-level imports of a hook.py: `import a, b.c as d` and `from a.b import …`.
export function topLevelImports(source: string): string[] {
  const modules: string[] = [];
  for (const line of source.split("\n")) {
    const code = line.replace(/#.*$/, "").trimEnd();
    let m = /^import\s+(.+)$/.exec(code);
    if (m) {
      for (const part of m[1]!.split(",")) {
        const mod = part.trim().split(/\s+as\s+/)[0]!.trim();
        if (mod) modules.push(mod);
      }
      continue;
    }
    m = /^from\s+(\S+)\s+import\b/.exec(code);
    if (m && !m[1]!.startsWith(".")) modules.push(m[1]!);
  }
  return modules;
}

const FRAMEWORK_OF: Record<string, string> = {
  skill: "anthropic-agent-skills",
  agent: "claude-code-subagents",
  hook: "hook-dir-layout",
};

export function mechanicalVerdicts(entry: RosterEntry, unit: Unit, stdlib: Set<string>): Verdict[] {
  const fm = unit.frontmatter;
  const has = (rel: string) => unit.files.some((f) => f.relpath === rel);
  const under = (dir: string) => unit.files.filter((f) => f.relpath.startsWith(`${dir}/`)).length;
  const out: Verdict[] = [];
  const framework = FRAMEWORK_OF[entry.type] ?? "";
  const v = (element: string, verdict: string, evidence: string) => out.push({ framework, element, verdict, evidence });
  if (entry.type === "skill") {
    const skillMd = unit.files.find((f) => f.relpath === "SKILL.md");
    v("skill-md-entrypoint", skillMd ? "present" : "absent", skillMd ? "SKILL.md at folder root" : "no SKILL.md found");
    const name = textOf(fm.name);
    const n = chars(name);
    v("frontmatter-name", n === 0 ? "absent" : n <= 64 ? "present" : "partial", `name=${JSON.stringify(name)} (${n} chars)`);
    const description = textOf(fm.description);
    const d = chars(description);
    v("frontmatter-description", d === 0 ? "absent" : d <= 1024 ? "present" : "partial", `${d} chars`);
    const lines = skillMd ? skillMd.content.split("\n").length : 0;
    v("concise-body", lines <= 500 ? "present" : "partial", `${lines} lines`);
    for (const [element, dir] of [["references-dir", "references"], ["scripts-dir", "scripts"], ["assets-dir", "assets"]] as const) {
      const count = under(dir);
      v(element, count > 0 ? "present" : "absent", count > 0 ? `${count} file(s)` : "not bundled (optional)");
    }
    return out;
  }
  if (entry.type === "agent") {
    for (const [element, key] of [["frontmatter-name", "name"], ["frontmatter-description", "description"], ["tools-allowlist", "tools"], ["model-tier", "model"]] as const) {
      v(element, isSet(fm[key]) ? "present" : "absent", `${key}=${json(fm[key])}`);
    }
    v("system-prompt-body", /\S/.test(unit.body) ? "present" : "absent", `${words(unit.body)} words`);
    return out;
  }
  if (entry.type === "hook") {
    const hookPy = unit.files.find((f) => f.relpath === "hook.py");
    v("hook-py-entrypoint", hookPy ? "present" : "absent", hookPy ? "hook.py in the hook's directory" : "no hook.py found");
    const sh = unit.files.filter((f) => f.relpath.endsWith(".sh")).map((f) => f.relpath);
    v("python-only-handler", sh.length > 0 ? "absent" : "present", sh.length > 0 ? `legacy .sh handler(s): ${JSON.stringify(sh)}` : "no .sh handler");
    if (!hookPy) v("stdlib-only-imports", "absent", "no hook.py to scan");
    else {
      const foreign = [...new Set(topLevelImports(hookPy.content).filter((m) => !stdlib.has(m.split(".")[0]!)))].sort(compareCodePoints);
      if (foreign.length > 0) v("stdlib-only-imports", "partial", `non-stdlib imports: ${JSON.stringify(foreign)}`);
      else v("stdlib-only-imports", "present", "all top-level imports are stdlib");
    }
    const configs = ["config.json", "hook.json"].filter(has).length;
    v("config-present", configs > 0 ? "present" : "absent", configs > 0 ? `${configs} file(s)` : "not bundled (optional)");
    return out;
  }
  return [];
}

function members(input: IngestInput, assembly: Assembly): string[] {
  const ids = new Set(input.roster.map((r) => r.entry.id));
  const out = [...assembly.skills, ...assembly.agents, ...assembly.hooks, ...assembly.commands].filter((n) => ids.has(n));
  if (assembly.mcpTarget !== null) {
    const target = normaliseSource(assembly.mcpTarget);
    const hit = input.roster.find((r) => normaliseSource(r.entry.source) === target);
    if (hit) out.push(hit.entry.id);
  }
  return out;
}

function distributionKind(name: string, assembly: Assembly): string {
  const names = [...assembly.skills, ...assembly.agents, ...assembly.hooks];
  return names.length === 1 && names[0] === name ? "standalone" : "bundle";
}

interface Dimension {
  key: string;
  appliesTo: string;
  requirement: string;
  description: string;
  specFramework: string; // slug or ""
  observed: number;
}

function dimensions(input: IngestInput): Dimension[] {
  const byKey = new Map<string, Dimension>();
  const at = (appliesTo: string, key: string) => `${key}|${appliesTo}`;
  for (const { entry, unit } of input.roster) {
    for (const key of Object.keys(unit.frontmatter)) {
      const k = at(entry.type, key);
      const d = byKey.get(k) ?? { key, appliesTo: entry.type, requirement: "custom", description: "", specFramework: "", observed: 0 };
      d.observed++;
      byKey.set(k, d);
    }
  }
  for (const s of input.seed.frontmatterKeys) {
    const k = at(s.applies_to, s.key);
    const d = byKey.get(k) ?? { key: s.key, appliesTo: s.applies_to, requirement: "custom", description: "", specFramework: "", observed: 0 };
    d.requirement = s.requirement;
    d.description = s.description ?? "";
    d.specFramework = s.spec_framework ?? "";
    byKey.set(k, d);
  }
  return [...byKey.values()];
}

function sourceFor(input: IngestInput, upstream: string): string {
  const hit = input.seed.upstreamPrefixes.find((p) => upstream.startsWith(p.prefix));
  return hit ? hit.source : "";
}

interface Counts {
  [collection: string]: number;
}

export function parseOnlyCounts(input: IngestInput): Counts {
  return {
    frameworks: input.seed.frameworks.length,
    framework_elements: input.seed.frameworks.reduce((n, f) => n + f.elements.length, 0),
    sources: input.seed.sources.length,
    extenders: input.roster.length + input.externals.length,
    files: input.roster.reduce((n, r) => n + r.unit.files.length, 0),
    distributions: input.plugins.length,
    frontmatter_dimensions: dimensions(input).length,
    assessments: input.roster.reduce((n, r) => n + mechanicalVerdicts(r.entry, r.unit, input.seed.stdlib).length, 0),
  };
}

function reverse(recs: Rec[], keyField: string): Map<string, string> {
  return new Map(recs.map((r) => [r.id, String(r[keyField] ?? "")]));
}

export interface IngestPlan {
  plans: CollectionPlan[]; // in write order, the retires last
  display: CollectionPlan[]; // one per collection, as the plan block prints them
  retired: string[]; // `<kind>/<slug>`
}

// Phase 2: reads the stored state and computes the complete plan.
export async function planIngest(conn: Connection, input: IngestInput): Promise<IngestPlan> {
  const { seed } = input;

  const storedFrameworks = await fetchAll(conn, "frameworks");
  const frameworks = diff(
    "frameworks",
    seed.frameworks.map((f) => ({
      key: f.slug,
      body: {
        slug: f.slug, name: f.name, source_org: f.source_org ?? "", source_url: f.source_url ?? "", kind: f.kind,
        applies_to: f.applies_to ?? [], status: f.status ?? "", summary: f.summary ?? "",
      },
    })),
    storedFrameworks,
    (r) => String(r.slug),
  );
  const fwId = (slug: string) => frameworks.ids.get(slug) ?? "";
  const fwSlugOf = reverse(storedFrameworks, "slug");

  const elementDesired: Desired[] = [];
  for (const f of seed.frameworks) {
    f.elements.forEach((e, i) => {
      elementDesired.push({
        key: `${f.slug}|${e.slug}`,
        body: {
          framework: fwId(f.slug), slug: e.slug, name: e.name, element_kind: e.element_kind,
          description: e.description ?? "", criteria: e.criteria ?? "", category: e.category ?? "", sort_order: i,
        },
      });
    });
  }
  const storedElements = await fetchAll(conn, "framework_elements");
  const elements = diff("framework_elements", elementDesired, storedElements, (r) => `${fwSlugOf.get(String(r.framework)) ?? r.framework}|${r.slug}`);
  const elementKeyOf = new Map(storedElements.map((r) => [r.id, `${fwSlugOf.get(String(r.framework)) ?? r.framework}|${r.slug}`]));

  const sourceFields = ["slug", "name", "url", "publisher_kind", "publishes", "trust_tier", "publishes_evals", "maintenance", "license", "adoption_signal", "rationale", "evidence_url", "status", "notes"];
  const sources = diff(
    "sources",
    seed.sources.map((s) => {
      const body: Body = {};
      for (const field of sourceFields) if (field in s) body[field] = s[field];
      return { key: String(s.slug), body };
    }),
    await fetchAll(conn, "sources"),
    (r) => String(r.slug),
  );

  const extenderDesired: Desired[] = [];
  for (const { entry, unit } of input.roster) {
    const fm = unit.frontmatter;
    extenderDesired.push({
      key: entry.id,
      body: {
        slug: entry.id,
        name: textOf(fm.name) || entry.id,
        kind: entry.type,
        description: textOf(fm.description) || entry.summary || "",
        origin: entry.origin,
        upstream: entry.upstream,
        upstream_ref: entry.ref,
        repo_path: entry.source,
        shelf: entry.shelf,
        disposition: entry.disposition,
        requires: entry.requires,
        assumes: entry.assumes,
        frontmatter: fm,
        body: unit.body,
        entry_file: unit.entryFile,
        file_count: unit.files.length,
        total_bytes: unit.files.reduce((n, f) => n + f.sizeBytes, 0),
        word_count: words(unit.body),
        retired: false,
      },
    });
  }
  for (const e of input.externals) {
    const source = sourceFor(input, e.upstream);
    extenderDesired.push({
      key: e.id,
      body: {
        slug: e.id, name: e.id, kind: e.kind, description: e.provides, origin: "external",
        source: source ? (sources.ids.get(source) ?? "") : "",
        upstream: e.upstream, upstream_ref: e.ref, repo_path: "", shelf: "", disposition: "", requires: [], assumes: [],
        frontmatter: {}, body: "", entry_file: "", file_count: 0, total_bytes: 0, word_count: 0, retired: false,
      },
    });
  }
  const storedExtenders = await fetchAll(conn, "extenders");
  const extenders = diff("extenders", extenderDesired, storedExtenders, (r) => String(r.slug), { showRetire: true });
  const live = new Set(extenderDesired.map((d) => d.key));
  const retired: string[] = [];
  for (const r of storedExtenders) {
    if (live.has(String(r.slug)) || r.retired === true) continue;
    extenders.retires.push({ id: r.id, key: String(r.slug), body: { retired: true } });
    retired.push(`${r.kind}/${r.slug}`);
  }
  const extId = (slug: string) => extenders.ids.get(slug) ?? "";
  const extSlugOf = reverse(storedExtenders, "slug");

  const fileDesired: Desired[] = [];
  for (const { entry, unit } of input.roster) {
    for (const f of unit.files) {
      fileDesired.push({
        key: `${entry.id}|${f.relpath}`,
        body: {
          extender: extId(entry.id), relpath: f.relpath, role: f.role, content: f.content, is_binary: f.isBinary,
          size_bytes: f.sizeBytes, sha256: f.sha256, language: f.language,
        },
      });
    }
  }
  const storedFiles = await fetchAll(conn, "files");
  const fileKey = (r: Rec) => `${extSlugOf.get(String(r.extender)) ?? r.extender}|${r.relpath}`;
  const files = diff("files", fileDesired, storedFiles, fileKey, { showDelete: true });
  const rosterIds = new Set(input.roster.map((r) => r.entry.id));
  const wantedFiles = new Set(fileDesired.map((d) => d.key));
  for (const r of storedFiles) {
    const owner = extSlugOf.get(String(r.extender));
    if (owner !== undefined && rosterIds.has(owner) && !wantedFiles.has(fileKey(r))) files.deletes.push({ id: r.id, key: fileKey(r) });
  }

  const distributions = diff(
    "distributions",
    input.plugins.map(({ plugin, assembly }) => ({
      key: plugin.name,
      body: {
        slug: plugin.name, kind: distributionKind(plugin.name, assembly), version: plugin.version,
        description: plugin.description, members: members(input, assembly).map(extId),
      },
    })),
    await fetchAll(conn, "distributions"),
    (r) => String(r.slug),
  );

  const dims = diff(
    "frontmatter_dimensions",
    dimensions(input).map((d) => ({
      key: `${d.key}|${d.appliesTo}`,
      body: {
        key: d.key, applies_to: d.appliesTo, requirement: d.requirement, description: d.description,
        spec_framework: d.specFramework ? fwId(d.specFramework) : "", observed_count: d.observed,
      },
    })),
    await fetchAll(conn, "frontmatter_dimensions"),
    (r) => `${r.key}|${r.applies_to}`,
  );

  const assessmentDesired: Desired[] = [];
  for (const { entry, unit } of input.roster) {
    for (const v of mechanicalVerdicts(entry, unit, seed.stdlib)) {
      const elementKey = `${v.framework}|${v.element}`;
      assessmentDesired.push({
        key: `${entry.id}|${elementKey}|${MECHANICAL}`,
        body: {
          extender: extId(entry.id), framework: fwId(v.framework), element: elements.ids.get(elementKey) ?? "",
          verdict: v.verdict, evidence: v.evidence, assessor: MECHANICAL,
        },
      });
    }
  }
  const storedAssessments = await fetchAll(conn, "assessments", conn.pb.filter("assessor = {:a}", { a: MECHANICAL }));
  const assessments = diff(
    "assessments",
    assessmentDesired,
    storedAssessments,
    (r) => `${extSlugOf.get(String(r.extender)) ?? r.extender}|${elementKeyOf.get(String(r.element)) ?? `${fwSlugOf.get(String(r.framework))}|${r.element}`}|${r.assessor}`,
  );

  const display = [frameworks, elements, sources, extenders, files, distributions, dims, assessments];
  // Retire after every other write.
  const retire = emptyPlan("extenders");
  retire.retires = extenders.retires;
  const plans = display.map((p) => (p === extenders ? { ...p, retires: [] } : p));
  return { plans: [...plans, retire], display, retired };
}

export interface IngestOptions {
  sourceRoot: string;
  mode: "parse-only" | "dry-run" | "write";
  env?: Record<string, string | undefined>;
}

export async function ingest(options: IngestOptions): Promise<number> {
  const input = readInput(options.sourceRoot);
  if (options.mode === "parse-only") {
    console.log(formatParseOnly(Object.entries(parseOnlyCounts(input)), input.warnings).join("\n"));
    return 0;
  }
  const conn = await connect(options.env);
  const planned = await planIngest(conn, input);
  if (options.mode === "dry-run") {
    const lines = formatPlan(planned.display, "dry-run");
    lines.push(...planned.retired.map((r) => `  to retire ${r}`));
    lines.push(...formatWarnings(input.warnings));
    console.log(lines.join("\n"));
    return 0;
  }
  await applyPlans(conn, planned.plans);
  const lines = formatPlan(planned.display, "applied");
  lines.push(...planned.retired.map((r) => `  retired ${r}`));
  lines.push(...formatWarnings(input.warnings));
  console.log(lines.join("\n"));
  return 0;
}
