import { Button, Checkbox, Pagination, Select, SelectItem, TextInput } from "@carbon/react";
import { ScaleTypes } from "@carbon/charts";
import { GroupedBarChart } from "@carbon/charts-react";
import { useEffect, useMemo, useState } from "react";
import { protectedFileToken, Session } from "./api";
import { recordScope } from "./data";
import { comparisonEligibility, descriptiveDelta, measurementBoolean, measurementNumber } from "./measurements";
import { artifactByteSize, assessmentsForCampaign, campaigns, campaignById, evidenceForRun, eventsForRun, protectedArtifactUrl, responsesForCampaign, runById, runs, toolCallsForRun, type Run } from "./performance-data";
import { Block, PageCrumbs, StateNotice } from "./ui";
import "./performance.scss";

type State = "loading" | "access" | "error" | "empty" | "populated";
const unavailable = "Unavailable";
const href = (key: "run" | "campaign", id: string) => `#performance?${key}=${encodeURIComponent(id)}`;
const shown = (value: number | null, unit = "") => value === null ? unavailable : `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 3 }).format(value)}${unit}`;

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
      const emptyPage = reply.kind === "ok" && Array.isArray((reply.data as { items?: unknown[] } | undefined)?.items) && !(reply.data as { items: unknown[] }).items.length;
      setResult(reply.kind === "ok" ? { state: emptyPage ? "empty" : "populated", data: reply.data } : { state: reply.kind === "access" ? "access" : "error" });
    });
    return () => { current = false; controller.abort(); };
  }, [key]);
  return result;
}

function Pager({ page, total, onChange }: { page: number; total: number; onChange: (page: number) => void }) {
  return <Pagination page={page} pageSize={25} pageSizes={[25]} totalItems={total} onChange={(next) => onChange(next.page)} />;
}

function RunMetrics({ run }: { run: Run }) {
  const metric = (label: string, field: string, unit = "") => <div key={field}><dt>{label}</dt><dd>{shown(measurementNumber(run, field), unit)}</dd></div>;
  const observed = (label: string, field: string) => <div key={field}><dt>{label}</dt><dd>{measurementBoolean(run, field) === null ? unavailable : String(measurementBoolean(run, field))}</dd></div>;
  return <dl className="performance-metrics">{metric("Duration", "duration_ms", " ms")}{metric("Cost", "cost_usd", " USD")}{metric("Input tokens", "input_tokens", " tokens")}{metric("Output tokens", "output_tokens", " tokens")}{metric("Cache creation tokens", "cache_creation_tokens", " tokens")}{metric("Cache read tokens", "cache_read_tokens", " tokens")}{metric("Turns", "num_turns", " turns")}{observed("Passed", "passed")}{observed("Skill used", "skill_used")}<div><dt>Exit code (execution status)</dt><dd>{typeof run.exit_code === "number" ? String(run.exit_code) : unavailable}</dd></div></dl>;
}

function Comparison({ selected }: { selected: Run[] }) {
  const verdict = comparisonEligibility(selected);
  if (verdict.reason || !verdict.baseline || !verdict.with) return <section className="surface performance-panel"><h2>Comparison</h2><p>Select one independently valid baseline and one with-configuration record with matching recorded identity. {verdict.reason ?? ""}</p></section>;
  const baseline = verdict.baseline as Run;
  const withValue = verdict.with as Run;
  const metric = (label: string, field: "duration_ms" | "cost_usd", unit: string) => {
    const baselineValue = measurementNumber(baseline, field);
    const withValueMetric = measurementNumber(withValue, field);
    const delta = descriptiveDelta(baselineValue, withValueMetric);
    return { label, field, unit, baselineValue, withValueMetric, delta };
  };
  const values = [metric("Duration", "duration_ms", "ms"), metric("Cost", "cost_usd", "USD")];
  return <section className="surface performance-panel"><h2>Comparison</h2><p>n=1 each. Differences mean with minus baseline; no causality, savings, significance, or installed-state claim.</p><table><caption>Comparable recorded measurements</caption><thead><tr><th>Metric</th><th>Baseline</th><th>With configuration</th><th>With minus baseline</th></tr></thead><tbody>{values.map((item) => <tr key={item.field}><th scope="row">{item.label}</th><td>{shown(item.baselineValue, ` ${item.unit}`)}</td><td>{shown(item.withValueMetric, ` ${item.unit}`)}</td><td>{item.delta.delta === null ? unavailable : `${shown(item.delta.delta, ` ${item.unit}`)}${item.delta.percent === null ? " · % unavailable" : ` (${shown(item.delta.percent, "%")})`}`}</td></tr>)}</tbody></table><div className="performance-charts">{values.map((item) => item.baselineValue === null || item.withValueMetric === null ? null : <div className="performance-chart" key={item.field}><GroupedBarChart data={[{ group: "Baseline", key: item.label, value: item.baselineValue }, { group: "With configuration", key: item.label, value: item.withValueMetric }]} options={{ title: item.label, height: "260px", axes: { left: { mapsTo: "value", title: item.unit, includeZero: true }, bottom: { mapsTo: "key", scaleType: ScaleTypes.LABELS } }, toolbar: { enabled: false }, animations: false }} /></div>)}</div></section>;
}

function RunDetail({ session, id, back }: { session: Session; id: string; back: () => void }) {
  const [eventPage, setEventPage] = useState(1);
  const [toolPage, setToolPage] = useState(1);
  const run = useLoad(`run:${id}`, (signal) => runById(session, id, signal));
  const evidence = useLoad(`evidence:${id}`, (signal) => evidenceForRun(session, id, signal));
  const events = useLoad(`events:${id}:${eventPage}`, (signal) => eventsForRun(session, id, eventPage, signal));
  const tools = useLoad(`tools:${id}:${toolPage}`, (signal) => toolCallsForRun(session, id, toolPage, signal));
  const [files, setFiles] = useState<Record<string, string>>({});
  if (run.state !== "populated" || !run.data) return <Block><StateNotice state={run.state === "populated" ? "empty" : run.state} subject="run detail" /></Block>;
  const open = async (artifact: { id: string; blob?: string }) => { const token = await protectedFileToken(session); if (token.kind === "ok") { const link = protectedArtifactUrl(artifact, token.token); if (link) setFiles((old) => ({ ...old, [artifact.id]: link })); } };
  const detail = { checks: run.data.checks, grades: run.data.grades, provenance: run.data.provenance, measurement: run.data.measurement, source_time: run.data.ts ?? unavailable, ingestion_time: run.data.created ?? unavailable, revision: run.data.cli_version ?? unavailable };
  return <Block><PageCrumbs current="Performance / run" /><Button kind="ghost" onClick={back}>Return to runs</Button><h1>Run {run.data.id}</h1><RunMetrics run={run.data} /><section className="surface performance-panel"><pre>{JSON.stringify(detail, null, 2)}</pre><p>Source time is not interpreted when timezone is unknown; ingestion time is separate.</p></section><section className="surface performance-panel"><h2>Evidence</h2>{evidence.state === "populated" && evidence.data ? <><p>Completeness: {evidence.data.completeness}.</p>{evidence.data.artifacts.map((artifact) => <p key={artifact.id}>{artifact.id} · {artifact.sha256} · {artifactByteSize(artifact) === null ? "size unavailable" : `${artifactByteSize(artifact)} bytes`} {files[artifact.id] ? <a href={files[artifact.id]}>Open evidence</a> : <Button kind="ghost" size="sm" onClick={() => open(artifact)}>Open evidence</Button>}</p>)}</> : <StateNotice state={evidence.state === "populated" ? "empty" : evidence.state} subject="evidence" />}</section><PagedRecords title="Current events" result={events} page={eventPage} setPage={setEventPage} /><PagedRecords title="Current tools" result={tools} page={toolPage} setPage={setToolPage} /></Block>;
}

function PagedRecords({ title, result, page, setPage }: { title: string; result: ReturnType<typeof useLoad<any>>; page: number; setPage: (page: number) => void }) {
  return <section className="surface performance-panel"><h2>{title}</h2>{result.state === "populated" && result.data ? <><pre>{JSON.stringify(result.data.items, null, 2)}</pre><Pager page={page} total={result.data.totalItems} onChange={setPage} /></> : <StateNotice state={result.state === "populated" ? "empty" : result.state} subject={title.toLowerCase()} />}</section>;
}

function CampaignDetail({ session, id, back }: { session: Session; id: string; back: () => void }) {
  const [responsePage, setResponsePage] = useState(1);
  const [assessmentPage, setAssessmentPage] = useState(1);
  const campaign = useLoad(`campaign:${id}`, (signal) => campaignById(session, id, signal));
  const responses = useLoad(`responses:${id}:${responsePage}`, (signal) => responsesForCampaign(session, id, responsePage, signal));
  const assessments = useLoad(`assessments:${id}:${assessmentPage}`, (signal) => assessmentsForCampaign(session, id, assessmentPage, signal));
  if (campaign.state !== "populated" || !campaign.data) return <Block><StateNotice state={campaign.state === "populated" ? "empty" : campaign.state} subject="campaign" /></Block>;
  return <Block><Button kind="ghost" onClick={back}>Return to campaigns</Button><h1>Campaign {campaign.data.id}</h1><p>Conformance is not independent output quality; associations are current and can change.</p><PagedRecords title="Responses" result={responses} page={responsePage} setPage={setResponsePage} /><PagedRecords title="Current assessments" result={assessments} page={assessmentPage} setPage={setAssessmentPage} /></Block>;
}

function CampaignList({ session }: { session: Session }) {
  const [query, setQuery] = useState("");
  const [campaignPage, setCampaignPage] = useState(1);
  const result = useLoad(`campaigns:${query}:${campaignPage}`, (signal) => campaigns(session, query, campaignPage, signal));
  return <section className="surface performance-panel"><h2>Campaigns</h2><TextInput id="campaign-search" labelText="Search campaigns" value={query} onChange={(event) => { setCampaignPage(1); setQuery(event.currentTarget.value); }} />{result.state === "populated" && result.data ? <><ul>{result.data.items.map((campaign) => <li key={campaign.id}><a href={href("campaign", campaign.id)}>{campaign.id}</a> · {campaign.slug}</li>)}</ul><Pager page={campaignPage} total={result.data.totalItems} onChange={setCampaignPage} /></> : <StateNotice state={result.state === "populated" ? "empty" : result.state} subject="campaigns" />}</section>;
}

export function Performance({ session, onExpired, hash = location.hash }: { session: Session; onExpired: () => void; hash?: string }) {
  const [query, setQuery] = useState(""); const [config, setConfig] = useState<"all" | "baseline" | "with">("all"); const [page, setPage] = useState(1); const [perPage, setPerPage] = useState<25 | 50>(25); const [sort, setSort] = useState<"id" | "duration_ms" | "cost_usd">("id"); const [selected, setSelected] = useState<Run[]>([]);
  const runId = recordScope(hash, "run"); const campaignId = recordScope(hash, "campaign");
  const result = useLoad(`runs:${query}:${config}:${page}:${perPage}:${sort}`, (signal) => runs(session, { query, config, page, perPage, sort: "+id", ...(sort === "id" ? {} : { metricSort: { metric: sort, direction: "asc" } } as never), signal }));
  useEffect(() => { const unsubscribe = session.subscribe(() => { setSelected([]); onExpired(); }); return () => { unsubscribe(); }; }, [session, onExpired]);
  useEffect(() => { session.setSelection("performance", selected.map((run) => run.id)); }, [session, selected]);
  const rows = useMemo(() => result.data?.items ?? [], [result.data]);
  if (runId) return <RunDetail session={session} id={runId} back={() => { location.hash = "#performance"; }} />;
  if (campaignId) return <CampaignDetail session={session} id={campaignId} back={() => { location.hash = "#performance"; }} />;
  return <Block><PageCrumbs current="Performance" /><h1>Performance</h1><section className="surface performance-panel"><div className="performance-controls"><TextInput id="run-search" labelText="Search runs" value={query} onChange={(event) => { setPage(1); setQuery(event.currentTarget.value); }} /><Select id="configuration" labelText="Configuration" value={config} onChange={(event) => { setPage(1); setConfig(event.currentTarget.value as typeof config); }}><SelectItem value="all" text="All configurations" /><SelectItem value="baseline" text="Baseline" /><SelectItem value="with" text="With configuration" /></Select><Select id="sort" labelText="Sort" value={sort} onChange={(event) => { setPage(1); setSort(event.currentTarget.value as typeof sort); }}><SelectItem value="id" text="Record ID" /><SelectItem value="duration_ms" text="Duration" /><SelectItem value="cost_usd" text="Cost" /></Select></div>{selected.length > 0 && <aside className="selection-tray"><strong>Selected ({selected.length}/2)</strong>{selected.map((run) => <Button key={run.id} kind="ghost" size="sm" onClick={() => setSelected((old) => nextSelection(old, run))}>{run.id}{rows.some((row) => row.id === run.id) ? "" : " (off page)"} ×</Button>)}</aside>}{result.state !== "populated" ? <StateNotice state={result.state} subject="runs" /> : result.data && !result.data.items.length ? <StateNotice state="empty" subject="runs" /> : <><div className="table-scroll" role="region" aria-label="Recorded runs" tabIndex={0}><table><caption>Recorded performance runs</caption><thead><tr><th>Select</th><th>Run / harness campaign</th><th>Candidate / case</th><th>Outcome</th><th>Duration</th><th>Cost</th><th>Evidence</th></tr></thead><tbody>{rows.map((run) => <tr key={run.id}><td><Checkbox id={`select-${run.id}`} labelText="" hideLabel checked={selected.some((item) => item.id === run.id)} disabled={!selected.some((item) => item.id === run.id) && selected.length === 2} onChange={() => setSelected((old) => nextSelection(old, run))} /></td><th scope="row">{run.id}<br />{run.campaign ?? unavailable}</th><td>{run.candidate} / {run.case}</td><td>{measurementBoolean(run, "passed") === null ? unavailable : String(measurementBoolean(run, "passed"))}</td><td>{shown(measurementNumber(run, "duration_ms"), " ms")}</td><td>{shown(measurementNumber(run, "cost_usd"), " USD")}</td><td><a href={href("run", run.id)}>Inspect</a></td></tr>)}</tbody></table></div><Pagination page={page} pageSize={perPage} pageSizes={[25, 50]} totalItems={result.data!.totalItems} onChange={(next) => { setPage(next.page); setPerPage(next.pageSize as 25 | 50); }} /></>}</section><Comparison selected={selected} /><CampaignList session={session} /></Block>;
}
