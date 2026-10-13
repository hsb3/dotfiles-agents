// Appendix A of SPEC.md, parsed from the spec itself, so the schema tests check
// the migrations against the document rather than against a second copy.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { REPO_ROOT } from "./pb.ts";

export interface FieldSpec {
  name: string;
  type: string;
  required: boolean;
  max?: number; // text
  values?: string[]; // select
  maxSelect?: number; // select, relation, file
  target?: string; // relation
  cascadeDelete?: boolean; // relation
  isNew: boolean; // a v1 addition
  newValues: string[]; // select values that are v1 additions
}

export interface CollectionSpec {
  name: string;
  type: "base" | "view";
  fields: FieldSpec[];
  indexes: string[];
  viewQuery?: string;
}

function splitTopLevel(s: string, sep: string): string[] {
  const out: string[] = [];
  let depth = 0;
  let inCode = false;
  let cur = "";
  for (let i = 0; i < s.length; i++) {
    const ch = s[i]!;
    if (ch === "`") inCode = !inCode;
    if (!inCode && (ch === "[" || ch === "(")) depth++;
    if (!inCode && (ch === "]" || ch === ")")) depth--;
    if (!inCode && depth === 0 && s.startsWith(sep, i)) {
      out.push(cur);
      cur = "";
      i += sep.length - 1;
      continue;
    }
    cur += ch;
  }
  out.push(cur);
  return out.map((p) => p.trim()).filter((p) => p !== "");
}

function parseField(raw: string): FieldSpec | null {
  let text = raw.trim();
  if (text.startsWith("`")) return null; // an index
  const isNew = /^\*\*.*\(new\)\*\*$/.test(text);
  if (isNew) text = text.replace(/^\*\*/, "").replace(/\s*\(new\)\*\*$/, "");
  const m = /^(\S+)\s+(text|number|bool|json|select|relation|file)\b(.*)$/.exec(text);
  if (!m) throw new Error(`unparsed field: ${raw}`);
  const [, name, type, restRaw] = m as unknown as [string, string, string, string];
  let rest = restRaw;
  const field: FieldSpec = { name, type, required: false, isNew, newValues: [] };
  const list = /\[([^\]]*)\]/.exec(rest);
  if (list && type === "select") {
    field.values = [];
    for (let v of list[1]!.split(",").map((x) => x.trim())) {
      const added = /\(new\)/.test(v);
      v = v.replace(/\*\*/g, "").replace(/\s*\(new\)/, "").trim();
      field.values.push(v);
      if (added) field.newValues.push(v);
    }
    rest = rest.replace(list[0], "");
  }
  const target = /→\s*(\w+)/.exec(rest);
  if (target) field.target = target[1];
  if (/\breq\b/.test(rest)) field.required = true;
  const max = /\bmax (\d+)/.exec(rest);
  if (type === "text") field.max = max ? Number(max[1]) : 0;
  if (type === "select") field.maxSelect = max ? Number(max[1]) : 1;
  if (type === "relation") {
    field.maxSelect = max ? Number(max[1]) : 1;
    field.cascadeDelete = /\bcascade\b/.test(rest) && !/no cascade/.test(rest);
  }
  if (type === "file") field.maxSelect = 1;
  return field;
}

export function appendixA(): CollectionSpec[] {
  const spec = readFileSync(join(REPO_ROOT, "SPEC.md"), "utf8");
  const start = spec.indexOf("## Appendix A");
  const end = spec.indexOf("## Appendix B");
  const lines = spec.slice(start, end).split("\n").filter((l) => l.startsWith("- **"));
  return lines.map((line) => {
    const m = /^- \*\*(\w+)\*\*(?: \(view[^)]*\))?: (.*)$/.exec(line)!;
    const name = m[1]!;
    const body = m[2]!;
    if (line.includes("(view")) {
      const q = /`(SELECT .*)`$/.exec(body)!;
      return { name, type: "view", fields: [], indexes: [], viewQuery: q[1] } satisfies CollectionSpec;
    }
    const parts = splitTopLevel(body, " · ");
    const fields: FieldSpec[] = [];
    const indexes: string[] = [];
    for (const part of parts) {
      // An index may share its part with the last field ("notes text. `CREATE ...`").
      const idx = [...part.matchAll(/``\s?(CREATE [^`]*?(?:`[^`]+`[^`]*?)*)\s?``|`(CREATE [^`]+)`/g)];
      for (const i of idx) indexes.push((i[1] ?? i[2])!.trim());
      const fieldText = part.replace(/\.?\s*``.*$|\.?\s*`CREATE.*$/, "").trim();
      if (fieldText) {
        const f = parseField(fieldText);
        if (f) fields.push(f);
      }
    }
    return { name, type: "base", fields, indexes } satisfies CollectionSpec;
  });
}

// The legacy schema: Appendix A without the v1 additions.
export function legacySchema(): CollectionSpec[] {
  return appendixA().map((c) => ({
    ...c,
    fields: c.fields
      .filter((f) => !f.isNew)
      .map((f) => (f.values ? { ...f, values: f.values.filter((v) => !f.newValues.includes(v)) } : f)),
  }));
}

// A collection create body for the REST API, relations resolved through `ids`.
export function restBody(c: CollectionSpec, ids: Record<string, string>): Record<string, unknown> {
  if (c.type === "view") return { name: c.name, type: "view", viewQuery: c.viewQuery };
  const fields: Record<string, unknown>[] = c.fields.map((f) => {
    const base: Record<string, unknown> = { name: f.name, type: f.type, required: f.required };
    if (f.type === "text") base.max = f.max;
    if (f.type === "json") base.maxSize = 2000000;
    if (f.type === "select") Object.assign(base, { values: f.values, maxSelect: f.maxSelect });
    if (f.type === "relation")
      Object.assign(base, { collectionId: ids[f.target!], maxSelect: f.maxSelect, minSelect: 0, cascadeDelete: f.cascadeDelete });
    if (f.type === "file")
      Object.assign(base, { maxSelect: 1, maxSize: 10000000, mimeTypes: [], thumbs: [], protected: true });
    return base;
  });
  fields.push({ name: "created", type: "autodate", onCreate: true, onUpdate: false });
  fields.push({ name: "updated", type: "autodate", onCreate: true, onUpdate: true });
  return { name: c.name, type: "base", fields, indexes: c.indexes };
}
