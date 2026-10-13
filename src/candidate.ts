// The candidate extender: what kind it is (skill, plugin or agent set) and,
// for agents, each file's name, description and body. Loader errors are bad
// input; callers turn them into exit 2.
import { copyFileSync, existsSync, mkdtempSync, readdirSync, readFileSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";

export type Kind = "skill" | "plugin" | "agent";

export interface AgentDef {
  /** File name within the candidate dir. */
  file: string;
  name: string;
  description: string;
  body: string;
  model: string | null;
  tools: string | null;
}

export interface Candidate {
  /** The positional candidate name. */
  name: string;
  dir: string;
  kind: Kind;
  /** Skill name: the directory's base name. */
  skillName: string;
  /** Plugin name and version (plugin kind only). */
  plugin: { name: string; version: string } | null;
  agents: AgentDef[];
  /** Removes the temp dir made for a flat agent file; a no-op otherwise. */
  cleanup: () => void;
}

const FRONTMATTER = /^---\s*\n(.*?)\n---\s*\n?(.*)$/s;

function field(frontmatter: string, key: string): string | null {
  for (const line of frontmatter.split("\n")) {
    const m = new RegExp(`^${key}:\\s*(.+)$`).exec(line);
    if (m) return m[1]!.trim().replace(/^["']+|["']+$/g, "");
  }
  return null;
}

/** Parses one agent file per the frontmatter rules. */
export function parseAgent(file: string, text: string): AgentDef {
  const m = FRONTMATTER.exec(text);
  const frontmatter = m ? m[1]! : "";
  const body = (m ? m[2]! : text).trim();
  const stem = file.replace(/\.md$/, "");
  const name = field(frontmatter, "name") || stem;
  const description = field(frontmatter, "description") || (body.split("\n")[0] ?? "").slice(0, 200);
  return { file, name, description, body, model: field(frontmatter, "model"), tools: field(frontmatter, "tools") };
}

function isFile(path: string): boolean {
  return existsSync(path) && statSync(path).isFile();
}

function agentFiles(dir: string): string[] {
  return readdirSync(dir)
    .filter((f) => f.endsWith(".md") && f.toLowerCase() !== "readme.md" && isFile(join(dir, f)))
    .sort();
}

function pluginMeta(dir: string): { name: string; version: string } {
  let meta: Record<string, unknown> = {};
  try {
    const parsed = JSON.parse(readFileSync(join(dir, ".claude-plugin", "plugin.json"), "utf8"));
    if (parsed && typeof parsed === "object") meta = parsed;
  } catch {
    // An unreadable manifest still marks a plugin; its name and version default.
  }
  return {
    name: typeof meta.name === "string" && meta.name ? meta.name : basename(dir),
    version: typeof meta.version === "string" && meta.version ? meta.version : "0.0.0",
  };
}

/** Loads the candidate at `path` (a directory or a flat agent `.md` file). */
export function loadCandidate(name: string, path: string): Candidate {
  if (!existsSync(path)) throw new Error(`no such candidate path: ${path}`);
  let dir = path;
  let cleanup = () => {};
  if (!statSync(path).isDirectory()) {
    if (!path.endsWith(".md")) throw new Error(`${path}: not a directory or a flat agent .md file`);
    dir = mkdtempSync(join(tmpdir(), "agent-harness-candidate-"));
    copyFileSync(path, join(dir, basename(path)));
    const tmp = dir;
    const remove = () => rmSync(tmp, { recursive: true, force: true });
    process.once("exit", remove);
    cleanup = remove;
  }
  const base = { name, dir, skillName: basename(dir), plugin: null, agents: [], cleanup };
  if (isFile(join(dir, "SKILL.md"))) return { ...base, kind: "skill" };
  if (isFile(join(dir, ".claude-plugin", "plugin.json"))) return { ...base, kind: "plugin", plugin: pluginMeta(dir) };
  const files = agentFiles(dir);
  if (files.length === 0) {
    cleanup();
    throw new Error(`${path}: not recognizable as skill / agent / plugin`);
  }
  const agents = files.map((f) => parseAgent(f, readFileSync(join(dir, f), "utf8")));
  const seen = new Map<string, string>();
  for (const a of agents) {
    const first = seen.get(a.name);
    if (first !== undefined) {
      cleanup();
      throw new Error(`duplicate agent name '${a.name}': ${first} and ${a.file}`);
    }
    seen.set(a.name, a.file);
  }
  return { ...base, kind: "agent", agents };
}
