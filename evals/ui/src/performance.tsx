import { Button, Checkbox, Pagination, Select, SelectItem, Table, TableBody, TableCell, TableHead, TableHeader, TableRow, TextInput } from "@carbon/react";
import { ScaleTypes } from "@carbon/charts";
import { GroupedBarChart } from "@carbon/charts-react";
import { type ReactNode, useEffect, useRef, useState } from "react";
import { protectedFileToken, Session } from "./api";
import { recordScope } from "./data";
import { comparisonEligibility, descriptiveDelta, measurementBoolean, measurementNumber } from "./measurements";
import { artifactByteSize, assessmentsForCampaign, campaigns, campaignById, evidenceForRun, eventsForRun, protectedArtifactUrl, responsesForCampaign, runById, runs, toolCallsForRun, type Assessment, type Campaign, type Response, type Run, type RunEvent, type ToolCall } from "./performance-data";
import { Block, PageCrumbs, StateNotice } from "./ui";
import "./performance.scss";

type State = "loading" | "access" | "error" | "empty" | "populated";
type Paged<T> = { items: T[]; totalItems: number };
type ListFocus = "runs" | "campaigns" | null;
export type PerformanceListState = { page: number; campaignPage: number; focus: ListFocus };
export type PerformanceListAction = "runs-changed" | "campaigns-changed" | "return-runs" | "return-campaigns";

const unavailable = "Unavailable";
const href = (key: "run" | "campaign", id: string) => `#performance?${key}=${encodeURIComponent(id)}`;

const shown = (value: number | null, unit = "") => {
  if (value === null) return unavailable;
  const text = value !== 0 && Math.abs(value) < 0.001
    ? value.toExponential(2)
    : new Intl.NumberFormat("en-US", { maximumFractionDigits: 3 }).format(value);
  return `${text}${unit}`;
};

const asText = (value: unknown) => {
  if (value === undefined || value === null) return unavailable;
  return typeof value === "string" ? value : JSON.stringify(value);
};

const object = (value: unknown): Record<string, unknown> | null =>
  value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;

const v1Measurement = (record: { measurement?: unknown }) => {
  const measurement = object(record.measurement);
  return measurement?.version === 1 && object(measurement.available) ? measurement : null;
};

export function sourceRevision(run: { measurement?: unknown }): string | null {
  const sourceIdentity = object(v1Measurement(run)?.source_identity);
  const revision = object(sourceIdentity?.revision);
  return revision?.available === true && typeof revision.value === "string"
    ? revision.value
    : null;
}

export function executionValidity(run: { measurement?: unknown }) {
  const execution = object(v1Measurement(run)?.execution);
  return {
    validity: typeof execution?.validity === "string" ? execution.validity : null,
    reason: typeof execution?.reason === "string" ? execution.reason : null,
  };
}

export function executionPreconditions(run: { measurement?: unknown }): unknown | null {
  return object(v1Measurement(run)?.execution)?.preconditions ?? null;
}

export function responseMetric(response: { measurement?: unknown; [key: string]: unknown }, field: "tokens" | "duration_ms"): number | null {
  const available = object(v1Measurement(response)?.available);
  const value = response[field];
  return available?.[field] === true && typeof value === "number"
    && Number.isFinite(value) && value >= 0 ? value : null;
}

export function fileTokenResult(fresh: boolean, reply: { kind: string; token?: string }) {
  if (!fresh) return { state: "stale" as const };
  if (reply.kind === "ok" && typeof reply.token === "string" && reply.token.trim()) {
    return { state: "ready" as const, token: reply.token };
  }
  return { state: reply.kind === "access" ? "access" as const : "error" as const };
}

export function fileRequestIsCurrent(requests: ReadonlyMap<string, number>, id: string, request: number) {
  return requests.get(id) === request;
}

export function performanceListState(state: PerformanceListState, action: PerformanceListAction): PerformanceListState {
  if (action === "runs-changed") return { ...state, page: 1 };
  if (action === "campaigns-changed") return { ...state, campaignPage: 1 };
  return { ...state, focus: action === "return-runs" ? "runs" : "campaigns" };
}

export function exitStatus(run: Run): number | null {
  const measurement = run.measurement;
  if (!measurement || typeof measurement !== "object" || Array.isArray(measurement)) return null;
  const envelope = measurement as { version?: unknown; available?: unknown };
  if (envelope.version !== 1 || !envelope.available || typeof envelope.available !== "object" || Array.isArray(envelope.available)) return null;
  const available = envelope.available as Record<string, unknown>;
  return available.exit_code === true && typeof run.exit_code === "number"
    && Number.isFinite(run.exit_code) && Number.isInteger(run.exit_code)
    ? run.exit_code
    : null;
}

export function nextSelection(selected: Run[], run: Run): Run[] {
  if (selected.some((item) => item.id === run.id)) return selected.filter((item) => item.id !== run.id);
  return selected.length === 2 ? selected : [...selected, run].slice(0, 2);
}

function useLoad<T>(key: string, load: (signal: AbortSignal) => Promise<{ kind: string; data?: T }>) {
  const [result, setResult] = useState<{ state: State; data?: T }>({ state: "loading" });
  useEffect(() => {
    const controller = new AbortController();
    let current = true;
    setResult({ state: "loading" });
    load(controller.signal).then((reply) => {
      if (!current || controller.signal.aborted) return;
      const items = (reply.data as { items?: unknown[] } | undefined)?.items;
      const state = reply.kind === "ok"
        ? Array.isArray(items) && items.length === 0 ? "empty" : "populated"
        : reply.kind === "access" ? "access" : "error";
      setResult(reply.kind === "ok" ? { state, data: reply.data } : { state });
    });
    return () => {
      current = false;
      controller.abort();
    };
  }, [key]);
  return result;
}

function Pager({ page, total, onChange }: { page: number; total: number; onChange: (page: number) => void }) {
  return <Pagination page={page} pageSize={25} pageSizes={[25]} totalItems={total} onChange={(next) => onChange(next.page)} />;
}

function TableRegion({ label, children }: { label: string; children: ReactNode }) {
  return <div className="table-scroll" role="region" aria-label={label} tabIndex={0}>{children}</div>;
}

function valueSummary(value: unknown) {
  const record = object(value);
  if (record) return Object.keys(record).length ? Object.keys(record).join(", ") : "Empty object";
  return Array.isArray(value) ? `${value.length} entries` : asText(value);
}

function RunMetrics({ run }: { run: Run }) {
  const metric = (label: string, field: string, unit = "") => (
    <div key={field}>
      <dt>{label}</dt>
      <dd>{shown(measurementNumber(run, field), unit)}</dd>
    </div>
  );
  const observed = (label: string, field: string) => {
    const value = measurementBoolean(run, field);
    return <div key={field}><dt>{label}</dt><dd>{value === null ? unavailable : String(value)}</dd></div>;
  };
  const status = exitStatus(run);
  return <dl className="performance-metrics">
    {metric("Duration", "duration_ms", " ms")}
    {metric("Cost", "cost_usd", " USD")}
    {metric("Input tokens", "input_tokens", " tokens")}
    {metric("Output tokens", "output_tokens", " tokens")}
    {metric("Cache creation tokens", "cache_creation_tokens", " tokens")}
    {metric("Cache read tokens", "cache_read_tokens", " tokens")}
    {metric("Turns", "num_turns", " turns")}
    {observed("Passed", "passed")}
    {observed("Skill used", "skill_used")}
    <div><dt>Exit code (execution status)</dt><dd>{status === null ? unavailable : String(status)}</dd></div>
  </dl>;
}

function Comparison({ selected }: { selected: Run[] }) {
  const verdict = comparisonEligibility(selected);
  if (verdict.reason || !verdict.baseline || !verdict.with) {
    return <section className="surface performance-panel"><h2>Comparison</h2><p>Select one independently valid baseline and one with-configuration record with matching recorded identity. {verdict.reason ?? ""}</p></section>;
  }
  const baseline = verdict.baseline as Run;
  const withValue = verdict.with as Run;
  const metrics = (["duration_ms", "cost_usd"] as const).map((field) => {
    const baselineValue = measurementNumber(baseline, field);
    const withValueMetric = measurementNumber(withValue, field);
    return {
      field,
      label: field === "duration_ms" ? "Duration" : "Cost",
      unit: field === "duration_ms" ? "ms" : "USD",
      baselineValue,
      withValueMetric,
      delta: descriptiveDelta(baselineValue, withValueMetric),
    };
  });
  return <section className="surface performance-panel">
    <h2>Comparison</h2>
    <p>n=1 each. Differences mean with minus baseline; no causality, savings, significance, or installed-state claim.</p>
    <TableRegion label="Comparable recorded measurements">
      <Table>
        <caption>Comparable recorded measurements</caption>
        <TableHead>
          <TableRow>
            <TableHeader>Metric</TableHeader>
            <TableHeader>Baseline</TableHeader>
            <TableHeader>With configuration</TableHeader>
            <TableHeader>With minus baseline</TableHeader>
          </TableRow>
        </TableHead>
        <TableBody>{metrics.map((item) => <TableRow key={item.field}>
          <TableCell>{item.label}</TableCell>
          <TableCell>{shown(item.baselineValue, ` ${item.unit}`)}</TableCell>
          <TableCell>{shown(item.withValueMetric, ` ${item.unit}`)}</TableCell>
          <TableCell>{item.delta.delta === null ? unavailable : `${shown(item.delta.delta, ` ${item.unit}`)}${item.delta.percent === null ? " · % unavailable" : ` (${shown(item.delta.percent, "%")})`}`}</TableCell>
        </TableRow>)}</TableBody>
      </Table>
    </TableRegion>
    <TableRegion label="Comparable measurement sources">
      <Table>
        <caption>Recorded observation sources</caption>
        <TableHead><TableRow><TableHeader>Source</TableHeader><TableHeader>Baseline</TableHeader><TableHeader>With configuration</TableHeader></TableRow></TableHead>
        <TableBody>
          <TableRow><TableCell>Source time</TableCell><TableCell>{baseline.ts ?? unavailable}</TableCell><TableCell>{withValue.ts ?? unavailable}</TableCell></TableRow>
          <TableRow><TableCell>Ingestion time</TableCell><TableCell>{baseline.created ?? unavailable}</TableCell><TableCell>{withValue.created ?? unavailable}</TableCell></TableRow>
          <TableRow><TableCell>Source revision</TableCell><TableCell>{sourceRevision(baseline) ?? unavailable}</TableCell><TableCell>{sourceRevision(withValue) ?? unavailable}</TableCell></TableRow>
          <TableRow><TableCell>CLI version</TableCell><TableCell>{baseline.cli_version ?? unavailable}</TableCell><TableCell>{withValue.cli_version ?? unavailable}</TableCell></TableRow>
        </TableBody>
      </Table>
    </TableRegion>
    <div className="performance-charts">{metrics.map((item) => item.baselineValue === null || item.withValueMetric === null ? null : <div className="performance-chart" key={item.field}><GroupedBarChart data={[{ group: "Baseline", key: item.label, value: item.baselineValue }, { group: "With configuration", key: item.label, value: item.withValueMetric }]} options={{ title: item.label, height: "260px", axes: { left: { mapsTo: "value", title: item.unit, includeZero: true }, bottom: { mapsTo: "key", scaleType: ScaleTypes.LABELS } }, toolbar: { enabled: false }, animations: false }} /></div>)}</div>
  </section>;
}

function DetailRecord({ run }: { run: Run }) {
  const execution = executionValidity(run);
  const preconditions = executionPreconditions(run);
  return <section className="surface performance-panel">
    <h2>Run record</h2>
    <dl>
      <div><dt>Checks</dt><dd>{valueSummary(run.checks)}</dd></div>
      <div><dt>Grades</dt><dd>{valueSummary(run.grades)}</dd></div>
      <div><dt>Provenance</dt><dd>{valueSummary(run.provenance)}</dd></div>
      <div><dt>Execution validity</dt><dd>{execution.validity ?? unavailable}</dd></div>
      <div><dt>Execution reason</dt><dd>{execution.reason ?? unavailable}</dd></div>
      <div><dt>Preconditions</dt><dd>{valueSummary(preconditions)}</dd></div>
      <div><dt>Source time</dt><dd>{run.ts ?? unavailable}</dd></div>
      <div><dt>Ingestion time</dt><dd>{run.created ?? unavailable}</dd></div>
      <div><dt>Source revision</dt><dd>{sourceRevision(run) ?? unavailable}</dd></div>
      <div><dt>CLI version</dt><dd>{run.cli_version ?? unavailable}</dd></div>
    </dl>
    <details><summary>Raw measurement envelope</summary><pre>{asText(run.measurement)}</pre></details>
    <details><summary>Raw provenance</summary><pre>{asText(run.provenance)}</pre></details>
    <details><summary>Raw grades</summary><pre>{asText(run.grades)}</pre></details>
    <p>Source time is not interpreted when timezone is unknown; ingestion time is separate.</p>
  </section>;
}

function RunDetail({ session, id, back }: { session: Session; id: string; back: () => void }) {
  const [eventPage, setEventPage] = useState(1);
  const [toolPage, setToolPage] = useState(1);
  const [files, setFiles] = useState<Record<string, "loading" | "access" | "error">>({});
  const fileRequests = useRef(new Map<string, number>());
  const run = useLoad(`run:${id}`, (signal) => runById(session, id, signal));
  const evidence = useLoad(`evidence:${id}`, (signal) => evidenceForRun(session, id, signal));
  const events = useLoad(`events:${id}:${eventPage}`, (signal) => eventsForRun(session, id, eventPage, signal));
  const tools = useLoad(`tools:${id}:${toolPage}`, (signal) => toolCallsForRun(session, id, toolPage, signal));
  useEffect(() => () => {
    fileRequests.current.clear();
  }, []);
  const open = async (artifact: { id: string; blob?: string }) => {
    const request = (fileRequests.current.get(artifact.id) ?? 0) + 1;
    fileRequests.current.set(artifact.id, request);
    setFiles((old) => ({ ...old, [artifact.id]: "loading" }));
    const token = await protectedFileToken(session);
    if (!fileRequestIsCurrent(fileRequests.current, artifact.id, request)) return;
    const result = fileTokenResult(fileRequestIsCurrent(fileRequests.current, artifact.id, request), token);
    if (result.state === "stale") return;
    if (result.state !== "ready") {
      setFiles((old) => ({ ...old, [artifact.id]: result.state }));
      return;
    }
    const link = protectedArtifactUrl(artifact, result.token);
    if (!link) {
      setFiles((old) => ({ ...old, [artifact.id]: "error" }));
      return;
    }
    location.assign(link);
  };
  return <Block>
    <PageCrumbs current="Performance / run" />
    <Button kind="ghost" onClick={back}>Return to runs</Button>
    <h1>Run {id}</h1>
    {run.state !== "populated" || !run.data ? <StateNotice state={run.state === "populated" ? "empty" : run.state} subject="run detail" /> : <>
      <RunMetrics run={run.data} />
      <DetailRecord run={run.data} />
      <Evidence result={evidence} files={files} open={open} />
      <EventRecords result={events} page={eventPage} setPage={setEventPage} />
      <ToolRecords result={tools} page={toolPage} setPage={setToolPage} />
    </>}
  </Block>;
}

function Evidence({ result, files, open }: { result: ReturnType<typeof useLoad<{ artifacts: { id: string; blob?: string; sha256: string; byte_size?: number }[]; completeness: string }>>; files: Record<string, "loading" | "access" | "error">; open: (artifact: { id: string; blob?: string }) => void }) {
  return <section className="surface performance-panel">
    <h2>Evidence</h2>
    {result.state === "populated" && result.data ? <><p>Completeness: {result.data.completeness}.</p>{result.data.artifacts.map((artifact) => <p key={artifact.id}>{artifact.id} · {artifact.sha256} · {artifactByteSize(artifact) === null ? "size unavailable" : `${artifactByteSize(artifact)} bytes`} <Button kind="ghost" size="sm" onClick={() => open(artifact)} disabled={files[artifact.id] === "loading"}>Open evidence</Button>{files[artifact.id] === "loading" ? " Opening…" : files[artifact.id] === "access" ? " Access denied." : files[artifact.id] === "error" ? " Could not access evidence." : null}</p>)}</> : <StateNotice state={result.state === "populated" ? "empty" : result.state} subject="evidence" />}
  </section>;
}

function EventRecords({ result, page, setPage }: { result: ReturnType<typeof useLoad<Paged<RunEvent>>>; page: number; setPage: (page: number) => void }) {
  return <section className="surface performance-panel">
    <h2>Current events</h2>
    {result.state === "populated" ? <TableRegion label="Current run events"><Table><TableHead><TableRow><TableHeader>ID</TableHeader><TableHeader>Sequence</TableHeader><TableHeader>Role</TableHeader><TableHeader>Type</TableHeader><TableHeader>Status</TableHeader><TableHeader>Text and payload</TableHeader></TableRow></TableHead><TableBody>{result.data?.items.map((item) => <TableRow key={item.id}><TableCell>{item.id}</TableCell><TableCell>{asText(item.seq)}</TableCell><TableCell>{asText(item.role)}</TableCell><TableCell>{asText(item.event_type)}</TableCell><TableCell>{asText(item.status)}</TableCell><TableCell>{asText(item.text)}{item.payload === undefined ? null : <details><summary>Payload</summary><pre>{asText(item.payload)}</pre></details>}</TableCell></TableRow>)}</TableBody></Table></TableRegion> : <StateNotice state={result.state} subject="current events" />}
    {result.data && <Pager page={page} total={result.data.totalItems} onChange={setPage} />}
  </section>;
}

function ToolRecords({ result, page, setPage }: { result: ReturnType<typeof useLoad<Paged<ToolCall>>>; page: number; setPage: (page: number) => void }) {
  return <section className="surface performance-panel">
    <h2>Current tools</h2>
    {result.state === "populated" ? <TableRegion label="Current run tools"><Table><TableHead><TableRow><TableHeader>ID</TableHeader><TableHeader>Call</TableHeader><TableHeader>Tool</TableHeader><TableHeader>Status</TableHeader><TableHeader>Timing</TableHeader><TableHeader>Payload</TableHeader></TableRow></TableHead><TableBody>{result.data?.items.map((item) => <TableRow key={item.id}><TableCell>{item.id}</TableCell><TableCell>{item.tool_call_id}</TableCell><TableCell>{item.tool_name}</TableCell><TableCell>{asText(item.status)}</TableCell><TableCell>{asText(item.wallclock_ms)}</TableCell><TableCell><details><summary>Input and output</summary><pre>{asText({ input: item.input, output: item.output })}</pre></details></TableCell></TableRow>)}</TableBody></Table></TableRegion> : <StateNotice state={result.state} subject="current tools" />}
    {result.data && <Pager page={page} total={result.data.totalItems} onChange={setPage} />}
  </section>;
}

function CampaignFacts({ campaign }: { campaign: Campaign }) {
  return <section className="surface performance-panel"><h2>Campaign facts</h2><dl><div><dt>Slug</dt><dd>{campaign.slug}</dd></div><div><dt>Kind</dt><dd>{campaign.kind}</dd></div><div><dt>Method</dt><dd>{campaign.method ?? unavailable}</dd></div><div><dt>Criteria</dt><dd>{campaign.criteria_text ?? unavailable}</dd></div><div><dt>Status</dt><dd>{campaign.status ?? unavailable}</dd></div><div><dt>Notes</dt><dd>{campaign.notes ?? unavailable}</dd></div></dl></section>;
}

function ResponseRecords({ result, page, setPage }: { result: ReturnType<typeof useLoad<Paged<Response>>>; page: number; setPage: (page: number) => void }) {
  return <section className="surface performance-panel"><h2>Responses</h2>{result.state === "populated" ? <TableRegion label="Campaign responses"><Table><TableHead><TableRow><TableHeader>ID</TableHeader><TableHeader>Role</TableHeader><TableHeader>Prompt</TableHeader><TableHeader>Response</TableHeader><TableHeader>Tokens</TableHeader><TableHeader>Duration</TableHeader><TableHeader>Raw response evidence</TableHeader></TableRow></TableHead><TableBody>{result.data?.items.map((item) => <TableRow key={item.id}><TableCell>{item.id}</TableCell><TableCell>{item.role}</TableCell><TableCell>{item.prompt ?? unavailable}</TableCell><TableCell>{item.response_text ?? unavailable}</TableCell><TableCell>{shown(responseMetric(item, "tokens"), " tokens")}</TableCell><TableCell>{shown(responseMetric(item, "duration_ms"), " ms")}</TableCell><TableCell>{item.response_json === undefined ? unavailable : <details><summary>Response JSON</summary><pre>{asText(item.response_json)}</pre></details>}</TableCell></TableRow>)}</TableBody></Table></TableRegion> : <StateNotice state={result.state} subject="responses" />}{result.data && <Pager page={page} total={result.data.totalItems} onChange={setPage} />}</section>;
}

function AssessmentRecords({ result, page, setPage }: { result: ReturnType<typeof useLoad<Paged<Assessment>>>; page: number; setPage: (page: number) => void }) {
  return <section className="surface performance-panel"><h2>Current assessments</h2>{result.state === "populated" ? <TableRegion label="Campaign assessments"><Table><TableHead><TableRow><TableHeader>ID</TableHeader><TableHeader>Extender</TableHeader><TableHeader>Framework</TableHeader><TableHeader>Element</TableHeader><TableHeader>Verdict</TableHeader><TableHeader>Evidence</TableHeader></TableRow></TableHead><TableBody>{result.data?.items.map((item) => <TableRow key={item.id}><TableCell>{item.id}</TableCell><TableCell><a href={`#documentation?extender=${encodeURIComponent(item.extender)}`}>{item.expand?.extender?.name ?? item.extender}</a><br /><a href={`#evaluations?extender=${encodeURIComponent(item.extender)}`}>Assessments</a></TableCell><TableCell>{item.expand?.framework?.name ?? item.framework}</TableCell><TableCell>{item.expand?.element?.name ?? item.element ?? unavailable}</TableCell><TableCell>{item.verdict}</TableCell><TableCell>{item.evidence ?? unavailable}</TableCell></TableRow>)}</TableBody></Table></TableRegion> : <StateNotice state={result.state} subject="current assessments" />}{result.data && <Pager page={page} total={result.data.totalItems} onChange={setPage} />}</section>;
}

function CampaignDetail({ session, id, back }: { session: Session; id: string; back: () => void }) {
  const [responsePage, setResponsePage] = useState(1);
  const [assessmentPage, setAssessmentPage] = useState(1);
  const campaign = useLoad(`campaign:${id}`, (signal) => campaignById(session, id, signal));
  const responses = useLoad(`responses:${id}:${responsePage}`, (signal) => responsesForCampaign(session, id, responsePage, signal));
  const assessments = useLoad(`assessments:${id}:${assessmentPage}`, (signal) => assessmentsForCampaign(session, id, assessmentPage, signal));
  return <Block><PageCrumbs current="Performance / campaign" /><Button kind="ghost" onClick={back}>Return to campaigns</Button><h1>Campaign {id}</h1><p>Conformance is not independent output quality; associations are current and can change.</p>{campaign.state !== "populated" || !campaign.data ? <StateNotice state={campaign.state === "populated" ? "empty" : campaign.state} subject="campaign" /> : <CampaignFacts campaign={campaign.data} />}<ResponseRecords result={responses} page={responsePage} setPage={setResponsePage} /><AssessmentRecords result={assessments} page={assessmentPage} setPage={setAssessmentPage} /></Block>;
}

function CampaignList({ session, query, page, setQuery, setPage }: { session: Session; query: string; page: number; setQuery: (query: string) => void; setPage: (page: number) => void }) {
  const result = useLoad(`campaigns:${query}:${page}`, (signal) => campaigns(session, query, page, signal));
  return <section className="surface performance-panel"><h2 id="campaign-list" tabIndex={-1}>Campaign search</h2><TextInput id="campaign-search" labelText="Search campaigns" value={query} onChange={(event) => setQuery(event.currentTarget.value)} />{result.state === "populated" ? <ul>{result.data?.items.map((campaign) => <li key={campaign.id}><a href={href("campaign", campaign.id)}>{campaign.id}</a> · {campaign.slug}</li>)}</ul> : <StateNotice state={result.state} subject="campaigns" />}{result.data && <Pager page={page} total={result.data.totalItems} onChange={setPage} />}</section>;
}

export function Performance({ session, onExpired, hash = location.hash }: { session: Session; onExpired: () => void; hash?: string }) {
  const [query, setQuery] = useState("");
  const [config, setConfig] = useState<"all" | "baseline" | "with">("all");
  const [perPage, setPerPage] = useState<25 | 50>(25);
  const [sort, setSort] = useState<"id" | "duration_ms" | "cost_usd">("id");
  const [selected, setSelected] = useState<Run[]>([]);
  const [campaignQuery, setCampaignQuery] = useState("");
  const [listState, setListState] = useState<PerformanceListState>({ page: 1, campaignPage: 1, focus: null });
  const runId = recordScope(hash, "run");
  const campaignId = recordScope(hash, "campaign");
  const result = useLoad(`runs:${query}:${config}:${listState.page}:${perPage}:${sort}`, (signal) => runs(session, { query, config, page: listState.page, perPage, sort: "+id", ...(sort === "id" ? {} : { metricSort: { metric: sort, direction: "asc" } }), signal }));
  useEffect(() => {
    const unsubscribe = session.subscribe(() => { setSelected([]); onExpired(); });
    return () => { unsubscribe(); };
  }, [session, onExpired]);
  useEffect(() => { session.setSelection("performance", selected.map((run) => run.id)); }, [session, selected]);
  useEffect(() => {
    if (runId || campaignId || !listState.focus) return;
    document.getElementById(listState.focus === "runs" ? "performance-runs" : "campaign-list")?.focus();
    setListState((state) => ({ ...state, focus: null }));
  }, [campaignId, listState.focus, runId]);
  const rows: Run[] = result.data?.items ?? [];
  const resetRuns = () => setListState((state) => performanceListState(state, "runs-changed"));
  const resetCampaigns = () => setListState((state) => performanceListState(state, "campaigns-changed"));
  const returnTo = (action: "return-runs" | "return-campaigns") => {
    setListState((state) => performanceListState(state, action));
    location.hash = "#performance";
  };
  if (runId) return <RunDetail session={session} id={runId} back={() => returnTo("return-runs")} />;
  if (campaignId) return <CampaignDetail session={session} id={campaignId} back={() => returnTo("return-campaigns")} />;
  return <Block>
    <PageCrumbs current="Performance" />
    <h1>Performance</h1>
    <section className="surface performance-panel">
      <h2 id="performance-runs" tabIndex={-1}>Recorded runs</h2>
      <div className="performance-controls">
        <TextInput id="run-search" labelText="Search runs" value={query} onChange={(event) => {
          resetRuns();
          setQuery(event.currentTarget.value);
        }} />
        <Select id="configuration" labelText="Configuration" value={config} onChange={(event) => {
          resetRuns();
          setConfig(event.currentTarget.value as typeof config);
        }}>
          <SelectItem value="all" text="All configurations" />
          <SelectItem value="baseline" text="Baseline" />
          <SelectItem value="with" text="With configuration" />
        </Select>
        <Select id="sort" labelText="Sort" value={sort} onChange={(event) => {
          resetRuns();
          setSort(event.currentTarget.value as typeof sort);
        }}>
          <SelectItem value="id" text="Record ID" />
          <SelectItem value="duration_ms" text="Duration" />
          <SelectItem value="cost_usd" text="Cost" />
        </Select>
      </div>
      {selected.length > 0 && <aside className="selection-tray">
        <strong>Selected ({selected.length}/2)</strong>
        {selected.map((run) => <Button key={run.id} kind="ghost" size="sm" onClick={() => setSelected((old) => nextSelection(old, run))}>
          {run.id}{rows.some((row) => row.id === run.id) ? "" : " (off page)"} ×
        </Button>)}
      </aside>}
      {result.state === "populated" ? <div className="table-scroll" role="region" aria-label="Recorded runs" tabIndex={0}>
        <Table>
          <caption>Recorded performance runs</caption>
          <TableHead>
            <TableRow>
              <TableHeader>Select</TableHeader>
              <TableHeader>Record</TableHeader>
              <TableHeader>Configuration</TableHeader>
              <TableHeader>Identity</TableHeader>
              <TableHeader>Execution</TableHeader>
              <TableHeader>Grade</TableHeader>
              <TableHeader>Outcome</TableHeader>
              <TableHeader>Duration</TableHeader>
              <TableHeader>Cost</TableHeader>
              <TableHeader>Evidence</TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>{rows.map((run) => {
            const outcome = measurementBoolean(run, "passed");
            return <TableRow key={run.id}>
              <TableCell><Checkbox id={`select-${run.id}`} labelText={`Select run ${run.id}`} hideLabel checked={selected.some((item) => item.id === run.id)} disabled={!selected.some((item) => item.id === run.id) && selected.length === 2} onChange={() => setSelected((old) => nextSelection(old, run))} /></TableCell>
              <TableCell>{run.id}<br />Campaign: {run.campaign ?? unavailable}</TableCell>
              <TableCell>{run.config ?? unavailable}</TableCell>
              <TableCell>Harness: {run.harness}<br />Model: {run.model ?? unavailable}<br />Candidate: {run.candidate}<br />Case: {run.case}</TableCell>
              <TableCell>{executionValidity(run).validity ?? unavailable}</TableCell>
              <TableCell>{asText(run.grades)}</TableCell>
              <TableCell>{outcome === null ? unavailable : String(outcome)}</TableCell>
              <TableCell>{shown(measurementNumber(run, "duration_ms"), " ms")}</TableCell>
              <TableCell>{shown(measurementNumber(run, "cost_usd"), " USD")}</TableCell>
              <TableCell><a href={href("run", run.id)}>Inspect</a></TableCell>
            </TableRow>;
          })}</TableBody>
        </Table>
      </div> : <StateNotice state={result.state} subject="runs" />}
      {result.data && <Pagination page={listState.page} pageSize={perPage} pageSizes={[25, 50]} totalItems={result.data.totalItems} onChange={(next) => {
        setListState((state) => ({ ...state, page: next.page }));
        setPerPage(next.pageSize as 25 | 50);
      }} />}
    </section>
    <Comparison selected={selected} />
    <CampaignList session={session} query={campaignQuery} page={listState.campaignPage} setQuery={(value) => {
      resetCampaigns();
      setCampaignQuery(value);
    }} setPage={(campaignPage) => setListState((state) => ({ ...state, campaignPage }))} />
  </Block>;
}
