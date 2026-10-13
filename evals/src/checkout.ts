// Reads a dotfiles-agents checkout without changing it: the roster, the
// externals, unit sources with their frontmatter and files, the marketplace
// manifest and the plugin assemblies of symlinks.
import { existsSync, lstatSync, readdirSync, readFileSync, readlinkSync, statSync } from "node:fs";
import { basename, dirname, extname, join, posix, relative, resolve, sep } from "node:path";
import { compareCodePoints } from "./canonical.ts";

export const UNIT_TYPES = ["skill", "agent", "hook", "command", "mcp"] as const;
const ORIGINS = ["authored", "sourced", "vendored"];
const DISPOSITIONS = ["qualified", "grandfathered-pending-use", "demoted", "untriaged", "orphaned"];
const SHELVES = ["core", "toggle"];
const EXTERNAL_KINDS = ["skill", "agent", "hook", "mcp", "command", "plugin"];

export interface RosterEntry {
  id: string;
  type: string;
  source: string;
  origin: string;
  disposition: string;
  targets: string[];
  requires: string[];
  assumes: string[];
  upstream: string;
  ref: string;
  shelf: string;
  summary: string;
}

export interface ExternalEntry {
  id: string;
  kind: string;
  upstream: string;
  ref: string;
  path: string;
  provides: string;
  targets: string[];
}

export interface UnitFile {
  relpath: string;
  content: string;
  isBinary: boolean;
  sizeBytes: number;
  sha256: string;
  language: string;
  role: string;
}

export interface Unit {
  exists: boolean;
  frontmatter: Record<string, unknown>;
  body: string;
  entryFile: string; // relpath of the entry file, "" when it is missing
  entryText: string | null; // the entry file's text, null when it is missing
  files: UnitFile[];
}

export interface MarketplacePlugin {
  name: string;
  version: string;
  description: string;
}

export interface Assembly {
  skills: string[]; // symlink names, sorted
  agents: string[]; // `.md` stripped
  hooks: string[];
  commands: string[]; // `.md` stripped
  mcpTarget: string | null; // the .mcp.json link target, relative to the source root
}

export class CheckoutError extends Error {
  constructor(readonly problems: string[]) {
    super(problems.join("\n"));
  }
}

function asText(v: unknown): string {
  if (v === undefined || v === null) return "";
  return typeof v === "string" ? v : String(v);
}

// A list key given as a scalar is a one-item list; null and absent mean none.
function asList(v: unknown): string[] {
  if (v === undefined || v === null) return [];
  if (Array.isArray(v)) return v.filter((x) => x !== null && x !== undefined).map((x) => asText(x));
  return [asText(v)];
}

function readYaml(root: string, file: string): unknown {
  const path = join(root, file);
  if (!existsSync(path)) throw new CheckoutError([`missing ${file} under ${root}`]);
  try {
    return Bun.YAML.parse(readFileSync(path, "utf8"));
  } catch (err) {
    throw new CheckoutError([`${file}: invalid YAML: ${err instanceof Error ? err.message : String(err)}`]);
  }
}

function listOfMappings(doc: unknown, file: string, key: string, problems: string[]): Record<string, unknown>[] {
  const list = doc !== null && typeof doc === "object" ? (doc as Record<string, unknown>)[key] : undefined;
  if (list === undefined || list === null) return [];
  if (!Array.isArray(list)) {
    problems.push(`${file}: ${key} is not a list`);
    return [];
  }
  const out: Record<string, unknown>[] = [];
  list.forEach((item, i) => {
    if (item === null || typeof item !== "object" || Array.isArray(item)) problems.push(`${file}: ${key}[${i}] is not a mapping`);
    else out.push(item as Record<string, unknown>);
  });
  return out;
}

export function readRoster(root: string): RosterEntry[] {
  const problems: string[] = [];
  const file = "primitives-core.yaml";
  const items = listOfMappings(readYaml(root, file), file, "primitives", problems);
  const seen = new Set<string>();
  const entries: RosterEntry[] = [];
  items.forEach((item, i) => {
    const id = asText(item.id);
    const where = `${file}: primitives[${i}]${id ? ` (${id})` : ""}`;
    const e: RosterEntry = {
      id,
      type: asText(item.type),
      source: asText(item.source),
      origin: asText(item.origin),
      disposition: asText(item.disposition),
      targets: asList(item.targets),
      requires: asList(item.requires),
      assumes: asList(item.assumes),
      upstream: asText(item.upstream),
      ref: asText(item.ref),
      shelf: asText(item.shelf),
      summary: asText(item.summary),
    };
    if (!id) problems.push(`${where}: missing id`);
    else if (seen.has(id)) problems.push(`${where}: duplicate id`);
    seen.add(id);
    if (!(UNIT_TYPES as readonly string[]).includes(e.type)) problems.push(`${where}: type must be one of ${UNIT_TYPES.join(", ")}`);
    if (!e.source) problems.push(`${where}: missing source`);
    if (!ORIGINS.includes(e.origin)) problems.push(`${where}: origin must be one of ${ORIGINS.join(", ")}`);
    if (!DISPOSITIONS.includes(e.disposition)) problems.push(`${where}: disposition must be one of ${DISPOSITIONS.join(", ")}`);
    if (e.shelf && !SHELVES.includes(e.shelf)) problems.push(`${where}: shelf must be one of ${SHELVES.join(", ")}`);
    entries.push(e);
  });
  if (problems.length > 0) throw new CheckoutError(problems);
  return entries;
}

export function readExternals(root: string): ExternalEntry[] {
  const problems: string[] = [];
  const file = "externals.yaml";
  const items = listOfMappings(readYaml(root, file), file, "externals", problems);
  const seen = new Set<string>();
  const entries: ExternalEntry[] = [];
  items.forEach((item, i) => {
    const id = asText(item.id);
    const where = `${file}: externals[${i}]${id ? ` (${id})` : ""}`;
    const e: ExternalEntry = {
      id,
      kind: asText(item.kind),
      upstream: asText(item.upstream),
      ref: asText(item.ref),
      path: asText(item.path),
      provides: asText(item.provides),
      targets: asList(item.targets),
    };
    if (!id) problems.push(`${where}: missing id`);
    else if (seen.has(id)) problems.push(`${where}: duplicate id`);
    seen.add(id);
    if (!EXTERNAL_KINDS.includes(e.kind)) problems.push(`${where}: kind must be one of ${EXTERNAL_KINDS.join(", ")}`);
    entries.push(e);
  });
  if (problems.length > 0) throw new CheckoutError(problems);
  return entries;
}

export interface Frontmatter {
  frontmatter: Record<string, unknown>;
  body: string;
  warning: string | null;
}

// The YAML mapping between a first line `---` and the next line `---`; the body
// is everything after the closing line.
export function splitFrontmatter(text: string): Frontmatter {
  const lines = text.split("\n");
  if (lines[0]?.replace(/\r$/, "") !== "---") return { frontmatter: {}, body: text, warning: null };
  const close = lines.findIndex((l, i) => i > 0 && l.replace(/\r$/, "") === "---");
  if (close < 0) return { frontmatter: {}, body: text, warning: null };
  const yaml = lines.slice(1, close).join("\n");
  const body = lines.slice(close + 1).join("\n");
  try {
    const parsed = Bun.YAML.parse(yaml);
    if (parsed === null || parsed === undefined) return { frontmatter: {}, body, warning: null };
    if (typeof parsed !== "object" || Array.isArray(parsed)) return { frontmatter: {}, body, warning: "frontmatter is not a YAML mapping" };
    return { frontmatter: parsed as Record<string, unknown>, body, warning: null };
  } catch (err) {
    return { frontmatter: {}, body, warning: `unparseable frontmatter YAML: ${err instanceof Error ? err.message.split("\n")[0] : String(err)}` };
  }
}

const LANGUAGES: Record<string, string> = {
  ".py": "python",
  ".sh": "shell",
  ".js": "javascript",
  ".ts": "typescript",
  ".md": "markdown",
  ".json": "json",
  ".yaml": "yaml",
  ".yml": "yaml",
  ".toml": "toml",
  ".txt": "text",
  ".css": "css",
  ".html": "html",
};

export function languageOf(relpath: string): string {
  return LANGUAGES[extname(relpath).toLowerCase()] ?? "";
}

const SEGMENT_ROLES: Record<string, string> = {
  references: "reference",
  scripts: "script",
  assets: "asset",
  templates: "template",
  evals: "eval",
  eval: "eval",
};

export function roleOf(relpath: string, entryFile: string): string {
  if (relpath === entryFile) return "entrypoint";
  const first = relpath.split("/")[0]!;
  if (relpath.includes("/") && SEGMENT_ROLES[first]) return SEGMENT_ROLES[first]!;
  const name = basename(relpath);
  if (name.toUpperCase().startsWith("LICENSE")) return "license";
  if (name.endsWith(".md") || name.endsWith(".txt")) return "doc";
  if ([".json", ".yaml", ".yml", ".toml"].some((ext) => name.endsWith(ext))) return "config";
  return "other";
}

const UTF8 = new TextDecoder("utf-8", { fatal: true });

function decode(bytes: Uint8Array): string | null {
  try {
    return UTF8.decode(bytes);
  } catch {
    return null;
  }
}

function readFile(path: string, relpath: string, entryFile: string): UnitFile {
  const bytes = new Uint8Array(readFileSync(path));
  const text = decode(bytes);
  return {
    relpath,
    content: text ?? "",
    isBinary: text === null,
    sizeBytes: bytes.length,
    sha256: new Bun.CryptoHasher("sha256").update(bytes).digest("hex"),
    language: languageOf(relpath),
    role: roleOf(relpath, entryFile),
  };
}

// Every file under dir, skipping dot names and __pycache__; symlinked
// directories are not descended, symlinked files are read through.
function walk(dir: string, prefix: string, out: string[], warnings: string[]): void {
  for (const name of readdirSync(dir)) {
    if (name.startsWith(".")) continue;
    const path = join(dir, name);
    const rel = prefix ? `${prefix}/${name}` : name;
    const ls = lstatSync(path);
    if (ls.isSymbolicLink()) {
      let st;
      try {
        st = statSync(path);
      } catch {
        warnings.push(`broken symlink skipped: ${rel}`);
        continue;
      }
      if (st.isFile()) out.push(rel);
      continue;
    }
    if (ls.isDirectory()) {
      if (name === "__pycache__") continue;
      walk(path, rel, out, warnings);
    } else if (ls.isFile()) out.push(rel);
  }
}

const ENTRY: Record<string, string> = { skill: "SKILL.md", hook: "hook.py" };

// Reads a roster entry's unit source. Warnings name problems that do not stop ingest.
export function readUnit(root: string, entry: RosterEntry, warnings: string[]): Unit {
  const path = resolve(root, entry.source);
  const missing: Unit = { exists: false, frontmatter: {}, body: "", entryFile: "", entryText: null, files: [] };
  if (!existsSync(path)) {
    warnings.push(`${entry.type} ${entry.id}: source ${entry.source} does not exist`);
    return missing;
  }
  const st = statSync(path);
  let relpaths: string[];
  let entryName: string;
  let baseDir: string;
  if (st.isDirectory()) {
    relpaths = [];
    const walkWarnings: string[] = [];
    walk(path, "", relpaths, walkWarnings);
    for (const w of walkWarnings) warnings.push(`${entry.type} ${entry.id}: ${w}`);
    entryName = ENTRY[entry.type] ?? "";
    baseDir = path;
  } else {
    relpaths = [basename(path)];
    entryName = basename(path);
    baseDir = dirname(path);
  }
  relpaths.sort(compareCodePoints);
  const entryFile = relpaths.includes(entryName) ? entryName : "";
  const files = relpaths.map((rel) => readFile(join(baseDir, ...rel.split("/")), rel, entryFile));
  const entryUnit = files.find((f) => f.relpath === entryFile);
  const entryText = entryUnit && !entryUnit.isBinary ? entryUnit.content : entryUnit ? "" : null;
  let frontmatter: Record<string, unknown> = {};
  let body = "";
  if ((entry.type === "skill" || entry.type === "agent" || entry.type === "command") && entryText !== null) {
    const fm = splitFrontmatter(entryText);
    if (fm.warning) warnings.push(`${entry.type} ${entry.id}: ${fm.warning}`);
    frontmatter = fm.frontmatter;
    body = fm.body;
  }
  return { exists: true, frontmatter, body, entryFile, entryText, files };
}

export function readMarketplace(root: string): MarketplacePlugin[] {
  const file = ".claude-plugin/marketplace.json";
  const path = join(root, file);
  if (!existsSync(path)) throw new CheckoutError([`missing ${file} under ${root}`]);
  let doc: unknown;
  try {
    doc = JSON.parse(readFileSync(path, "utf8"));
  } catch (err) {
    throw new CheckoutError([`${file}: invalid JSON: ${err instanceof Error ? err.message : String(err)}`]);
  }
  const plugins = (doc as { plugins?: unknown })?.plugins;
  if (!Array.isArray(plugins)) throw new CheckoutError([`${file}: plugins is not a list`]);
  const problems: string[] = [];
  const seen = new Set<string>();
  const out: MarketplacePlugin[] = [];
  plugins.forEach((p, i) => {
    const name = p && typeof p === "object" ? (p as Record<string, unknown>).name : undefined;
    if (typeof name !== "string" || !name) {
      problems.push(`${file}: plugins[${i}] has no name`);
      return;
    }
    if (seen.has(name)) problems.push(`${file}: duplicate plugin ${name}`);
    seen.add(name);
    const rec = p as Record<string, unknown>;
    out.push({ name, version: asText(rec.version), description: asText(rec.description) });
  });
  if (problems.length > 0) throw new CheckoutError(problems);
  return out;
}

function symlinkNames(dir: string): string[] {
  if (!existsSync(dir) || !lstatSync(dir).isDirectory()) return [];
  return readdirSync(dir)
    .filter((name) => lstatSync(join(dir, name)).isSymbolicLink())
    .sort(compareCodePoints);
}

// The symlinks of plugins/<name>/; a missing directory means no members.
export function readAssembly(root: string, name: string): Assembly {
  const dir = join(root, "plugins", name);
  const stripMd = (names: string[]) => names.filter((n) => n.endsWith(".md")).map((n) => n.slice(0, -3));
  const mcp = join(dir, ".mcp.json");
  let mcpTarget: string | null = null;
  if (existsSync(dir) && lstatSync(dir).isDirectory()) {
    try {
      if (lstatSync(mcp).isSymbolicLink()) {
        const target = resolve(dirname(mcp), readlinkSync(mcp));
        mcpTarget = relative(resolve(root), target).split(sep).join("/");
      }
    } catch {
      mcpTarget = null;
    }
  }
  return {
    skills: symlinkNames(join(dir, "skills")),
    agents: stripMd(symlinkNames(join(dir, "agents"))),
    hooks: symlinkNames(join(dir, "hooks")),
    commands: stripMd(symlinkNames(join(dir, "commands"))),
    mcpTarget,
  };
}

// A roster source path as written, normalised for comparison with link targets.
export function normaliseSource(source: string): string {
  return posix.normalize(source.replace(/\\/g, "/")).replace(/^\.\//, "").replace(/\/$/, "");
}
