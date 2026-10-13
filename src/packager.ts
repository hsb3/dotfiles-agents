// `evals package`: builds a new, deterministic deploy directory for the
// PocketBase service (Dockerfile, start.sh, railway.toml, the catalog hook with
// its catalog and receipt, every migration and the UI build). Never deploys.
import { chmodSync, copyFileSync, existsSync, lstatSync, mkdirSync, readdirSync, readFileSync, realpathSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { basename, dirname, isAbsolute, join, relative, resolve } from "node:path";
import { compareCodePoints, sha256Hex } from "./canonical.ts";
import { CommandError, ValidationError } from "./store.ts";

const REPO = join(import.meta.dir, "..");

export const DOCKERFILE = "FROM alpine:3.20\n\nARG PB_VERSION=0.40.3\nARG TARGETARCH\n\nRUN apk add --no-cache ca-certificates curl unzip\nRUN set -e; case \"$TARGETARCH\" in \\\n      amd64) PB_SHA256=8d81b6b79add0e219373e922ebe1dddbee7f57fcff602e3585e0d2c654b983ce ;; \\\n      arm64) PB_SHA256=d5092815259f5bc2dffabf6a71da2168851c8d75c04d6e56f6e7a38c48941c70 ;; \\\n      *) echo \"unsupported PocketBase architecture: $TARGETARCH\" >&2; exit 1 ;; \\\n    esac; \\\n    curl -fsSL -o /tmp/pb.zip \"https://github.com/pocketbase/pocketbase/releases/download/v${PB_VERSION}/pocketbase_${PB_VERSION}_linux_${TARGETARCH}.zip\"; \\\n    echo \"$PB_SHA256  /tmp/pb.zip\" | sha256sum -c -; \\\n    unzip /tmp/pb.zip -d /pb; rm /tmp/pb.zip; /pb/pocketbase --version\n\nWORKDIR /pb\nCOPY start.sh ./start.sh\nCOPY pb_public ./pb_public\nCOPY pb_hooks ./pb_hooks\nCOPY pb_migrations ./pb_migrations\nRUN chmod +x /pb/start.sh\n\nEXPOSE 8090\nHEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \\\n  CMD wget -q -O- \"http://127.0.0.1:${PORT:-8090}/api/health\" >/dev/null 2>&1 || exit 1\nCMD [\"/pb/start.sh\"]\n";
export const START_SH = "#!/bin/sh\nset -eu\n\ndata_dir=${PB_DATA_DIR:-/pb/pb_data}\npb_bin=${POCKETBASE_BIN:-/pb/pocketbase}\npackage_dir=$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\n: \"${PB_SUPERUSER_EMAIL:?PB_SUPERUSER_EMAIL is required}\"\n: \"${PB_SUPERUSER_PASSWORD:?PB_SUPERUSER_PASSWORD is required}\"\nif output=$(\"$pb_bin\" superuser create \"$PB_SUPERUSER_EMAIL\" \"$PB_SUPERUSER_PASSWORD\" --dir \"$data_dir\" 2>&1); then\n  :\nelif printf '%s' \"$output\" | grep -q 'failed to create new superuser account: email: Value must be unique\\.$'; then\n  :\nelse\n  printf '%s\\n' \"$output\" >&2\n  exit 1\nfi\n\nexec \"$pb_bin\" serve --http=\"${PB_BIND:-0.0.0.0}:${PORT:-8090}\" --dir \"$data_dir\" \\\n  --hooksDir=\"$package_dir/pb_hooks\" --publicDir=\"$package_dir/pb_public\" \\\n  --migrationsDir=\"$package_dir/pb_migrations\" --automigrate=false \\\n  --origins=\"${PB_CORS_ORIGINS:-https://invalid.local}\"\n";
export const RAILWAY_TOML = "[build]\nbuilder = \"DOCKERFILE\"\ndockerfilePath = \"Dockerfile\"\n\n[deploy]\nhealthcheckPath = \"/api/health\"\nhealthcheckTimeout = 100\n";

const HEADERS = ["Stage", "Current marketplace plugin(s)", "Choose them when"];

type Obj = Record<string, unknown>;

// Every regular file under dir as a sorted relative path; symlinks are reported.
function listFiles(dir: string, problems: string[], label: string): string[] {
  const out: string[] = [];
  const walk = (d: string, rel: string) => {
    for (const name of readdirSync(d)) {
      const path = join(d, name);
      const r = rel ? `${rel}/${name}` : name;
      const st = lstatSync(path);
      if (st.isSymbolicLink()) problems.push(`${label} contains a symlink: ${r}`);
      else if (st.isDirectory()) walk(path, r);
      else if (st.isFile()) out.push(r);
      else problems.push(`${label} contains a special file: ${r}`);
    }
  };
  walk(dir, "");
  return out.sort(compareCodePoints);
}

// sha256 over, per file in sorted order, its relpath, 0x00, its bytes and 0x00.
export function snapshot(dir: string, relpaths: string[]): string {
  const hasher = new Bun.CryptoHasher("sha256");
  const zero = new Uint8Array([0]);
  for (const rel of [...relpaths].sort(compareCodePoints)) {
    hasher.update(rel);
    hasher.update(zero);
    hasher.update(readFileSync(join(dir, ...rel.split("/"))));
    hasher.update(zero);
  }
  return hasher.digest("hex");
}

// The asset references index.html makes: module scripts and stylesheets.
function assetRefs(html: string): string[] {
  const refs: string[] = [];
  for (const tag of html.match(/<(script|link)\b[^>]*>/gi) ?? []) {
    const attr = (name: string) => new RegExp(`\\b${name}\\s*=\\s*(?:"([^"]*)"|'([^']*)'|([^\\s>]+))`, "i").exec(tag);
    const value = (name: string) => {
      const m = attr(name);
      return m ? (m[1] ?? m[2] ?? m[3] ?? "") : null;
    };
    if (/^<script/i.test(tag) && value("type") === "module" && value("src") !== null) refs.push(value("src")!);
    if (/^<link/i.test(tag) && (value("rel") ?? "").toLowerCase().split(/\s+/).includes("stylesheet") && value("href") !== null) refs.push(value("href")!);
  }
  return refs;
}

export function validateUiBuild(dir: string): string[] {
  if (!existsSync(dir) || !lstatSync(dir).isDirectory()) throw new CommandError(`no UI build at ${dir}; run bun run build:ui`);
  const problems: string[] = [];
  const label = `UI build ${dir}`;
  if (lstatSync(dir).isSymbolicLink()) problems.push(`${label} is a symlink`);
  const files = listFiles(dir, problems, label);
  if (!files.includes("index.html")) throw new CommandError(`no UI build at ${dir}; run bun run build:ui`);
  if (!files.some((f) => f.startsWith("assets/"))) problems.push(`${label} has no file under assets/`);
  for (const f of files) {
    const parts = f.split("/");
    const name = parts[parts.length - 1]!;
    if (name.endsWith(".map")) problems.push(`${label} contains a source map: ${f}`);
    if (name.startsWith(".env")) problems.push(`${label} contains an environment file: ${f}`);
    if (parts.some((p) => p === "node_modules" || p === "src" || p.startsWith("private"))) problems.push(`${label} contains a forbidden path: ${f}`);
  }
  const html = readFileSync(join(dir, "index.html"), "utf8");
  for (const ref of assetRefs(html)) {
    const bad = /^[a-z][a-z0-9+.-]*:/i.test(ref) || ref.startsWith("//") || ref.split(/[/\\]/).includes("..") || ref.includes("\\");
    const target = ref.replace(/^\.\//, "").replace(/^\//, "").replace(/[?#].*$/, "");
    if (bad) problems.push(`${label}: index.html references ${ref}, which is not a relative or root path`);
    else if (!files.includes(target)) problems.push(`${label}: index.html references ${ref}, which is not a file of the build`);
  }
  if (problems.length > 0) throw new ValidationError(problems);
  return files;
}

// A catalog input must be a regular file with no symlink at or above it inside the source root.
function readCatalogInput(root: string, rel: string, problems: string[]): Uint8Array | null {
  let at = root;
  const parts = rel.split("/");
  for (let i = 0; i < parts.length; i++) {
    at = join(at, parts[i]!);
    if (!existsSync(at) && !lstatExists(at)) {
      problems.push(`missing ${rel} under ${root}`);
      return null;
    }
    const st = lstatSync(at);
    if (st.isSymbolicLink()) {
      problems.push(`${rel}: ${parts.slice(0, i + 1).join("/")} is a symlink`);
      return null;
    }
    if (i === parts.length - 1 && !st.isFile()) {
      problems.push(`${rel} is not a regular file`);
      return null;
    }
  }
  return new Uint8Array(readFileSync(at));
}

function lstatExists(path: string): boolean {
  try {
    lstatSync(path);
    return true;
  } catch {
    return false;
  }
}

interface CatalogPlugin {
  id: string;
  version: string;
  description: string;
}

function manifestPlugins(bytes: Uint8Array, problems: string[]): CatalogPlugin[] {
  let doc: unknown;
  try {
    doc = JSON.parse(new TextDecoder().decode(bytes));
  } catch (err) {
    problems.push(`.claude-plugin/marketplace.json: invalid JSON: ${err instanceof Error ? err.message : String(err)}`);
    return [];
  }
  const plugins = (doc as Obj | null)?.plugins;
  if (!Array.isArray(plugins)) {
    problems.push(".claude-plugin/marketplace.json: plugins is not a list");
    return [];
  }
  const seen = new Set<string>();
  const out: CatalogPlugin[] = [];
  plugins.forEach((p, i) => {
    if (p === null || typeof p !== "object" || Array.isArray(p)) return problems.push(`.claude-plugin/marketplace.json: plugins[${i}] is not an object`);
    const o = p as Obj;
    if (typeof o.name !== "string" || o.name === "") return problems.push(`.claude-plugin/marketplace.json: plugins[${i}] has no string name`);
    if (seen.has(o.name)) problems.push(`.claude-plugin/marketplace.json: duplicate plugin name ${o.name}`);
    seen.add(o.name);
    out.push({ id: o.name, version: typeof o.version === "string" ? o.version : "", description: typeof o.description === "string" ? o.description : "" });
  });
  return out;
}

interface Workflow {
  id: string;
  name: string;
  guidance: string;
  plugins: string[];
}

function cells(line: string): string[] {
  let body = line.trim();
  if (body.startsWith("|")) body = body.slice(1);
  if (body.endsWith("|") && !body.endsWith("\\|")) body = body.slice(0, -1);
  return body.split(/(?<!\\)\|/).map((c) => c.trim());
}

export function workflowId(stage: string): string {
  return stage.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

// The first table after a "Choose a workflow" heading of level 2 or deeper.
export function parseWorkflows(text: string, pluginIds: Set<string>, problems: string[]): Workflow[] {
  const where = "docs/workflows.md";
  const lines = text.split(/\r?\n/);
  const heading = lines.findIndex((l) => /^#{2,}\s+Choose a workflow\s*#*\s*$/.test(l));
  if (heading < 0) {
    problems.push(`${where}: no "Choose a workflow" heading of level 2 or deeper`);
    return [];
  }
  let start = heading + 1;
  while (start < lines.length && !lines[start]!.trim().startsWith("|")) {
    if (/^#{1,6}\s/.test(lines[start]!)) break;
    start++;
  }
  const table: string[] = [];
  for (let i = start; i < lines.length && lines[i]!.trim().startsWith("|"); i++) table.push(lines[i]!);
  if (table.length < 3) {
    problems.push(`${where}: the workflow table needs a header row, a separator row and at least one row`);
    return [];
  }
  const header = cells(table[0]!);
  if (header.length !== 3 || header.some((h, i) => h !== HEADERS[i])) problems.push(`${where}: header cells must be ${HEADERS.map((h) => `"${h}"`).join(", ")}`);
  const separator = cells(table[1]!);
  if (separator.length !== 3 || separator.some((c) => !/^:?-+:?$/.test(c))) problems.push(`${where}: invalid separator row`);
  const byId = new Map<string, Workflow>();
  table.slice(2).forEach((line, i) => {
    const at = `${where}: workflow row ${i + 1}`;
    const row = cells(line);
    if (row.length !== 3 || row.some((c) => c === "")) return problems.push(`${at} must have exactly 3 non-empty cells`);
    const [stage, pluginCell, guidance] = row as [string, string, string];
    const id = workflowId(stage);
    if (id === "") return problems.push(`${at}: stage ${JSON.stringify(stage)} gives an empty workflow id`);
    const plugins: string[] = [];
    for (const m of pluginCell.matchAll(/\[([^\]]*)\]\(([^)]*)\)/g)) {
      const [, label, target] = m as unknown as [string, string, string];
      const t = /^\.\.\/plugins\/([^/]+)\/README\.md$/.exec(target);
      if (!t || t[1] !== label) problems.push(`${at}: plugin link [${label}](${target}) must read [<id>](../plugins/<id>/README.md)`);
      else if (!pluginIds.has(label)) problems.push(`${at}: ${label} is not a marketplace plugin`);
      else plugins.push(label);
    }
    if ([...pluginCell.matchAll(/\[([^\]]*)\]\(([^)]*)\)/g)].length === 0) problems.push(`${at}: no plugin link`);
    const wf: Workflow = { id, name: stage, guidance, plugins: [...new Set(plugins)].sort(compareCodePoints) };
    const prior = byId.get(id);
    if (prior && JSON.stringify(prior) !== JSON.stringify(wf)) problems.push(`${at}: workflow ${id} disagrees with an earlier row`);
    byId.set(id, prior ?? wf);
  });
  return [...byId.values()].sort((a, b) => compareCodePoints(a.id, b.id));
}

function sortKeys(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortKeys);
  if (value !== null && typeof value === "object") {
    const out: Obj = {};
    for (const k of Object.keys(value).sort(compareCodePoints)) out[k] = sortKeys((value as Obj)[k]);
    return out;
  }
  return value;
}

export function stableJson(value: unknown): string {
  return JSON.stringify(sortKeys(value), null, 2) + "\n";
}

export interface Catalog {
  plugins: { description: string; id: string; name: string; version: string; workflows: string[] }[];
  source_snapshot: string;
  workflows: Workflow[];
}

export function buildCatalog(sourceRoot: string): Catalog {
  const problems: string[] = [];
  const manifest = readCatalogInput(sourceRoot, ".claude-plugin/marketplace.json", problems);
  const workflowsMd = readCatalogInput(sourceRoot, "docs/workflows.md", problems);
  if (!manifest || !workflowsMd) throw new ValidationError(problems);
  const plugins = manifestPlugins(manifest, problems);
  const workflows = parseWorkflows(new TextDecoder().decode(workflowsMd), new Set(plugins.map((p) => p.id)), problems);
  if (problems.length > 0) throw new ValidationError(problems);
  const joined = new Uint8Array(manifest.length + 1 + workflowsMd.length);
  joined.set(manifest, 0);
  joined.set(workflowsMd, manifest.length + 1);
  return {
    plugins: [...plugins]
      .sort((a, b) => compareCodePoints(a.id, b.id))
      .map((p) => ({
        description: p.description,
        id: p.id,
        name: p.id,
        version: p.version,
        workflows: workflows.filter((w) => w.plugins.includes(p.id)).map((w) => w.id),
      })),
    source_snapshot: sha256Hex(joined),
    workflows,
  };
}

function isInside(child: string, parent: string): boolean {
  const rel = relative(parent, child);
  return rel === "" || (!rel.startsWith("..") && !isAbsolute(rel));
}

// The nearest existing ancestor's real path joined with the rest, so a path
// that does not exist yet can still be compared with the source root.
function realish(path: string): string {
  const abs = resolve(path);
  let at = abs;
  const rest: string[] = [];
  while (!existsSync(at)) {
    rest.unshift(basename(at));
    const up = dirname(at);
    if (up === at) break;
    at = up;
  }
  return join(realpathSync(at), ...rest);
}

export interface PackageOptions {
  sourceRoot: string;
  out: string;
  uiBuild?: string;
  quiet?: boolean;
}

export function buildPackage(o: PackageOptions): string {
  const out = resolve(o.out);
  if (lstatExists(out)) throw new CommandError(`${o.out} already exists`);
  if (!existsSync(o.sourceRoot) || !lstatSync(resolve(o.sourceRoot)).isDirectory()) throw new CommandError(`no source root at ${o.sourceRoot}`);
  const sourceRoot = realpathSync(o.sourceRoot);
  if (isInside(realish(out), sourceRoot)) throw new CommandError(`${o.out} is inside --source-root`);
  const uiBuild = resolve(o.uiBuild ?? join(REPO, "ui", "dist"));
  const uiFiles = validateUiBuild(uiBuild);
  const catalog = buildCatalog(sourceRoot);
  const migrationsDir = join(REPO, "pb_migrations");
  const migrations = readdirSync(migrationsDir).filter((n) => n.endsWith(".js")).sort(compareCodePoints);
  const receipt = {
    migrations,
    migrations_snapshot: snapshot(migrationsDir, migrations),
    source_snapshot: catalog.source_snapshot,
    ui_files: uiFiles,
    ui_snapshot: snapshot(uiBuild, uiFiles),
  };

  // Build beside the target and rename at the end, so a failure leaves nothing.
  const created: string[] = [];
  for (let d = dirname(out); !existsSync(d); d = dirname(d)) created.unshift(d);
  const staging = `${out}.partial-${process.pid}`;
  try {
    mkdirSync(dirname(out), { recursive: true });
    mkdirSync(staging);
    const put = (rel: string, content: string | Uint8Array) => {
      const path = join(staging, ...rel.split("/"));
      mkdirSync(dirname(path), { recursive: true });
      writeFileSync(path, content);
    };
    put("Dockerfile", DOCKERFILE);
    put("start.sh", START_SH);
    chmodSync(join(staging, "start.sh"), 0o755);
    put("railway.toml", RAILWAY_TOML);
    put("pb_hooks/toolbox_catalog.pb.js", readFileSync(join(REPO, "pb_hooks", "toolbox_catalog.pb.js")));
    put("pb_hooks/toolbox-catalog.json", stableJson(catalog));
    put("pb_hooks/toolbox-package.json", stableJson(receipt));
    for (const m of migrations) put(`pb_migrations/${m}`, readFileSync(join(migrationsDir, m)));
    for (const f of uiFiles) {
      const target = join(staging, "pb_public", ...f.split("/"));
      mkdirSync(dirname(target), { recursive: true });
      copyFileSync(join(uiBuild, ...f.split("/")), target);
    }
    renameSync(staging, out);
  } catch (err) {
    rmSync(staging, { recursive: true, force: true });
    for (const d of [...created].reverse()) rmSync(d, { recursive: true, force: true });
    throw new CommandError(`cannot build ${o.out}: ${err instanceof Error ? err.message : String(err)}`);
  }
  return out;
}

export async function packageCommand(o: PackageOptions): Promise<number> {
  buildPackage(o);
  console.log(`packaged ${o.out}`);
  return 0;
}

