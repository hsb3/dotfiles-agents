// The LLM rubric grader: always claude --bare with a JSON schema, isolated in
// its own per-run home. Anything but a grades array fails every assertion.
import { lstatSync, readdirSync } from "node:fs";
import { join } from "node:path";
import type { Assertion } from "./cases.ts";
import { claude, claudeRunEnv } from "./claude.ts";
import { scrubEnv } from "./harnesses.ts";
import type { Entry } from "./ledger.ts";
import { runProcess, type Env } from "./subprocess.ts";

const DIGEST_LINES = 80;
const RESULT_CHARS = 3000;

export const GRADES_SCHEMA = JSON.stringify({
  type: "object",
  properties: {
    grades: {
      type: "array",
      items: {
        type: "object",
        properties: { id: { type: "string" }, passed: { type: "boolean" }, evidence: { type: "string" } },
        required: ["id", "passed", "evidence"],
      },
    },
  },
  required: ["grades"],
});

function listFiles(root: string, rel = ""): { path: string; size: number }[] {
  const out: { path: string; size: number }[] = [];
  for (const name of readdirSync(join(root, rel))) {
    const path = rel ? `${rel}/${name}` : name;
    const st = lstatSync(join(root, path), { throwIfNoEntry: false }); // symlinks are listed, not followed
    if (!st) continue;
    if (st.isDirectory()) out.push(...listFiles(root, path));
    else out.push({ path, size: st.size });
  }
  return out;
}

/** Every file under the workspace as `<path> (<size>B)`, sorted, capped at 80 lines. */
export function workspaceDigest(ws: string): string {
  const files = listFiles(ws).sort((a, b) => (a.path < b.path ? -1 : a.path > b.path ? 1 : 0));
  if (files.length === 0) return "(empty)";
  const lines = files.slice(0, DIGEST_LINES).map((f) => `${f.path} (${f.size}B)`);
  if (files.length > DIGEST_LINES) lines.push(`... and ${files.length - DIGEST_LINES} more`);
  return lines.join("\n");
}

export function graderPrompt(digest: string, result: string | null, assertions: Assertion[]): string {
  return `You are an impartial grader for a coding-agent trial. Judge each assertion against the trial workspace (your current directory) and the agent's final response below. You may Read/Grep/Glob files. Be strict: an assertion passes only with concrete evidence you can cite (file path + line, or a quoted excerpt). If you cannot determine an assertion, mark it failed with evidence starting 'unknown:'. Do not give benefit of the doubt.

Workspace files:
${digest}

Agent's final response (truncated):
${(result ?? "").slice(0, RESULT_CHARS)}

Assertions (JSON):
${JSON.stringify(assertions)}

Return JSON matching the schema: every assertion id exactly once.`;
}

export function graderArgv(prompt: string, model: string): string[] {
  return [
    claude.exe,
    "-p",
    prompt,
    "--bare",
    "--model",
    model,
    "--output-format",
    "json",
    "--json-schema",
    GRADES_SCHEMA,
    "--allowedTools",
    "Read,Grep,Glob",
    "--setting-sources",
    "",
    "--strict-mcp-config",
  ];
}

/** The grades in a grader's stdout, or null when it holds no grades array. */
export function parseGrades(stdout: string): Entry[] | null {
  try {
    const grades = JSON.parse(stdout)?.structured_output?.grades;
    return Array.isArray(grades) ? grades : null;
  } catch {
    return null;
  }
}

export interface GradeRequest {
  runDir: string;
  ws: string;
  result: string | null;
  assertions: Assertion[];
  model: string;
  timeoutSec: number;
  baseEnv: Env | NodeJS.ProcessEnv;
}

/** Grades the assertions; every failure marks each one failed with `grader-error`. */
export async function grade(req: GradeRequest): Promise<Entry[]> {
  const env = { ...scrubEnv(req.baseEnv, claude.scrubPrefix), ...claudeRunEnv(join(req.runDir, "grader-home"), join(req.runDir, "grader-config")) };
  const prompt = graderPrompt(workspaceDigest(req.ws), req.result, req.assertions);
  const r = await runProcess(graderArgv(prompt, req.model), { cwd: req.ws, env, timeoutSec: req.timeoutSec });
  const grades = r.notFound || r.timedOut ? null : parseGrades(r.stdout);
  return grades ?? req.assertions.map((a) => ({ id: a.id, passed: false, evidence: "grader-error" }));
}
