import { type ApiResult, Session } from "./api";
import { pageRecords, pocketBaseLiteral, type Page } from "./data";
import { measurementNumber } from "./measurements";

export type Run = {
  id: string; harness: string; era?: string; campaign?: string; candidate: string; case: string;
  config?: "baseline" | "with"; kind?: string; trial?: number; model?: string; grader_model?: string;
  cli_version?: string; session_id?: string; passed?: boolean; skill_used?: boolean; exit_code?: number;
  num_turns?: number; cost_usd?: number; duration_ms?: number; input_tokens?: number;
  output_tokens?: number; cache_creation_tokens?: number; cache_read_tokens?: number; error?: string;
  workspace?: string; checks?: unknown; grades?: unknown; tool_names?: unknown; model_usage?: unknown;
  provenance?: unknown; measurement?: unknown; log_path?: string; ts?: string; created?: string; updated?: string;
};
export type Artifact = { id: string; run: string; kind?: string; mime?: string; blob?: string; sha256: string; byte_size?: number; text_ref?: string };
export type RunEvent = { id: string; run: string; seq?: number; artifact?: string; [key: string]: unknown };
export type ToolCall = { id: string; run: string; tool_call_id: string; tool_name: string; artifact?: string; [key: string]: unknown };
export type Campaign = { id: string; slug: string; kind: string; method?: string; criteria_text?: string; status?: string; notes?: string };
export type Response = { id: string; run: string; role: string; prompt?: string; response_text?: string; response_json?: unknown; measurement?: unknown };
export type Assessment = { id: string; extender: string; framework: string; element?: string; eval_run?: string; verdict: string; score?: number; evidence?: string; assessor?: string };

type RequestSession = Session;
type RunFilter = "all" | "baseline" | "with";
type SortDirection = "asc" | "desc";
export type KnownMetric = "duration_ms" | "cost_usd" | "input_tokens" | "output_tokens" | "cache_creation_tokens" | "cache_read_tokens" | "num_turns";
const RUN_FIELDS = "id,harness,era,campaign,candidate,case,config,trial,model,grader_model,cli_version,session_id,passed,skill_used,exit_code,num_turns,cost_usd,duration_ms,input_tokens,output_tokens,cache_creation_tokens,cache_read_tokens,error,checks,grades,tool_names,model_usage,provenance,measurement,log_path,ts,created,updated";
const ARTIFACT_FIELDS = "id,run,kind,mime,blob,sha256,byte_size,text_ref";
const EVENT_FIELDS = "id,run,seq,ts,vendor,role,event_type,tool_name,tool_call_id,status,is_error,input_tokens,output_tokens,cache_read_tokens,cache_write_tokens,cost_usd,wallclock_ms,text,payload,artifact,created,updated";
const TOOL_FIELDS = "id,run,tool_call_id,tool_name,input,output,status,is_error,wallclock_ms,started_ts,artifact,created,updated";

export function pageSize(value: number | undefined): 25 | 50 { return value === 50 ? 50 : 25; }
export function runSearchFilter(query = "", config: RunFilter = "all"): string | undefined {
  const term = query.trim();
  const family = term ? "(" + ["id", "campaign", "candidate", "case", "model", "harness"].map((field) => field + " ~ " + pocketBaseLiteral(term)).join(" || ") + ")" : "";
  const configuration = config === "all" ? "" : "config = " + pocketBaseLiteral(config);
  return [family, configuration].filter(Boolean).join(" && ") || undefined;
}
export function runs(session: RequestSession, options: { query?: string; config?: RunFilter; page?: number; perPage?: number; sort?: string; signal?: AbortSignal } = {}) {
  return pageRecords<Run>(session, "/api/collections/runs/records", { fields: RUN_FIELDS, filter: runSearchFilter(options.query, options.config), page: options.page, perPage: pageSize(options.perPage), sort: options.sort ?? "-created", signal: options.signal });
}
export const runById = (session: RequestSession, id: string, signal?: AbortSignal) => session.request<Run>("/api/collections/runs/records/" + encodeURIComponent(id) + "?fields=" + encodeURIComponent(RUN_FIELDS), { signal });
export function sortRuns(rows: readonly Run[], metric: KnownMetric, direction: SortDirection): Run[] {
  const multiplier = direction === "asc" ? 1 : -1;
  return [...rows].sort((left, right) => {
    const a = measurementNumber(left, metric); const b = measurementNumber(right, metric);
    if (a === null || b === null) return a === b ? left.id.localeCompare(right.id) : a === null ? 1 : -1;
    return (a - b) * multiplier || left.id.localeCompare(right.id) * multiplier;
  });
}
export const campaigns = (session: RequestSession, query = "", page = 1, signal?: AbortSignal) => {
  const term = query.trim();
  const filter = term ? "(" + ["id", "slug", "method", "criteria_text", "notes"].map((field) => field + " ~ " + pocketBaseLiteral(term)).join(" || ") + ")" : undefined;
  return pageRecords<Campaign>(session, "/api/collections/eval_runs/records", { fields: "id,slug,kind,method,criteria_text,status,notes,created,updated", filter, sort: "+slug", page, signal });
};
export const campaignById = (session: RequestSession, id: string, signal?: AbortSignal) => session.request<Campaign>("/api/collections/eval_runs/records/" + encodeURIComponent(id) + "?fields=id,slug,kind,method,criteria_text,status,notes,created,updated", { signal });
export const responsesForCampaign = (session: RequestSession, id: string, page = 1, signal?: AbortSignal) => pageRecords<Response>(session, "/api/collections/eval_responses/records", { fields: "id,run,role,agent_type,model,prompt,response_text,response_json,extenders,tokens,duration_ms,measurement,created,updated", filter: "run = " + pocketBaseLiteral(id), sort: "+created", page, signal });
export const assessmentsForCampaign = (session: RequestSession, id: string, page = 1, signal?: AbortSignal) => pageRecords<Assessment>(session, "/api/collections/assessments/records", { fields: "id,extender,framework,element,eval_run,verdict,score,evidence,assessor,created,updated", filter: "eval_run = " + pocketBaseLiteral(id), sort: "+created", page, signal });
export const artifactsForRun = (session: RequestSession, run: string, page = 1, signal?: AbortSignal) =>
  pageRecords<Artifact>(session, "/api/collections/artifacts/records", {
    fields: ARTIFACT_FIELDS, filter: "run = " + pocketBaseLiteral(run), sort: "+id", page, signal,
  });
export const artifactById = (session: RequestSession, id: string, signal?: AbortSignal) =>
  session.request<Artifact>("/api/collections/artifacts/records/" + encodeURIComponent(id) + "?fields=" + encodeURIComponent(ARTIFACT_FIELDS), { signal });
export const eventsForRun = (session: RequestSession, run: string, page = 1, signal?: AbortSignal) =>
  pageRecords<RunEvent>(session, "/api/collections/run_events/records", {
    fields: EVENT_FIELDS, filter: "run = " + pocketBaseLiteral(run), sort: "+seq", page, signal,
  });
export const toolCallsForRun = (session: RequestSession, run: string, page = 1, signal?: AbortSignal) =>
  pageRecords<ToolCall>(session, "/api/collections/tool_calls/records", {
    fields: TOOL_FIELDS, filter: "run = " + pocketBaseLiteral(run), sort: "+started_ts", page, signal,
  });
async function allPages<T>(load: (page: number) => Promise<ApiResult<Page<T>>>): Promise<ApiResult<T[]>> {
  const first = await load(1); if (first.kind !== "ok") return first;
  const items = [...first.data.items];
  for (let page = 2; page <= first.data.totalPages; page += 1) { const result = await load(page); if (result.kind !== "ok") return result; items.push(...result.data.items); }
  return { kind: "ok", data: items };
}
export type Evidence = { artifacts: Artifact[]; completeness: "complete" | "unknown" };
export async function evidenceForRun(session: RequestSession, run: string, signal?: AbortSignal): Promise<ApiResult<Evidence>> {
  const owned = await allPages((page) => artifactsForRun(session, run, page, signal)); if (owned.kind !== "ok") return owned;
  const [events, tools] = await Promise.all([allPages((page) => eventsForRun(session, run, page, signal)), allPages((page) => toolCallsForRun(session, run, page, signal))]);
  if (events.kind !== "ok" || tools.kind !== "ok") return { kind: "ok", data: { artifacts: deduplicateArtifacts(owned.data), completeness: "unknown" } };
  const ids = new Set([...events.data, ...tools.data].map((record) => record.artifact).filter((id): id is string => Boolean(id)));
  const referenced: Artifact[] = [];
  for (const id of ids) { const result = await session.request<Artifact>("/api/collections/artifacts/records/" + encodeURIComponent(id) + "?fields=" + encodeURIComponent(ARTIFACT_FIELDS), { signal }); if (result.kind !== "ok") return { kind: "ok", data: { artifacts: deduplicateArtifacts(owned.data), completeness: "unknown" } }; referenced.push(result.data); }
  return { kind: "ok", data: { artifacts: deduplicateArtifacts([...owned.data, ...referenced]), completeness: "complete" } };
}
function deduplicateArtifacts(artifacts: Artifact[]): Artifact[] { const seen = new Set<string>(); return artifacts.filter((artifact) => !seen.has(artifact.sha256) && (seen.add(artifact.sha256), true)); }
export function protectedArtifactUrl(artifact: Pick<Artifact, "id" | "blob">, fileToken: string): string | undefined { return artifact.id && artifact.blob && fileToken.trim() ? "/api/files/artifacts/" + encodeURIComponent(artifact.id) + "/" + encodeURIComponent(artifact.blob) + "?token=" + encodeURIComponent(fileToken) : undefined; }
export function artifactByteSize(artifact: Pick<Artifact, "byte_size">): number | null { return typeof artifact.byte_size === "number" && Number.isFinite(artifact.byte_size) && artifact.byte_size >= 0 ? artifact.byte_size : null; }
