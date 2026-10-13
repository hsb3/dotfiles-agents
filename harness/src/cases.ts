// A candidate's case dataset: <cases-dir>/<candidate>/<case-id>/case.json with
// an optional fixture/ and check.py. Loader errors are bad input; callers turn
// them into exit 2.
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

export interface Assertion {
  id: string;
  text: string;
}

export interface Case {
  id: string;
  dir: string;
  prompt: string;
  assertions: Assertion[];
  /** The fixture directory copied as the workspace, or null for an empty one. */
  fixture: string | null;
  /** The case's check.py, or null. */
  check: string | null;
}

function isDir(path: string): boolean {
  return existsSync(path) && statSync(path).isDirectory();
}

function parseCase(id: string, dir: string): Case {
  const file = join(dir, "case.json");
  let data: unknown;
  try {
    data = JSON.parse(readFileSync(file, "utf8"));
  } catch {
    throw new Error(`${file}: not valid JSON`);
  }
  const obj = (typeof data === "object" && data !== null && !Array.isArray(data) ? data : {}) as Record<string, unknown>;
  if (typeof obj.prompt !== "string" || obj.prompt === "") throw new Error(`${file}: missing required field 'prompt'`);
  const raw = obj.assertions ?? [];
  const valid =
    Array.isArray(raw) &&
    raw.every((a) => typeof a === "object" && a !== null && typeof a.id === "string" && typeof a.text === "string");
  if (!valid) throw new Error(`${file}: every assertion needs 'id' and 'text'`);
  const check = join(dir, "check.py");
  return {
    id,
    dir,
    prompt: obj.prompt,
    assertions: (raw as Assertion[]).map((a) => ({ id: a.id, text: a.text })),
    fixture: isDir(join(dir, "fixture")) ? join(dir, "fixture") : null,
    check: existsSync(check) && statSync(check).isFile() ? check : null,
  };
}

/** Loads the cases of `candidate` under `casesDir`, sorted by id, or only `caseId`. */
export function loadCases(casesDir: string, candidate: string, caseId?: string): Case[] {
  const root = join(casesDir, candidate);
  if (!isDir(root)) throw new Error(`no eval cases at ${root} — copy cases/_template to author some`);
  const ids = readdirSync(root)
    .filter((id) => existsSync(join(root, id, "case.json")))
    .filter((id) => caseId === undefined || id === caseId)
    .sort();
  if (ids.length === 0) {
    throw new Error(`no case.json found under ${root}${caseId === undefined ? "" : ` for --case ${caseId}`}`);
  }
  return ids.map((id) => parseCase(id, join(root, id)));
}
