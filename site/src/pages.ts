// Selects the pages a config lists from the checkout, gives each its output
// path and site URL, and checks the config rules that need the page list.
import { lstat, readdir, stat } from "node:fs/promises";
import { join, posix } from "node:path";
import { ConfigError, type SiteConfig } from "./config.ts";

export interface Page {
  /** The listed repo path, kept even when the file is a symlink. */
  path: string;
  /** Path under the output folder, such as `docs/codex-compatibility.html`. */
  output: string;
  /** `<base>/<output path>`, percent-encoded. */
  url: string;
}

export interface Site {
  config: SiteConfig;
  /** The checkout being rendered. */
  root: string;
  /** Pages sorted by listed path. */
  pages: Page[];
  byPath: Map<string, Page>;
}

/** Expands the config's page list against the checkout at `root`; throws a ConfigError listing every problem. */
export async function selectPages(config: SiteConfig, root: string): Promise<Site> {
  const problems: string[] = [];
  const problem = (text: string) => problems.push(`${config.label}: ${text}`);

  const selected = new Set<string>();
  for (const entry of config.pages) {
    if (!isRepoPath(entry)) {
      problem(`pages entry "${entry}" must be a repo-relative path`);
      continue;
    }
    const matches = await expand(root, entry.split("/"));
    if (matches.length === 0) problem(`pages entry "${entry}" matches no file`);
    for (const match of matches) selected.add(match);
  }
  for (const entry of config.exclude) {
    const pattern = entry.split("/");
    const matches = [...selected].filter((path) => matchPath(pattern, path.split("/")));
    if (matches.length === 0) problem(`exclude entry "${entry}" matches no page`);
    for (const match of matches) selected.delete(match);
  }

  const paths = [...selected].sort(compare);
  for (const [path, output] of Object.entries(config.rename)) {
    if (!selected.has(path)) problem(`rename page ${path} is not in the page list`);
    if (!isRepoPath(output)) problem(`rename of ${path} must be a relative output path: "${output}"`);
  }
  for (const [key, links] of [["nav", config.nav], ["footer", config.footer]] as const) {
    for (const link of links) {
      if (!selected.has(link.page)) problem(`${key} page ${link.page} is not in the page list`);
    }
  }

  const pages = paths.map((path) => {
    const output = config.rename[path] ?? path.replace(/\.md$/, ".html");
    return { path, output, url: siteUrl(config.base, output) };
  });
  if (!pages.some((page) => page.output === "index.html")) problem("no page publishes at index.html");
  const byOutput = new Map<string, string>();
  for (const page of pages) {
    const other = byOutput.get(page.output);
    if (other !== undefined) problem(`${other} and ${page.path} would both publish at ${page.output}`);
    else byOutput.set(page.output, page.path);
    if (isRepoPath(page.output) && page.output.split("/").some((segment) => segment.startsWith("."))) {
      problem(`${page.path} would publish at hidden path ${page.output}`);
    }
  }

  if (problems.length > 0) throw new ConfigError(problems);
  return { config, root, pages, byPath: new Map(pages.map((page) => [page.path, page])) };
}

/** Reads a page's Markdown source through its listed path. */
export function readSource(site: Site, page: Page): Promise<string> {
  return Bun.file(join(site.root, page.path)).text();
}

/** Percent-encodes each segment of a path, keeping `A–Z a–z 0–9 - . _ ~`. */
export function encodePath(path: string): string {
  return path.split("/").map(encodeSegment).join("/");
}

export function siteUrl(base: string, output: string): string {
  return `${base}/${encodePath(output)}`;
}

/** A GitHub URL for a repo path at `ref`: `blob` for a file, `tree` for a folder, `raw` for an image. */
export function githubUrl(repo: string, ref: string, kind: "blob" | "tree" | "raw", path: string): string {
  const prefix = kind === "raw" ? `https://raw.githubusercontent.com/${repo}` : `https://github.com/${repo}/${kind}`;
  return path === "" ? `${prefix}/${encodePath(ref)}` : `${prefix}/${encodePath(ref)}/${encodePath(path)}`;
}

function encodeSegment(segment: string): string {
  let out = "";
  for (const byte of new TextEncoder().encode(segment)) {
    const char = String.fromCharCode(byte);
    out += /^[A-Za-z0-9\-._~]$/.test(char) ? char : `%${byte.toString(16).toUpperCase().padStart(2, "0")}`;
  }
  return out;
}

/** A relative path with no empty, `.` or `..` segment. */
function isRepoPath(path: string): boolean {
  return path.split("/").every((segment) => segment !== "" && segment !== "." && segment !== "..");
}

function compare(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

/** Whether one pattern segment matches one name: `*` stays within the segment and never matches a leading `.`. */
function matchSegment(pattern: string, name: string): boolean {
  if (!pattern.includes("*")) return pattern === name;
  if (name.startsWith(".") && !pattern.startsWith(".")) return false;
  const source = pattern.split("*").map((part) => part.replace(/[.+?^${}()|[\]\\]/g, "\\$&")).join("[^/]*");
  return new RegExp(`^${source}$`).test(name);
}

/** Whether pattern segments match path segments; `**` matches zero or more segments that do not start with `.`. */
function matchPath(pattern: string[], path: string[]): boolean {
  const [head, ...rest] = pattern;
  if (head === undefined) return path.length === 0;
  if (head === "**") {
    if (matchPath(rest, path)) return true;
    return path.length > 0 && !path[0]!.startsWith(".") && matchPath(pattern, path.slice(1));
  }
  return path.length > 0 && matchSegment(head, path[0]!) && matchPath(rest, path.slice(1));
}

/** Repo paths of the `.md` files the pattern matches. `**` does not descend into symlinked folders. */
async function expand(root: string, pattern: string[], at = ""): Promise<string[]> {
  const [head, ...rest] = pattern;
  if (head === undefined) return (await isMarkdownFile(join(root, at))) ? [at] : [];
  const found: string[] = [];
  if (head === "**") {
    found.push(...(await expand(root, rest, at)));
    for (const name of await list(join(root, at))) {
      const child = posix.join(at, name);
      if (!name.startsWith(".") && (await lstat(join(root, child))).isDirectory()) {
        found.push(...(await expand(root, pattern, child)));
      }
    }
  } else if (head.includes("*")) {
    for (const name of await list(join(root, at))) {
      if (matchSegment(head, name)) found.push(...(await expand(root, rest, posix.join(at, name))));
    }
  } else if (await exists(join(root, at, head))) {
    found.push(...(await expand(root, rest, posix.join(at, head))));
  }
  return [...new Set(found)];
}

async function list(dir: string): Promise<string[]> {
  try {
    return (await readdir(dir)).sort(compare);
  } catch {
    return [];
  }
}

async function exists(path: string): Promise<boolean> {
  try {
    await lstat(path);
    return true;
  } catch {
    return false;
  }
}

async function isMarkdownFile(path: string): Promise<boolean> {
  if (!path.endsWith(".md")) return false;
  try {
    return (await stat(path)).isFile();
  } catch {
    return false;
  }
}
