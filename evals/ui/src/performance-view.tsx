// The Performance area: the runs list with its selection tray, the comparison
// of an eligible baseline and with-configuration pair, run detail with its
// evidence opened through a file token, and campaign search and detail.
import { ScaleTypes, type BarChartOptions } from "@carbon/charts";
import { GroupedBarChart } from "@carbon/charts-react";
import { Button, Checkbox, Link, Select, SelectItem } from "@carbon/react";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import {
  assessmentsQuery,
  DataRegion,
  expandedName,
  hashHref,
  isAbort,
  jsonText,
  orUnavailable,
  PagedList,
  Pager,
  pageCount,
  pageSlice,
  RecordRegion,
  searchFilter,
  SearchForm,
  statusOf,
  useClient,
  useLoad,
  useSearch,
  type AssessmentRecord,
  type ListQuery,
  type ToolboxClient,
} from "./api.tsx";

const UNAVAILABLE = "Unavailable";

// ---------------------------------------------------------------- measurement display

export type ValueKind = "number" | "boolean" | "integer";

export interface Metric {
  field: string;
  label: string;
  unit: string;
  kind: ValueKind;
}

const metric = (field: string, label: string, unit = "", kind: ValueKind = "number"): Metric => ({ field, label, unit, kind });

export const DURATION = metric("duration_ms", "Duration", "ms");
export const COST = metric("cost_usd", "Cost", "USD");
export const PASSED = metric("passed", "Passed", "", "boolean");

/** The run metrics in display order. */
export const RUN_METRICS: readonly Metric[] = [
  DURATION,
  COST,
  metric("input_tokens", "Input tokens", "tokens"),
  metric("output_tokens", "Output tokens", "tokens"),
  metric("cache_creation_tokens", "Cache creation tokens", "tokens"),
  metric("cache_read_tokens", "Cache read tokens", "tokens"),
  metric("num_turns", "Turns", "turns"),
  PASSED,
  metric("skill_used", "Skill used", "", "boolean"),
  metric("exit_code", "Exit code", "", "integer"),
];

/** The eval-response metrics. */
export const RESPONSE_METRICS: readonly Metric[] = [metric("tokens", "Tokens", "tokens"), metric("duration_ms", "Duration", "ms")];

export type Measured = { available: true; value: number | boolean } | { available: false };

const NOT_MEASURED: Measured = { available: false };

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * A record's metric when its `measurement` is version 1, marks the field
 * available, and the value is a finite non-negative number (a boolean for
 * booleans, an integer for exit_code). A legacy record without the envelope
 * has no available metric.
 */
export function measured(record: Record<string, unknown>, { field, kind }: Pick<Metric, "field" | "kind">): Measured {
  const envelope = record.measurement;
  if (!isObject(envelope) || envelope.version !== 1 || !isObject(envelope.available) || envelope.available[field] !== true) return NOT_MEASURED;
  const value = record[field];
  if (kind === "boolean") return typeof value === "boolean" ? { available: true, value } : NOT_MEASURED;
  if (typeof value !== "number" || !Number.isFinite(value)) return NOT_MEASURED;
  if (kind === "integer") return Number.isInteger(value) ? { available: true, value } : NOT_MEASURED;
  return value >= 0 ? { available: true, value } : NOT_MEASURED;
}

/** 0 < |v| < 0.001 in exponential notation with 2 fraction digits; otherwise en-US with at most 3 fraction digits. */
export function formatNumber(value: number): string {
  const size = Math.abs(value);
  return size > 0 && size < 0.001 ? value.toExponential(2) : value.toLocaleString("en-US", { maximumFractionDigits: 3 });
}

/** A number followed by its unit, if it has one. */
export function withUnit(value: number, unit: string): string {
  return unit ? `${formatNumber(value)} ${unit}` : formatNumber(value);
}

/** A measured value as shown: the number with its unit, "Yes"/"No" for a boolean, or "Unavailable". */
export function formatMeasured(value: Measured, unit = ""): string {
  if (!value.available) return UNAVAILABLE;
  if (typeof value.value === "boolean") return value.value ? "Yes" : "No";
  return withUnit(value.value, unit);
}

export function showMetric(record: Record<string, unknown>, which: Metric): string {
  return formatMeasured(measured(record, which), which.unit);
}

function envelopePart(record: Record<string, unknown>, part: string): Record<string, unknown> | undefined {
  const envelope = record.measurement;
  if (!isObject(envelope)) return undefined;
  const value = envelope[part];
  return isObject(value) ? value : undefined;
}

/** `measurement.execution.validity`, or undefined when the record has none. */
export function executionValidity(record: Record<string, unknown>): string | undefined {
  const validity = envelopePart(record, "execution")?.validity;
  return typeof validity === "string" && validity !== "" ? validity : undefined;
}

/** `measurement.source_identity.revision.value` when the revision is marked available. */
export function sourceRevision(record: Record<string, unknown>): string {
  const revision = envelopePart(record, "source_identity")?.revision;
  if (!isObject(revision) || revision.available !== true) return UNAVAILABLE;
  const value = revision.value;
  return typeof value === "string" || typeof value === "number" ? String(value) : UNAVAILABLE;
}

/** A JSON value summarised as its keys, or "<n> entries" for a list. */
export function shapeSummary(value: unknown): string {
  if (Array.isArray(value)) return `${value.length} entries`;
  if (isObject(value)) {
    const keys = Object.keys(value);
    return keys.length ? keys.join(", ") : "0 entries";
  }
  return value === null || value === undefined ? UNAVAILABLE : JSON.stringify(value);
}

// ---------------------------------------------------------------- runs

export interface RunRow {
  id: string;
  campaign: string;
  candidate: string;
  case: string;
  harness: string;
  model: string;
  config: string;
  ts: string;
  created: string;
  cli_version: string;
  [field: string]: unknown;
}

export const RUN_LIST_FIELDS = [
  "id",
  "campaign",
  "candidate",
  "case",
  "harness",
  "model",
  "config",
  "trial",
  "grades",
  "passed",
  "duration_ms",
  "cost_usd",
  "input_tokens",
  "output_tokens",
  "cache_creation_tokens",
  "cache_read_tokens",
  "num_turns",
  "measurement",
  "ts",
  "created",
  "cli_version",
] as const;

const RUN_DETAIL_FIELDS = [...RUN_LIST_FIELDS, "kind", "skill_used", "exit_code", "checks", "provenance"];

export const RUN_SEARCH_FIELDS = ["id", "campaign", "candidate", "case", "model", "harness"] as const;

export type ConfigFilter = "all" | "baseline" | "with";
export type RunSort = "id" | "duration" | "cost";
export const PAGE_SIZES = [25, 50] as const;
/** Page size of the reads that gather every page for a client-side sort or for evidence. */
export const GATHER_PAGE_SIZE = 200;

/** The runs filter: the substring search and the configuration, each an escaped parameter. */
export function runFilter(client: Pick<ToolboxClient, "filter">, query: string, config: ConfigFilter): string | undefined {
  const search = searchFilter(client, RUN_SEARCH_FIELDS, query);
  const parts = [search ? `(${search})` : "", config === "all" ? "" : client.filter("config = {:config}", { config })].filter(Boolean);
  return parts.length ? parts.join(" && ") : undefined;
}

/** Code-point order of record ids. */
export function compareIds(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

const SORT_METRICS: Record<Exclude<RunSort, "id">, Metric> = { duration: DURATION, cost: COST };

/** Runs in server order for "id", else ascending by the measured duration or cost, unavailable last, ties by id. */
export function sortRuns<T extends RunRow>(runs: readonly T[], sort: RunSort): T[] {
  if (sort === "id") return [...runs];
  const by = SORT_METRICS[sort];
  const key = (run: T) => {
    const value = measured(run, by);
    return value.available ? (value.value as number) : null;
  };
  return [...runs].sort((a, b) => {
    const [x, y] = [key(a), key(b)];
    if (x !== null && y !== null && x !== y) return x - y;
    if ((x === null) !== (y === null)) return x === null ? 1 : -1;
    return compareIds(a.id, b.id);
  });
}

/** Every page of a list read. */
export async function gatherPages<T>(client: ToolboxClient, query: Omit<ListQuery, "page" | "perPage">, signal: AbortSignal): Promise<T[]> {
  const items: T[] = [];
  for (let page = 1; ; page += 1) {
    const result = await client.list<T>({ ...query, page, perPage: GATHER_PAGE_SIZE }, signal);
    items.push(...result.items);
    if (page >= result.totalPages) return items;
  }
}

export interface RunsView {
  query: string;
  config: ConfigFilter;
  sort: RunSort;
  page: number;
  perPage: number;
}

export interface RunsData {
  rows: RunRow[];
  total: number;
  /** True when `rows` is already the current page; false when it holds every page in client-side order. */
  serverPaged: boolean;
}

/** One page in server order, or every page sorted client-side by duration or cost. */
export async function loadRuns(client: ToolboxClient, view: RunsView, signal: AbortSignal): Promise<RunsData> {
  const query = { collection: "runs", fields: RUN_LIST_FIELDS, filter: runFilter(client, view.query, view.config) };
  if (view.sort === "id") {
    const result = await client.list<RunRow>({ ...query, page: view.page, perPage: view.perPage }, signal);
    return { rows: result.items, total: result.totalItems, serverPaged: true };
  }
  const rows = sortRuns(await gatherPages<RunRow>(client, query, signal), view.sort);
  return { rows, total: rows.length, serverPaged: false };
}

export function visibleRuns(data: RunsData, view: RunsView): RunRow[] {
  return data.serverPaged ? data.rows : pageSlice(data.rows, view.page, view.perPage);
}

export function identityText(run: RunRow): string {
  return [
    orUnavailable(run.harness, "Harness"),
    orUnavailable(run.model, "Model"),
    orUnavailable(run.candidate, "Candidate"),
    orUnavailable(run.case, "Case"),
  ].join(" · ");
}

export function gradesText(run: Record<string, unknown>): string {
  return run.grades === null || run.grades === undefined ? UNAVAILABLE : JSON.stringify(run.grades);
}

// ---------------------------------------------------------------- selection

export const MAX_SELECTION = 2;

/** Adds a run to the selection, or removes it when present; a third run is refused. */
export function toggleSelection<T extends { id: string }>(selection: readonly T[], run: T): T[] {
  if (selection.some((entry) => entry.id === run.id)) return selection.filter((entry) => entry.id !== run.id);
  return selection.length >= MAX_SELECTION ? [...selection] : [...selection, run];
}

export function trayLabel(run: RunRow, onPage: boolean): string {
  return `${run.id} · ${orUnavailable(run.config, "Configuration")} · ${orUnavailable(run.candidate, "Candidate")}${onPage ? "" : " (off page)"}`;
}

// ---------------------------------------------------------------- comparison

export const IDENTITY_FIELDS = ["campaign", "candidate", "case", "harness", "model"] as const;
export const INELIGIBLE_TEXT = "Select one independently valid baseline and one with-configuration record with matching recorded identity.";
export const CAVEAT_TEXT = "n=1 each. Differences mean with minus baseline; no causality, savings, significance, or installed-state claim.";

export type Eligibility<T> = { eligible: true; baseline: T; with: T } | { eligible: false; reason: string };

/** Whether a selection can be compared, else its first failing reason. */
export function comparisonEligibility<T extends RunRow>(selection: readonly T[]): Eligibility<T> {
  if (selection.length !== 2) return { eligible: false, reason: "select-exactly-two" };
  const [a, b] = selection as [T, T];
  if (a.id === b.id) return { eligible: false, reason: "duplicate-record" };
  for (const field of IDENTITY_FIELDS) {
    const [x, y] = [a[field], b[field]];
    if (typeof x !== "string" || x === "" || typeof y !== "string" || y === "") return { eligible: false, reason: `missing-${field}` };
    if (x !== y) return { eligible: false, reason: `${field}-mismatch` };
  }
  const baseline = [a, b].find((run) => run.config === "baseline");
  const withRun = [a, b].find((run) => run.config === "with");
  if (!baseline || !withRun) return { eligible: false, reason: "configuration-mismatch" };
  if (executionValidity(a) !== "valid" || executionValidity(b) !== "valid") return { eligible: false, reason: "execution-invalid" };
  return { eligible: true, baseline, with: withRun };
}

/** with − baseline as a percentage of baseline; null unless baseline > 0. */
export function percentOfBaseline(difference: number, baseline: number): number | null {
  return baseline > 0 ? (difference / baseline) * 100 : null;
}

export interface DifferenceRow {
  label: string;
  baseline: string;
  with: string;
  difference: string;
  percent: string;
}

/** One row of the differences table: both values, with − baseline and its percentage of baseline. */
export function differenceRow(which: Metric, baseline: RunRow, withRun: RunRow): DifferenceRow {
  const [b, w] = [measured(baseline, which), measured(withRun, which)];
  const row = { label: `${which.label} (${which.unit})`, baseline: formatMeasured(b, which.unit), with: formatMeasured(w, which.unit) };
  if (!b.available || !w.available) return { ...row, difference: UNAVAILABLE, percent: UNAVAILABLE };
  const difference = (w.value as number) - (b.value as number);
  const percent = percentOfBaseline(difference, b.value as number);
  return { ...row, difference: withUnit(difference, which.unit), percent: percent === null ? UNAVAILABLE : `${formatNumber(percent)}%` };
}

export const COMPARISON_METRICS: readonly Metric[] = [DURATION, COST];
export const CHART_METRICS: readonly Metric[] = RUN_METRICS.filter((entry) => entry.kind === "number");

export interface ChartDatum {
  group: string;
  key: string;
  value: number;
}

/** The grouped bar data of one metric, or null unless both values are available. */
export function chartData(which: Metric, baseline: RunRow, withRun: RunRow): ChartDatum[] | null {
  const [b, w] = [measured(baseline, which), measured(withRun, which)];
  if (!b.available || !w.available) return null;
  return [
    { group: "Baseline", key: which.label, value: b.value as number },
    { group: "With", key: which.label, value: w.value as number },
  ];
}

function chartOptions(which: Metric): BarChartOptions {
  return {
    title: `${which.label} (${which.unit})`,
    axes: { left: { mapsTo: "value", title: which.unit }, bottom: { mapsTo: "key", scaleType: ScaleTypes.LABELS } },
    height: "240px",
  };
}

export function Comparison({ selection }: { selection: readonly RunRow[] }) {
  const result = comparisonEligibility(selection);
  return (
    <section aria-labelledby="performance-comparison">
      <h2 id="performance-comparison">Comparison</h2>
      {result.eligible ? <EligibleComparison baseline={result.baseline} withRun={result.with} /> : <IneligibleComparison reason={result.reason} />}
    </section>
  );
}

function IneligibleComparison({ reason }: { reason: string }) {
  return (
    <div role="status">
      <p>{INELIGIBLE_TEXT}</p>
      <p>{`Reason: ${reason}`}</p>
    </div>
  );
}

function Table({ caption, head, rows }: { caption: string; head: readonly string[]; rows: readonly (readonly string[])[] }) {
  return (
    <table className="cds--data-table cds--data-table--sm toolbox-table">
      <caption>{caption}</caption>
      <thead>
        <tr>
          {head.map((cell) => (
            <th key={cell} scope="col">
              {cell}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row[0]}>
            {row.map((cell, index) => (index === 0 ? <th key={index} scope="row">{cell}</th> : <td key={index}>{cell}</td>))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function sourceRow(label: string, run: RunRow): string[] {
  return [`${label} ${run.id}`, orUnavailable(run.ts, "Source time"), orUnavailable(run.created, "Ingestion time"), sourceRevision(run), orUnavailable(run.cli_version, "CLI version")];
}

function EligibleComparison({ baseline, withRun }: { baseline: RunRow; withRun: RunRow }) {
  const charts = CHART_METRICS.map((which) => ({ which, data: chartData(which, baseline, withRun) }));
  return (
    <>
      <p>{CAVEAT_TEXT}</p>
      <Table
        caption="Differences"
        head={["Metric", "Baseline", "With", "With − baseline", "Percentage of baseline"]}
        rows={COMPARISON_METRICS.map((which) => {
          const row = differenceRow(which, baseline, withRun);
          return [row.label, row.baseline, row.with, row.difference, row.percent];
        })}
      />
      <Table
        caption="Sources"
        head={["Record", "Source time (ts)", "Ingestion time (created)", "Source revision", "CLI version"]}
        rows={[sourceRow("Baseline", baseline), sourceRow("With", withRun)]}
      />
      <div className="toolbox-charts">
        {charts.map(({ which, data }) =>
          data ? (
            <figure key={which.field} className="toolbox-chart" aria-label={`${which.label} chart`}>
              <GroupedBarChart data={data} options={chartOptions(which)} />
            </figure>
          ) : null,
        )}
      </div>
    </>
  );
}

// ---------------------------------------------------------------- runs list

function SelectField<V extends string>({ label, value, options, onChange }: { label: string; value: V; options: readonly [V, string][]; onChange: (value: V) => void }) {
  const id = useId();
  return (
    <Select id={id} size="sm" inline labelText={label} value={value} onChange={(event) => onChange(event.target.value as V)}>
      {options.map(([option, text]) => (
        <SelectItem key={option} value={option} text={text} />
      ))}
    </Select>
  );
}

const CONFIG_OPTIONS: readonly [ConfigFilter, string][] = [
  ["all", "All"],
  ["baseline", "Baseline"],
  ["with", "With"],
];

const SORT_OPTIONS: readonly [RunSort, string][] = [
  ["id", "Record id"],
  ["duration", "Duration (ascending)"],
  ["cost", "Cost (ascending)"],
];

export const RUN_COLUMNS = ["Select", "Record", "Configuration", "Identity", "Execution validity", "Grades", "Outcome (passed)", "Duration", "Cost", "Inspect"] as const;

export function RunTable({ runs, selection, onToggle }: { runs: readonly RunRow[]; selection: readonly RunRow[]; onToggle: (run: RunRow) => void }) {
  const full = selection.length >= MAX_SELECTION;
  return (
    <table className="cds--data-table cds--data-table--sm toolbox-table">
      <caption>Runs</caption>
      <thead>
        <tr>
          {RUN_COLUMNS.map((column) => (
            <th key={column} scope="col">
              {column}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {runs.map((run) => {
          const selected = selection.some((entry) => entry.id === run.id);
          return (
            <tr key={run.id}>
              <td>
                <Checkbox id={`select-run-${run.id}`} labelText={`Select ${run.id}`} hideLabel checked={selected} disabled={full && !selected} onChange={() => onToggle(run)} />
              </td>
              <td>
                <div>{run.id}</div>
                <div>{run.campaign ? `Campaign: ${run.campaign}` : "Campaign unavailable"}</div>
              </td>
              <td>{orUnavailable(run.config, "Configuration")}</td>
              <td>{identityText(run)}</td>
              <td>{executionValidity(run) ?? UNAVAILABLE}</td>
              <td>
                <code className="toolbox-code">{gradesText(run)}</code>
              </td>
              <td>{showMetric(run, PASSED)}</td>
              <td>{showMetric(run, DURATION)}</td>
              <td>{showMetric(run, COST)}</td>
              <td>
                <Link href={hashHref("performance", { run: run.id })} data-inspect={run.id}>
                  Inspect
                </Link>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export function SelectionTray({ selection, onPage, onRemove }: { selection: readonly RunRow[]; onPage: ReadonlySet<string>; onRemove: (run: RunRow) => void }) {
  return (
    <section aria-labelledby="performance-selection">
      <h2 id="performance-selection">{`Selected (${selection.length}/${MAX_SELECTION})`}</h2>
      {selection.length === 0 ? (
        <p>No runs selected.</p>
      ) : (
        <ul className="toolbox-list">
          {selection.map((run) => {
            const label = trayLabel(run, onPage.has(run.id));
            return (
              <li key={run.id}>
                <Button kind="ghost" size="sm" aria-label={`Remove ${label}`} onClick={() => onRemove(run)}>
                  {label}
                </Button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

export const FIRST_RUNS_VIEW: RunsView = { query: "", config: "all", sort: "id", page: 1, perPage: PAGE_SIZES[0] };

function RunsList({ selection, onToggle }: { selection: readonly RunRow[]; onToggle: (run: RunRow) => void }) {
  const [view, setView] = useState<RunsView>(FIRST_RUNS_VIEW);
  const restart = (change: Partial<RunsView>) => setView((current) => ({ ...current, ...change, page: 1 }));
  const serverPaged = view.sort === "id";
  const state = useLoad((client, signal) => loadRuns(client, view, signal), [view.query, view.config, view.sort, serverPaged ? view.page : 0, serverPaged ? view.perPage : 0]);
  const visible = state.status === "ready" ? visibleRuns(state.data, view) : [];
  return (
    <>
      <section aria-labelledby="performance-runs">
        <h2 id="performance-runs" tabIndex={-1}>
          Runs
        </h2>
        <SearchForm label="Search runs" onSearch={(query) => restart({ query })} />
        <div className="toolbox-controls">
          <SelectField label="Configuration" value={view.config} options={CONFIG_OPTIONS} onChange={(config) => restart({ config })} />
          <SelectField label="Sort by" value={view.sort} options={SORT_OPTIONS} onChange={(sort) => restart({ sort })} />
        </div>
        <DataRegion subject="runs" state={state} isEmpty={(data) => data.total === 0}>
          {(data) => (
            <>
              <RunTable runs={visible} selection={selection} onToggle={onToggle} />
              <Pager
                label="Runs"
                page={view.page}
                totalPages={pageCount(data.total, view.perPage)}
                onPage={(page) => setView((current) => ({ ...current, page }))}
                pageSize={view.perPage}
                pageSizes={PAGE_SIZES}
                onPageSize={(perPage) => restart({ perPage })}
              />
            </>
          )}
        </DataRegion>
      </section>
      <SelectionTray selection={selection} onPage={new Set(visible.map((run) => run.id))} onRemove={onToggle} />
    </>
  );
}

// ---------------------------------------------------------------- campaigns

export interface EvalRunRecord {
  id: string;
  slug: string;
  kind: string;
  method: string;
  criteria_text: string;
  status: string;
  notes: string;
}

export const EVAL_RUN_FIELDS = ["id", "slug", "kind", "method", "criteria_text", "status", "notes"] as const;
export const CAMPAIGN_SEARCH_FIELDS = ["id", "slug", "method", "criteria_text", "notes"] as const;

export function campaignLabel(run: EvalRunRecord): string {
  return `${run.slug} · ${orUnavailable(run.kind, "Kind")} · ${orUnavailable(run.status, "Status")}`;
}

function CampaignSearch() {
  const { query, round, search } = useSearch();
  return (
    <section aria-labelledby="performance-campaigns">
      <h2 id="performance-campaigns" tabIndex={-1}>
        Campaigns
      </h2>
      <SearchForm label="Search campaigns" onSearch={search} />
      <PagedList<EvalRunRecord>
        key={round}
        subject="campaigns"
        label="Campaigns"
        query={(client) => ({ collection: "eval_runs", fields: EVAL_RUN_FIELDS, sort: ["slug"], filter: searchFilter(client, CAMPAIGN_SEARCH_FIELDS, query) })}
        deps={[query]}
        item={(run) => (
          <Link href={hashHref("performance", { campaign: run.id })} data-campaign={run.id}>
            {campaignLabel(run)}
          </Link>
        )}
      />
    </section>
  );
}

export const CONFORMANCE_TEXT = "Conformance is not independent output quality; associations are current and can change.";

interface ResponseRecord {
  id: string;
  role: string;
  prompt: string;
  response_text: string;
  response_json: unknown;
  [field: string]: unknown;
}

const RESPONSE_FIELDS = ["id", "role", "agent_type", "model", "prompt", "response_text", "response_json", "tokens", "duration_ms", "measurement"];

function Disclosure({ summary, children }: { summary: string; children: ReactNode }) {
  return (
    <details className="toolbox-disclosure">
      <summary>{summary}</summary>
      {children}
    </details>
  );
}

function TextBlock({ text, missing }: { text: unknown; missing: string }) {
  return typeof text === "string" && text !== "" ? <pre className="toolbox-text">{text}</pre> : <p>{missing}</p>;
}

function JsonBlock({ value }: { value: unknown }) {
  return <pre className="toolbox-text">{jsonText(value)}</pre>;
}

function Facts({ facts }: { facts: readonly [string, ReactNode][] }) {
  return (
    <dl className="toolbox-facts">
      {facts.map(([term, value]) => (
        <div key={term}>
          <dt>{term}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function ResponseItem({ response }: { response: ResponseRecord }) {
  return (
    <article>
      <h4>{orUnavailable(response.role, "Role")}</h4>
      <Facts facts={RESPONSE_METRICS.map((which): [string, string] => [which.label, showMetric(response, which)])} />
      <Disclosure summary="Prompt">
        <TextBlock text={response.prompt} missing="Prompt unavailable" />
      </Disclosure>
      <Disclosure summary="Response">
        <TextBlock text={response.response_text} missing="Response unavailable" />
      </Disclosure>
      <Disclosure summary="Raw response JSON">
        <JsonBlock value={response.response_json} />
      </Disclosure>
    </article>
  );
}

export function CampaignAssessment({ assessment }: { assessment: AssessmentRecord }) {
  const name = expandedName(assessment, "extender");
  return (
    <p>
      {assessment.extender ? (
        <>
          <Link href={hashHref("documentation", { extender: assessment.extender })}>{name ?? "Extender name unavailable"}</Link>
          {" ("}
          <Link href={hashHref("evaluations", { extender: assessment.extender })}>evaluations</Link>
          {")"}
        </>
      ) : (
        "Extender unavailable"
      )}
      {` · ${orUnavailable(expandedName(assessment, "framework"), "Framework")} · ${orUnavailable(expandedName(assessment, "element"), "Element")} · ${orUnavailable(assessment.verdict, "Verdict")}; ${orUnavailable(assessment.evidence, "Evidence")}`}
    </p>
  );
}

export function CampaignFacts({ run }: { run: EvalRunRecord }) {
  return (
    <>
      <h2>{`Campaign ${orUnavailable(run.slug, "Slug")}`}</h2>
      <Facts
        facts={[
          ["Slug", orUnavailable(run.slug, "Slug")],
          ["Kind", orUnavailable(run.kind, "Kind")],
          ["Method", <TextBlock text={run.method} missing="Method unavailable" />],
          ["Criteria", <TextBlock text={run.criteria_text} missing="Criteria unavailable" />],
          ["Status", orUnavailable(run.status, "Status")],
          ["Notes", <TextBlock text={run.notes} missing="Notes unavailable" />],
        ]}
      />
    </>
  );
}

function CampaignDetail({ id, onReturn }: { id: string; onReturn: () => void }) {
  return (
    <article className="toolbox-document">
      <Button kind="secondary" size="md" onClick={onReturn}>
        Return to campaigns
      </Button>
      <RecordRegion<EvalRunRecord> key={id} subject="campaign" collection="eval_runs" id={id} fields={EVAL_RUN_FIELDS}>
        {(run) => <CampaignFacts run={run} />}
      </RecordRegion>
      <p>{CONFORMANCE_TEXT}</p>
      <h3>Responses</h3>
      <PagedList<ResponseRecord>
        key={`responses-${id}`}
        subject="responses"
        label="Responses"
        query={(client) => ({ collection: "eval_responses", fields: RESPONSE_FIELDS, sort: ["role"], filter: client.filter("run = {:run}", { run: id }) })}
        deps={[id]}
        item={(response) => <ResponseItem response={response} />}
      />
      <h3>Assessments</h3>
      <PagedList<AssessmentRecord>
        key={`assessments-${id}`}
        subject="campaign assessments"
        label="Campaign assessments"
        query={(client) => assessmentsQuery(client.filter("eval_run = {:run}", { run: id }))}
        deps={[id]}
        item={(assessment) => <CampaignAssessment assessment={assessment} />}
      />
    </article>
  );
}

// ---------------------------------------------------------------- evidence

export interface ArtifactRecord {
  id: string;
  sha256: string;
  blob?: string;
  byte_size?: unknown;
  kind?: string;
  mime?: string;
  run?: string;
}

export const ARTIFACT_FIELDS = ["id", "run", "kind", "mime", "blob", "sha256", "byte_size"] as const;
const LINK_BATCH = 25;

/** Artifacts with a repeated sha256 dropped, the first kept. */
export function dedupeBySha<T extends { id: string; sha256: string }>(artifacts: readonly T[]): T[] {
  const seen = new Set<string>();
  return artifacts.filter((artifact) => {
    const key = artifact.sha256 || `id:${artifact.id}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export function completenessText(complete: boolean): string {
  return complete ? "Completeness: complete." : "Completeness: unknown.";
}

export function evidenceLabel(artifact: ArtifactRecord): string {
  const size = artifact.byte_size;
  const bytes = typeof size === "number" && Number.isFinite(size) && size >= 0 ? `${size} bytes` : "size unavailable";
  return `${artifact.id} · ${artifact.sha256} · ${bytes}`;
}

/** The download path of a protected artifact blob with its file token. */
export function evidenceUrl(id: string, blob: string, token: string): string {
  return `/api/files/artifacts/${encodeURIComponent(id)}/${encodeURIComponent(blob)}?token=${encodeURIComponent(token)}`;
}

export function evidenceFailure(error: unknown): string {
  const status = statusOf(error);
  return status === 401 || status === 403 || status === 404 ? "Access denied." : "Could not access evidence.";
}

/** A filter matching any of the ids, each an escaped parameter. */
export function idsFilter(client: Pick<ToolboxClient, "filter">, ids: readonly string[]): string {
  const params = Object.fromEntries(ids.map((id, index) => [`id${index}`, id]));
  return client.filter(ids.map((_, index) => `id = {:id${index}}`).join(" || "), params);
}

export interface Evidence {
  artifacts: ArtifactRecord[];
  complete: boolean;
}

/** The artifacts a run owns plus those its events and tool calls link, deduplicated by sha256; incomplete when any page failed. */
export async function loadEvidence(client: ToolboxClient, run: string, signal: AbortSignal): Promise<Evidence> {
  let complete = true;
  const attempt = async <T,>(read: () => Promise<T[]>): Promise<T[]> => {
    try {
      return await read();
    } catch (error) {
      if (isAbort(error) || signal.aborted) throw error;
      complete = false;
      return [];
    }
  };
  const linking = client.filter('run = {:run} && artifact != ""', { run });
  const [owned, events, calls] = await Promise.all([
    attempt(() => gatherPages<ArtifactRecord>(client, { collection: "artifacts", fields: ARTIFACT_FIELDS, sort: ["created"], filter: client.filter("run = {:run}", { run }) }, signal)),
    attempt(() => gatherPages<{ artifact: string }>(client, { collection: "run_events", fields: ["id", "artifact"], sort: ["seq"], filter: linking }, signal)),
    attempt(() => gatherPages<{ artifact: string }>(client, { collection: "tool_calls", fields: ["id", "artifact"], sort: ["started_ts"], filter: linking }, signal)),
  ]);
  const known = new Set(owned.map((artifact) => artifact.id));
  const linked = [...new Set([...events, ...calls].map((row) => row.artifact).filter((id) => id && !known.has(id)))];
  const found: ArtifactRecord[] = [];
  for (let start = 0; start < linked.length; start += LINK_BATCH) {
    const batch = linked.slice(start, start + LINK_BATCH);
    found.push(...(await attempt(() => gatherPages<ArtifactRecord>(client, { collection: "artifacts", fields: ARTIFACT_FIELDS, filter: idsFilter(client, batch) }, signal))));
  }
  const order = new Map(linked.map((id, index) => [id, index]));
  found.sort((a, b) => (order.get(a.id) ?? 0) - (order.get(b.id) ?? 0));
  return { artifacts: dedupeBySha([...owned, ...found]), complete };
}

/**
 * Opens evidence: requests a file token, then navigates to the blob. A newer
 * open of the same artifact cancels the older one, whose answer is ignored.
 */
export function evidenceOpener(client: ToolboxClient, navigate: (url: string) => void, report: (id: string, message: string | null) => void) {
  const pending = new Map<string, AbortController>();
  return async (artifact: ArtifactRecord): Promise<void> => {
    pending.get(artifact.id)?.abort();
    const controller = client.track();
    pending.set(artifact.id, controller);
    report(artifact.id, null);
    try {
      if (!artifact.blob) throw new Error("artifact has no stored blob");
      const token = await client.fileToken(controller.signal);
      if (!controller.signal.aborted) navigate(evidenceUrl(artifact.id, artifact.blob, token));
    } catch (error) {
      if (!controller.signal.aborted && !isAbort(error)) report(artifact.id, evidenceFailure(error));
    } finally {
      client.release(controller);
      if (pending.get(artifact.id) === controller) pending.delete(artifact.id);
    }
  };
}

function navigateTo(url: string): void {
  window.location.assign(url);
}

export function EvidenceList({ evidence, open, messages }: { evidence: Evidence; open: (artifact: ArtifactRecord) => void; messages: Readonly<Record<string, string>> }) {
  return (
    <>
      <p>{completenessText(evidence.complete)}</p>
      {evidence.artifacts.length === 0 ? (
        <p>No evidence artifacts.</p>
      ) : (
        <ul className="toolbox-list">
          {evidence.artifacts.map((artifact) => (
            <li key={artifact.id}>
              <span>{evidenceLabel(artifact)}</span>{" "}
              <Button kind="tertiary" size="sm" onClick={() => open(artifact)}>
                Open evidence
              </Button>
              {messages[artifact.id] ? <p role="alert">{messages[artifact.id]}</p> : null}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function EvidenceRegion({ run }: { run: string }) {
  const client = useClient();
  const [messages, setMessages] = useState<Record<string, string>>({});
  const [open] = useState(() =>
    evidenceOpener(client, navigateTo, (id, message) =>
      setMessages((current) => {
        const next = { ...current };
        if (message) next[id] = message;
        else delete next[id];
        return next;
      }),
    ),
  );
  const state = useLoad((c, signal) => loadEvidence(c, run, signal), [run]);
  return (
    <DataRegion subject="evidence" state={state} isEmpty={() => false}>
      {(evidence) => <EvidenceList evidence={evidence} open={(artifact) => void open(artifact)} messages={messages} />}
    </DataRegion>
  );
}

// ---------------------------------------------------------------- run detail

export const SOURCE_TIME_TEXT = "Source time is not interpreted when timezone is unknown; ingestion time is separate.";

export function RunFacts({ run }: { run: RunRow }) {
  const execution = envelopePart(run, "execution");
  const reason = execution?.reason;
  return (
    <>
      <h2>{`Run ${run.id}`}</h2>
      <p>{`${identityText(run)} · ${orUnavailable(run.config, "Configuration")}`}</p>
      <h3>Metrics</h3>
      <Facts facts={RUN_METRICS.map((which): [string, string] => [which.label, showMetric(run, which)])} />
      <h3>Record</h3>
      <Facts
        facts={[
          ["Checks", shapeSummary(run.checks)],
          ["Grades", shapeSummary(run.grades)],
          ["Provenance", shapeSummary(run.provenance)],
          ["Execution validity", executionValidity(run) ?? UNAVAILABLE],
          ["Execution reason", typeof reason === "string" && reason !== "" ? reason : UNAVAILABLE],
          ["Preconditions", shapeSummary(execution?.preconditions)],
          ["Source time", orUnavailable(run.ts, "Source time")],
          ["Ingestion time", orUnavailable(run.created, "Ingestion time")],
          ["Source revision", sourceRevision(run)],
          ["CLI version", orUnavailable(run.cli_version, "CLI version")],
        ]}
      />
      <p>{SOURCE_TIME_TEXT}</p>
      <Disclosure summary="Raw measurement">
        <JsonBlock value={run.measurement} />
      </Disclosure>
      <Disclosure summary="Raw provenance">
        <JsonBlock value={run.provenance} />
      </Disclosure>
      <Disclosure summary="Raw grades">
        <JsonBlock value={run.grades} />
      </Disclosure>
    </>
  );
}

export interface EventRecord {
  id: string;
  seq: number;
  role: string;
  event_type: string;
  tool_name: string;
  is_error: boolean;
  payload: unknown;
}

export interface ToolCallRecord {
  id: string;
  tool_call_id: string;
  tool_name: string;
  status: string;
  is_error: boolean;
  input: unknown;
  output: unknown;
}

export function eventLabel(event: EventRecord): string {
  const parts = [`Seq ${event.seq}`, orUnavailable(event.role, "Role"), orUnavailable(event.event_type, "Event type")];
  if (event.tool_name) parts.push(event.tool_name);
  if (event.is_error) parts.push("error");
  return parts.join(" · ");
}

export function toolCallLabel(call: ToolCallRecord): string {
  return [call.tool_name, call.tool_call_id, orUnavailable(call.status, "Status")].join(" · ") + (call.is_error ? " · error" : "");
}

export function EventItem({ event }: { event: EventRecord }) {
  return (
    <Disclosure summary={eventLabel(event)}>
      <JsonBlock value={event.payload} />
    </Disclosure>
  );
}

export function ToolCallItem({ call }: { call: ToolCallRecord }) {
  return (
    <Disclosure summary={toolCallLabel(call)}>
      <h4>Input</h4>
      <JsonBlock value={call.input} />
      <h4>Output</h4>
      <JsonBlock value={call.output} />
    </Disclosure>
  );
}

function RunDetail({ id, onReturn }: { id: string; onReturn: () => void }) {
  return (
    <article className="toolbox-document">
      <Button kind="secondary" size="md" onClick={onReturn}>
        Return to runs
      </Button>
      <RecordRegion<RunRow> key={id} subject="run" collection="runs" id={id} fields={RUN_DETAIL_FIELDS}>
        {(run) => <RunFacts run={run} />}
      </RecordRegion>
      <h3>Evidence</h3>
      <EvidenceRegion key={`evidence-${id}`} run={id} />
      <h3>Events</h3>
      <PagedList<EventRecord>
        key={`events-${id}`}
        subject="run events"
        label="Events"
        query={(client) => ({
          collection: "run_events",
          fields: ["id", "seq", "ts", "role", "event_type", "tool_name", "status", "is_error", "payload"],
          sort: ["seq"],
          filter: client.filter("run = {:run}", { run: id }),
        })}
        deps={[id]}
        item={(event) => <EventItem event={event} />}
      />
      <h3>Tool calls</h3>
      <PagedList<ToolCallRecord>
        key={`calls-${id}`}
        subject="tool calls"
        label="Tool calls"
        query={(client) => ({
          collection: "tool_calls",
          fields: ["id", "tool_call_id", "tool_name", "status", "is_error", "started_ts", "wallclock_ms", "input", "output"],
          sort: ["started_ts"],
          filter: client.filter("run = {:run}", { run: id }),
        })}
        deps={[id]}
        item={(call) => <ToolCallItem call={call} />}
      />
    </article>
  );
}

// ---------------------------------------------------------------- the area

type ReturnTarget = { kind: "run" | "campaign"; id: string };

/** Focuses the link the reader left the list from, else the list heading. */
function focusReturnTarget(root: HTMLElement | null, target: ReturnTarget): void {
  if (!root) return;
  const attribute = target.kind === "run" ? "data-inspect" : "data-campaign";
  const link = [...root.querySelectorAll<HTMLElement>(`[${attribute}]`)].find((element) => element.getAttribute(attribute) === target.id);
  (link ?? root.querySelector<HTMLElement>(target.kind === "run" ? "#performance-runs" : "#performance-campaigns"))?.focus();
}

export function PerformanceView({ params }: { params: Record<string, string> }) {
  const run = params.run ?? "";
  const campaign = run ? "" : (params.campaign ?? "");
  const detail = run ? "run" : campaign ? "campaign" : "";
  const [selection, setSelection] = useState<RunRow[]>([]);
  const lists = useRef<HTMLDivElement>(null);
  const returning = useRef<ReturnTarget | null>(null);

  useEffect(() => {
    const target = returning.current;
    if (detail || !target) return;
    returning.current = null;
    // After the shell has focused the main region for this route change.
    const handle = setTimeout(() => focusReturnTarget(lists.current, target), 0);
    return () => clearTimeout(handle);
  }, [detail]);

  const returnFrom = (target: ReturnTarget) => {
    returning.current = target;
    window.location.hash = hashHref("performance");
  };
  const toggle = (entry: RunRow) => setSelection((current) => toggleSelection(current, entry));

  return (
    <div className="toolbox-area">
      <h1>Performance</h1>
      {/* The lists stay mounted while a detail shows, so returning restores them as they were. */}
      <div ref={lists} hidden={detail !== ""}>
        <RunsList selection={selection} onToggle={toggle} />
        <Comparison selection={selection} />
        <CampaignSearch />
      </div>
      {run ? <RunDetail id={run} onReturn={() => returnFrom({ kind: "run", id: run })} /> : null}
      {campaign ? <CampaignDetail id={campaign} onReturn={() => returnFrom({ kind: "campaign", id: campaign })} /> : null}
    </div>
  );
}
