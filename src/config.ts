// Loads site.config.json and checks its shape. Every problem is reported as
// `<config path>: <problem>`; the page-list rules live in pages.ts.

export interface Link {
  label: string;
  page: string;
}

export interface SiteConfig {
  /** The config path as it appears in messages. */
  label: string;
  repo: string;
  ref: string;
  /** `/` plus one segment, such as `/dotfiles-agents`. */
  base: string;
  /** The base without its `/`, shown in titles and the header. */
  name: string;
  pages: string[];
  exclude: string[];
  rename: Record<string, string>;
  nav: Link[];
  footer: Link[];
}

/** One or more config problems, each already formatted as `<config path>: <problem>`. */
export class ConfigError extends Error {
  constructor(readonly problems: string[]) {
    super(problems.join("\n"));
  }
}

const KEYS = ["repo", "ref", "base", "pages", "exclude", "rename", "nav", "footer"];
const REQUIRED = ["repo", "ref"];
const BASE = /^\/[A-Za-z0-9_-]+$/;
const REPO = /^[^/\s]+\/([^/\s]+)$/;

/** Reads and validates the config at `path`; `label` is how messages name the file. */
export async function loadConfig(path: string, label: string): Promise<SiteConfig> {
  let text: string;
  try {
    text = await Bun.file(path).text();
  } catch (error) {
    throw new ConfigError([`${label}: cannot read config: ${reason(error)}`]);
  }
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch (error) {
    throw new ConfigError([`${label}: invalid JSON: ${reason(error)}`]);
  }
  return parseConfig(data, label);
}

/** Validates parsed config data, collecting every problem before throwing. */
export function parseConfig(data: unknown, label: string): SiteConfig {
  const problems: string[] = [];
  const problem = (text: string) => problems.push(`${label}: ${text}`);
  if (!isObject(data)) throw new ConfigError([`${label}: config must be a JSON object`]);

  for (const key of Object.keys(data)) if (!KEYS.includes(key)) problem(`unknown key "${key}"`);
  for (const key of REQUIRED) if (!(key in data)) problem(`missing key "${key}"`);

  const repo = optionalString(data, "repo", problem);
  if (repo !== undefined && !REPO.test(repo)) problem(`bad repo "${repo}": expected <owner>/<name>`);
  const ref = optionalString(data, "ref", problem);
  if (ref === "") problem(`"ref" must not be empty`);

  let base = optionalString(data, "base", problem);
  if (base !== undefined && !BASE.test(base)) {
    problem(`bad base "${base}": expected / followed by one segment of A-Z a-z 0-9 _ -`);
  }
  if (base === undefined && repo !== undefined) {
    const repoName = REPO.exec(repo)?.[1];
    if (repoName !== undefined) {
      base = `/${repoName}`;
      if (!BASE.test(base)) problem(`bad base "${base}" from repo: set "base" to / followed by one segment of A-Z a-z 0-9 _ -`);
    }
  }

  const pages = stringList(data, "pages", problem);
  const exclude = stringList(data, "exclude", problem);
  const rename = stringMap(data, "rename", problem);
  const nav = linkList(data, "nav", problem);
  const footer = linkList(data, "footer", problem);

  if (problems.length > 0) throw new ConfigError(problems);
  return {
    label,
    repo: repo!,
    ref: ref!,
    base: base!,
    name: base!.slice(1),
    pages,
    exclude,
    rename,
    nav,
    footer,
  };
}

type Report = (text: string) => void;

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function optionalString(data: Record<string, unknown>, key: string, problem: Report): string | undefined {
  const value = data[key];
  if (value === undefined) return undefined;
  if (typeof value !== "string") {
    problem(`"${key}" must be a string`);
    return undefined;
  }
  return value;
}

function stringList(data: Record<string, unknown>, key: string, problem: Report): string[] {
  const valid = (value: unknown) => Array.isArray(value) && value.every(isNonEmptyString);
  return checked(data, key, valid, [], `"${key}" must be a list of non-empty strings`, problem);
}

function stringMap(data: Record<string, unknown>, key: string, problem: Report): Record<string, string> {
  const valid = (value: unknown) => isObject(value) && Object.values(value).every(isNonEmptyString);
  return checked(data, key, valid, {}, `"${key}" must map page paths to non-empty output paths`, problem);
}

/** The value at `key` when `valid` accepts it; otherwise reports `message` and returns `fallback`. */
function checked<T>(
  data: Record<string, unknown>,
  key: string,
  valid: (value: unknown) => boolean,
  fallback: T,
  message: string,
  problem: Report,
): T {
  const value = data[key];
  if (value === undefined) return fallback;
  if (valid(value)) return value as T;
  problem(message);
  return fallback;
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value !== "";
}

function linkList(data: Record<string, unknown>, key: string, problem: Report): Link[] {
  const value = data[key];
  if (value === undefined) return [];
  if (!Array.isArray(value)) {
    problem(`"${key}" must be a list of { "label", "page" } entries`);
    return [];
  }
  const links: Link[] = [];
  value.forEach((entry, index) => {
    const where = `${key}[${index}]`;
    if (!isObject(entry)) {
      problem(`${where} must be a { "label", "page" } entry`);
      return;
    }
    for (const field of Object.keys(entry)) {
      if (field !== "label" && field !== "page") problem(`${where}: unknown key "${field}"`);
    }
    let ok = true;
    for (const field of ["label", "page"]) {
      if (!(field in entry)) {
        problem(`${where}: missing key "${field}"`);
        ok = false;
      } else if (typeof entry[field] !== "string" || entry[field] === "") {
        problem(`${where}: "${field}" must be a non-empty string`);
        ok = false;
      }
    }
    if (ok) links.push({ label: entry.label as string, page: entry.page as string });
  });
  return links;
}

function reason(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
