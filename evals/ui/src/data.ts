import { type ApiResult, Session } from "./api";

export const pocketBaseLiteral = (value: string) => `'${value.replaceAll("\\", "\\\\").replaceAll("'", "\\'").replaceAll('"', '\\\"')}'`;

type PageOptions = {
  fields: string;
  page?: number;
  perPage?: number;
  filter?: string;
  sort?: string;
  expand?: string;
  signal?: AbortSignal;
};
export type Page<T> = { items: T[]; page: number; totalPages: number; totalItems: number };

const stableSort = (sort: string) => sort.split(",").some((field) => field.replace(/^[+-]/, "") === "id") ? sort : `${sort},+id`;

export function pageRecords<T>(session: Session, collectionPath: string, options: PageOptions): Promise<ApiResult<Page<T>>> {
  const params = new URLSearchParams();
  if (options.filter) params.set("filter", options.filter);
  if (options.expand) params.set("expand", options.expand);
  params.set("sort", stableSort(options.sort ?? "+created"));
  params.set("fields", options.fields);
  params.set("page", String(options.page ?? 1));
  params.set("perPage", String(options.perPage ?? 25));
  return session.request<Page<T>>(`${collectionPath}?${params}`, { signal: options.signal });
}

export type CatalogItem = { id?: string; name?: string; slug?: string; description?: string; guidance?: string; version?: string };
export type Catalog = { source_snapshot: string; workflows: CatalogItem[]; plugins: CatalogItem[] };
export const catalog = (session: Session, signal?: AbortSignal) => session.request<Catalog>("/api/toolbox/catalog", { signal });
export function filterCatalog(items: CatalogItem[], query: string) {
  const term = query.trim().toLowerCase();
  return term ? items.filter((item) => [item.id, item.name, item.slug, item.description, item.guidance].some((value) => value?.toLowerCase().includes(term))) : items;
}

export type DocumentationFile = { id: string; extender: string; role: string; content: string; relpath: string };
export const documentationFor = (session: Session, extender: string, page = 1, signal?: AbortSignal) =>
  pageRecords<DocumentationFile>(session, "/api/collections/files/records", { fields: "id,extender,role,content,relpath", filter: `extender = ${pocketBaseLiteral(extender)}`, sort: "+relpath", page, signal });

export type Source = {
  id: string;
  name?: string;
  url?: string;
  publisher_kind?: string;
  maintenance?: string;
};
export type Extender = {
  id: string;
  slug: string;
  name: string;
  kind: string;
  description: string;
  body: string;
  entry_file: string;
  source: string;
  expand?: { source?: Source };
};
export const extenderById = (session: Session, id: string, signal?: AbortSignal) =>
  session.request<Extender>(`/api/collections/extenders/records/${encodeURIComponent(id)}?fields=id,body,entry_file,source`, { signal });
export const sourceById = (session: Session, id: string, signal?: AbortSignal) =>
  session.request<Source>(`/api/collections/sources/records/${encodeURIComponent(id)}?fields=id,name,url,publisher_kind,maintenance`, { signal });

export type Distribution = { id: string; slug: string; kind: string; version: string; members: string[] };
export const distributions = (session: Session, page = 1, signal?: AbortSignal) =>
  pageRecords<Distribution>(session, "/api/collections/distributions/records", { fields: "id,slug,kind,version,members", sort: "+slug", page, signal });

export const extenders = (session: Session, query = "", page = 1, signal?: AbortSignal) =>
  pageRecords<Extender>(session, "/api/collections/extenders/records", { fields: "id,slug,name,kind,description,body,entry_file,source", filter: query ? `(slug ~ ${pocketBaseLiteral(query)} || name ~ ${pocketBaseLiteral(query)} || description ~ ${pocketBaseLiteral(query)})` : undefined, sort: "+slug", page, signal });

export type Assessment = { id: string; extender: string; framework: string; element: string; eval_run?: string };
export const assessmentsFor = (session: Session, extender: string, signal?: AbortSignal) =>
  pageRecords<Assessment>(session, "/api/collections/assessments/records", { fields: "id,extender,framework,element,eval_run", filter: `extender = ${pocketBaseLiteral(extender)}`, sort: "+created", signal });

export type JobCoverage = { id: string; job: string; eval_run?: string };
export const coverageFor = (session: Session, job: string, signal?: AbortSignal) =>
  pageRecords<JobCoverage>(session, "/api/collections/job_coverage/records", { fields: "id,job,eval_run", filter: `job = ${pocketBaseLiteral(job)}`, sort: "+created", signal });

export type RelatedRecord = { id?: string; name?: string };
export type Evaluation = Assessment & {
  verdict: string;
  evidence: string;
  assessor: string;
  expand?: { extender?: RelatedRecord; framework?: RelatedRecord; element?: RelatedRecord };
};
export function evaluations(session: Session, page?: number, signal?: AbortSignal): Promise<ApiResult<Page<Evaluation>>>;
export function evaluations(session: Session, extender?: string, page?: number, signal?: AbortSignal): Promise<ApiResult<Page<Evaluation>>>;
export function evaluations(session: Session, extenderOrPage: string | number = "", pageOrSignal: number | AbortSignal = 1, signal?: AbortSignal) {
  const extender = typeof extenderOrPage === "string" ? extenderOrPage : "";
  const page = typeof extenderOrPage === "number" ? extenderOrPage : typeof pageOrSignal === "number" ? pageOrSignal : 1;
  const requestSignal = typeof extenderOrPage === "number" ? pageOrSignal as AbortSignal : signal;
  return pageRecords<Evaluation>(session, "/api/collections/assessments/records", {
    fields: "id,framework,element,extender,eval_run,verdict,evidence,assessor,expand.extender.id,expand.extender.name,expand.framework.id,expand.framework.name,expand.element.id,expand.element.name",
    filter: extender ? `extender = ${pocketBaseLiteral(extender)}` : undefined,
    expand: "extender,framework,element",
    sort: "+created",
    page,
    signal: requestSignal,
  });
}
export type Coverage = JobCoverage & { status: string; disposition: string; rationale: string; expand?: { job?: { id?: string; name?: string } } };
export const jobCoverage = (session: Session, page = 1, signal?: AbortSignal) =>
  pageRecords<Coverage>(session, "/api/collections/job_coverage/records", { fields: "id,job,eval_run,status,disposition,rationale,expand.job.id,expand.job.name", expand: "job", sort: "+created", page, signal });

export function safeHref(value: string): string | undefined {
  if (value.trim() !== value || value.includes("\\")) return undefined;
  if (value.startsWith("/") && !value.startsWith("//")) {
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

export function recordScope(hash: string, key: string): string | undefined {
  const query = hash.indexOf("?");
  const value = new URLSearchParams(query === -1 ? "" : hash.slice(query + 1)).get(key)?.trim();
  return value || undefined;
}
