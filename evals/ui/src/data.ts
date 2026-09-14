import { request, type ApiResult, type Fetcher } from "./api";

export const pocketBaseLiteral = (value: string) => `'${value.replaceAll("\\", "\\\\").replaceAll("'", "\\'").replaceAll('"', '\\\"')}'`;

type PageOptions = {
  fields: string;
  page?: number;
  perPage?: number;
  filter?: string;
  sort?: string;
  token: string;
  signal?: AbortSignal;
  fetcher?: Fetcher;
};
export type Page<T> = { items: T[]; page: number; totalPages: number };

export function pageRecords<T>(collectionPath: string, options: PageOptions): Promise<ApiResult<Page<T>>> {
  const params = new URLSearchParams();
  if (options.filter) params.set("filter", options.filter);
  params.set("sort", options.sort ?? "+created");
  params.set("fields", options.fields);
  params.set("page", String(options.page ?? 1));
  params.set("perPage", String(options.perPage ?? 25));
  return request<Page<T>>(`${collectionPath}?${params}`, options);
}

export type Catalog = { source_snapshot: string; workflows: unknown[]; plugins: unknown[] };
export const catalog = (token: string, fetcher?: Fetcher) => request<Catalog>("/api/toolbox/catalog", { token, fetcher });

export type DocumentationFile = { id: string; extender: string; role: string; content: string; relpath: string };
export const documentationFor = (extender: string, token: string, fetcher?: Fetcher) =>
  pageRecords<DocumentationFile>("/api/collections/files/records", { fields: "id,extender,role,content,relpath", filter: `extender = ${pocketBaseLiteral(extender)}`, sort: "+relpath", token, fetcher });

export type Extender = { id: string; body: string; entry_file: string };
export const extenderById = (id: string, token: string, fetcher?: Fetcher) =>
  request<Extender>(`/api/collections/extenders/records/${encodeURIComponent(id)}?fields=id,body,entry_file`, { token, fetcher });

export type Assessment = { id: string; extender: string; framework: string; element: string; eval_run?: string };
export const assessmentsFor = (extender: string, token: string, fetcher?: Fetcher) =>
  pageRecords<Assessment>("/api/collections/assessments/records", { fields: "id,extender,framework,element,eval_run", filter: `extender = ${pocketBaseLiteral(extender)}`, sort: "+created", token, fetcher });

export type JobCoverage = { id: string; job: string; eval_run?: string };
export const coverageFor = (job: string, token: string, fetcher?: Fetcher) =>
  pageRecords<JobCoverage>("/api/collections/job_coverage/records", { fields: "id,job,eval_run", filter: `job = ${pocketBaseLiteral(job)}`, sort: "+created", token, fetcher });
