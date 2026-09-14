import { type ApiResult, Session } from "./api";

export const pocketBaseLiteral = (value: string) => `'${value.replaceAll("\\", "\\\\").replaceAll("'", "\\'").replaceAll('"', '\\\"')}'`;

type PageOptions = {
  fields: string;
  page?: number;
  perPage?: number;
  filter?: string;
  sort?: string;
  signal?: AbortSignal;
};
export type Page<T> = { items: T[]; page: number; totalPages: number };

const stableSort = (sort: string) => sort.split(",").some((field) => field.replace(/^[+-]/, "") === "id") ? sort : `${sort},+id`;

export function pageRecords<T>(session: Session, collectionPath: string, options: PageOptions): Promise<ApiResult<Page<T>>> {
  const params = new URLSearchParams();
  if (options.filter) params.set("filter", options.filter);
  params.set("sort", stableSort(options.sort ?? "+created"));
  params.set("fields", options.fields);
  params.set("page", String(options.page ?? 1));
  params.set("perPage", String(options.perPage ?? 25));
  return session.request<Page<T>>(`${collectionPath}?${params}`, { signal: options.signal });
}

export type Catalog = { source_snapshot: string; workflows: unknown[]; plugins: unknown[] };
export const catalog = (session: Session, signal?: AbortSignal) => session.request<Catalog>("/api/toolbox/catalog", { signal });

export type DocumentationFile = { id: string; extender: string; role: string; content: string; relpath: string };
export const documentationFor = (session: Session, extender: string, signal?: AbortSignal) =>
  pageRecords<DocumentationFile>(session, "/api/collections/files/records", { fields: "id,extender,role,content,relpath", filter: `extender = ${pocketBaseLiteral(extender)}`, sort: "+relpath", signal });

export type Extender = { id: string; body: string; entry_file: string; source: string };
export const extenderById = (session: Session, id: string, signal?: AbortSignal) =>
  session.request<Extender>(`/api/collections/extenders/records/${encodeURIComponent(id)}?fields=id,body,entry_file,source`, { signal });

export type Assessment = { id: string; extender: string; framework: string; element: string; eval_run?: string };
export const assessmentsFor = (session: Session, extender: string, signal?: AbortSignal) =>
  pageRecords<Assessment>(session, "/api/collections/assessments/records", { fields: "id,extender,framework,element,eval_run", filter: `extender = ${pocketBaseLiteral(extender)}`, sort: "+created", signal });

export type JobCoverage = { id: string; job: string; eval_run?: string };
export const coverageFor = (session: Session, job: string, signal?: AbortSignal) =>
  pageRecords<JobCoverage>(session, "/api/collections/job_coverage/records", { fields: "id,job,eval_run", filter: `job = ${pocketBaseLiteral(job)}`, sort: "+created", signal });

export function safeHref(value: string): string | undefined {
  if (value.trim() !== value || value.includes("\\")) return undefined;
  if (value.startsWith("/") && !value.startsWith("//") && !value.includes("\\")) {
    const route = new URL(value, "https://toolbox.invalid");
    return route.pathname + route.search + route.hash;
  }
  try {
    if (!/^https?:\/\//i.test(value)) return undefined;
    const url = new URL(value);
    return (url.protocol === "http:" || url.protocol === "https:") && !url.username && !url.password ? url.href : undefined;
  } catch {
    return undefined;
  }
}
