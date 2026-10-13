import { afterAll, beforeAll, describe, expect, setDefaultTimeout, test } from "bun:test";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { assessmentsQuery, ClientProvider, ToolboxClient } from "../ui/src/api.tsx";
import {
  CampaignAssessment,
  CampaignFacts,
  chartData,
  COST,
  Comparison,
  comparisonEligibility,
  completenessText,
  DURATION,
  dedupeBySha,
  differenceRow,
  EventItem,
  evidenceFailure,
  evidenceLabel,
  EvidenceList,
  evidenceOpener,
  evidenceUrl,
  formatMeasured,
  formatNumber,
  FIRST_RUNS_VIEW,
  idsFilter,
  loadEvidence,
  loadRuns,
  measured,
  percentOfBaseline,
  PerformanceView,
  RESPONSE_METRICS,
  ResponseItem,
  RUN_COLUMNS,
  RUN_METRICS,
  RunFacts,
  runFilter,
  RunTable,
  SelectionTray,
  shapeSummary,
  showMetric,
  sortRuns,
  sourceRevision,
  ToolCallItem,
  toggleSelection,
  trayLabel,
  visibleRuns,
  type ArtifactRecord,
  type RunRow,
} from "../ui/src/performance-view.tsx";
import { api, HAS_POCKETBASE, startPocketBase, type PbServer } from "./pb.ts";

setDefaultTimeout(60000);

const HOSTILE = "fixture-<img src=x onerror=alert(1)>";
const ESCAPED = "fixture-&lt;img src=x onerror=alert(1)&gt;";
const offline = new ToolboxClient("http://127.0.0.1:1");

function render(node: ReactNode, client = offline): string {
  return renderToStaticMarkup(<ClientProvider value={client}>{node}</ClientProvider>);
}

function textOf(html: string): string {
  return html
    .replace(/<[^>]+>/g, " ")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#x27;/g, "'")
    .replace(/&amp;/g, "&")
    .replace(/\s+/g, " ");
}

const ALL_AVAILABLE = Object.fromEntries(RUN_METRICS.map((m) => [m.field, true]));

function run(id: string, overrides: Partial<RunRow> = {}, available: Record<string, boolean> = ALL_AVAILABLE, validity = "valid"): RunRow {
  return {
    id,
    campaign: "weekly",
    candidate: "scout",
    case: "stale-config-trap",
    harness: "opencode",
    model: "claude-sonnet-4-5",
    config: "baseline",
    ts: "2026-08-17T13:35:52",
    created: "2026-08-18 10:00:00.000Z",
    cli_version: "1.18.15",
    grades: [{ id: "a1", passed: true }],
    passed: true,
    skill_used: false,
    exit_code: 0,
    num_turns: 3,
    cost_usd: 0.0861297,
    duration_ms: 1466021,
    input_tokens: 13,
    output_tokens: 1006,
    cache_creation_tokens: 18170,
    cache_read_tokens: 9544,
    measurement: {
      version: 1,
      available,
      execution: { validity, reason: "producer recorded completed run evidence", preconditions: { harness: "opencode", timeout: 600 } },
      source_identity: { revision: { value: null, available: false } },
    },
    ...overrides,
  };
}

describe("measurement display", () => {
  test("a value shows only when version 1 marks it available and it has the right type", () => {
    const r = run("r1");
    expect(measured(r, DURATION)).toEqual({ available: true, value: 1466021 });
    expect(measured({ ...r, measurement: { ...(r.measurement as object), version: 2 } }, DURATION).available).toBe(false);
    expect(measured(run("r2", {}, { ...ALL_AVAILABLE, duration_ms: false }), DURATION).available).toBe(false);
    expect(measured({ ...r, duration_ms: -1 }, DURATION).available).toBe(false);
    expect(measured({ ...r, duration_ms: Number.POSITIVE_INFINITY }, DURATION).available).toBe(false);
    expect(measured({ ...r, duration_ms: "12" }, DURATION).available).toBe(false);
    expect(measured({ ...r, duration_ms: true }, DURATION).available).toBe(false);
    expect(measured({ ...r, measurement: { version: 1 } }, DURATION).available).toBe(false);
  });

  test("booleans for passed and skill_used, integers for exit_code", () => {
    const [passed, skill, exit] = ["passed", "skill_used", "exit_code"].map((f) => RUN_METRICS.find((m) => m.field === f)!);
    const r = run("r1");
    expect(showMetric(r, passed!)).toBe("Yes");
    expect(showMetric({ ...r, skill_used: false }, skill!)).toBe("No");
    expect(showMetric({ ...r, passed: 1 }, passed!)).toBe("Unavailable");
    expect(showMetric({ ...r, exit_code: 0 }, exit!)).toBe("0");
    expect(showMetric({ ...r, exit_code: 2 }, exit!)).toBe("2");
    expect(showMetric({ ...r, exit_code: 1.5 }, exit!)).toBe("Unavailable");
    expect(showMetric({ ...r, exit_code: false }, exit!)).toBe("Unavailable");
  });

  test("a legacy run without the envelope shows every metric as Unavailable", () => {
    const legacy = { ...run("legacy"), measurement: null };
    for (const m of RUN_METRICS) expect(showMetric(legacy, m)).toBe("Unavailable");
    const text = textOf(render(<RunFacts run={legacy} />));
    expect(text).toContain("Duration Unavailable Cost Unavailable Input tokens Unavailable");
    expect(text).toContain("Exit code Unavailable");
  });

  test("number formatting", () => {
    expect(formatNumber(0.0005)).toBe("5.00e-4");
    expect(formatNumber(-0.0005)).toBe("-5.00e-4");
    expect(formatNumber(0.000123456)).toBe("1.23e-4");
    expect(formatNumber(0.001)).toBe("0.001");
    expect(formatNumber(0)).toBe("0");
    expect(formatNumber(1466021)).toBe("1,466,021");
    expect(formatNumber(0.0861297)).toBe("0.086");
    expect(formatNumber(1234.56789)).toBe("1,234.568");
    expect(formatMeasured({ available: true, value: 0.0005 }, "USD")).toBe("5.00e-4 USD");
    expect(formatMeasured({ available: true, value: 1466021 }, "ms")).toBe("1,466,021 ms");
    expect(formatMeasured({ available: false }, "ms")).toBe("Unavailable");
    expect(showMetric(run("r1"), COST)).toBe("0.086 USD");
  });

  test("eval-response measurement availability", () => {
    const response = {
      id: "resp",
      role: "judge-1",
      prompt: HOSTILE,
      response_text: "",
      response_json: { ok: true },
      tokens: 65840,
      duration_ms: 0,
      measurement: { version: 1, available: { tokens: true, duration_ms: false } },
    };
    expect(RESPONSE_METRICS.map((m) => showMetric(response, m))).toEqual(["65,840 tokens", "Unavailable"]);
    const html = render(<ResponseItem response={response} />);
    const text = textOf(html);
    expect(text).toContain("judge-1 Tokens 65,840 tokens Duration Unavailable");
    expect(text).toContain("Prompt");
    expect(text).toContain("Response unavailable");
    expect(text).toContain("Raw response JSON");
    expect(html).toContain(ESCAPED);
    expect(html).not.toContain("<img");
  });

  test("record summaries and source revision", () => {
    expect(shapeSummary([1, 2, 3])).toBe("3 entries");
    expect(shapeSummary({ tools: [], plugins: [] })).toBe("tools, plugins");
    expect(shapeSummary(null)).toBe("Unavailable");
    expect(sourceRevision(run("r1"))).toBe("Unavailable");
    const revised = run("r1", { measurement: { version: 1, available: {}, source_identity: { revision: { value: "abc123", available: true } } } });
    expect(sourceRevision(revised)).toBe("abc123");
  });
});

describe("comparison", () => {
  const baseline = run("b1");
  const withRun = run("w1", { config: "with", duration_ms: 1000000, cost_usd: 0.1 });

  test("eligibility reasons, first failing one, in the documented order", () => {
    const reason = (selection: RunRow[]) => {
      const result = comparisonEligibility(selection);
      return result.eligible ? "eligible" : result.reason;
    };
    expect(reason([])).toBe("select-exactly-two");
    expect(reason([baseline])).toBe("select-exactly-two");
    expect(reason([baseline, withRun, run("x")])).toBe("select-exactly-two");
    expect(reason([baseline, { ...baseline }])).toBe("duplicate-record");
    expect(reason([{ ...baseline, campaign: "" }, withRun])).toBe("missing-campaign");
    expect(reason([baseline, { ...withRun, campaign: "other", candidate: "" }])).toBe("campaign-mismatch");
    expect(reason([baseline, { ...withRun, candidate: "" }])).toBe("missing-candidate");
    expect(reason([baseline, { ...withRun, candidate: "mermaid", model: "" }])).toBe("candidate-mismatch");
    expect(reason([baseline, { ...withRun, case: "other" }])).toBe("case-mismatch");
    expect(reason([baseline, { ...withRun, harness: "" }])).toBe("missing-harness");
    expect(reason([baseline, { ...withRun, harness: "claude" }])).toBe("harness-mismatch");
    expect(reason([baseline, { ...withRun, model: "" }])).toBe("missing-model");
    expect(reason([baseline, { ...withRun, model: "default" }])).toBe("model-mismatch");
    expect(reason([baseline, { ...withRun, config: "baseline" }])).toBe("configuration-mismatch");
    expect(reason([baseline, run("w2", { config: "with" }, ALL_AVAILABLE, "invalid")])).toBe("execution-invalid");
    expect(reason([baseline, { ...withRun, measurement: null }])).toBe("execution-invalid");
    const ok = comparisonEligibility([withRun, baseline]);
    expect(ok.eligible && ok.baseline.id === "b1" && ok.with.id === "w1").toBe(true);
  });

  test("differences: with minus baseline, percentage only when baseline > 0", () => {
    expect(differenceRow(DURATION, baseline, withRun)).toEqual({
      label: "Duration (ms)",
      baseline: "1,466,021 ms",
      with: "1,000,000 ms",
      difference: "-466,021 ms",
      percent: "-31.788%",
    });
    expect(differenceRow(COST, { ...baseline, cost_usd: 0 }, withRun).percent).toBe("Unavailable");
    expect(differenceRow(COST, { ...baseline, cost_usd: 0 }, withRun).difference).toBe("0.1 USD");
    expect(differenceRow(COST, run("b2", {}, { ...ALL_AVAILABLE, cost_usd: false }), withRun)).toMatchObject({ baseline: "Unavailable", difference: "Unavailable", percent: "Unavailable" });
    expect(percentOfBaseline(5, 0)).toBeNull();
    expect(percentOfBaseline(5, 10)).toBe(50);
  });

  test("a chart per metric only when both values are available", () => {
    expect(chartData(DURATION, baseline, withRun)).toEqual([
      { group: "Baseline", key: "Duration", value: 1466021 },
      { group: "With", key: "Duration", value: 1000000 },
    ]);
    expect(chartData(COST, run("b3", {}, { ...ALL_AVAILABLE, cost_usd: false }), withRun)).toBeNull();
  });

  test("an ineligible selection says why", () => {
    const text = textOf(render(<Comparison selection={[baseline]} />));
    expect(text).toContain("Select one independently valid baseline and one with-configuration record with matching recorded identity.");
    expect(text).toContain("Reason: select-exactly-two");
  });

  test("an eligible pair shows the caveat, both tables and one chart per available metric", () => {
    const partial = run("w3", { config: "with" }, { ...ALL_AVAILABLE, cost_usd: false, num_turns: false });
    const html = render(<Comparison selection={[baseline, partial]} />);
    const text = textOf(html);
    expect(text).toContain("n=1 each. Differences mean with minus baseline; no causality, savings, significance, or installed-state claim.");
    expect(text).toContain("Metric Baseline With With − baseline Percentage of baseline");
    expect(text).toContain("Duration (ms) 1,466,021 ms 1,466,021 ms 0 ms 0%");
    expect(text).toContain("Cost (USD) 0.086 USD Unavailable Unavailable Unavailable");
    expect(text).toContain("Record Source time (ts) Ingestion time (created) Source revision CLI version");
    expect(text).toContain("Baseline b1 2026-08-17T13:35:52 2026-08-18 10:00:00.000Z Unavailable 1.18.15");
    // seven numeric metrics, cost and turns unavailable on one side
    expect((html.match(/class="chart-holder"/g) ?? []).length).toBe(5);
    expect(html).toContain('aria-label="Duration chart"');
    expect(html).not.toContain('aria-label="Cost chart"');
  });
});

describe("runs list", () => {
  test("search and configuration reach the filter as escaped parameters", () => {
    expect(runFilter(offline, "", "all")).toBeUndefined();
    expect(runFilter(offline, "", "baseline")).toBe('config = "baseline"');
    expect(runFilter(offline, 'a"b', "with")).toBe(
      '(id ~ "a\\"b" || campaign ~ "a\\"b" || candidate ~ "a\\"b" || case ~ "a\\"b" || model ~ "a\\"b" || harness ~ "a\\"b") && config = "with"',
    );
  });

  test("client-side sort: ascending, unavailable last, ties by id; id keeps server order", () => {
    const rows = [
      run("e", { duration_ms: 5 }),
      run("d", {}, { ...ALL_AVAILABLE, duration_ms: false }),
      run("c", { duration_ms: 5 }),
      run("b", { duration_ms: 1 }),
      { ...run("a"), measurement: null },
    ];
    expect(sortRuns(rows, "duration").map((r) => r.id)).toEqual(["b", "c", "e", "a", "d"]);
    expect(sortRuns(rows, "id").map((r) => r.id)).toEqual(["e", "d", "c", "b", "a"]);
    expect(sortRuns([run("y", { cost_usd: 0.0005 }), run("x", { cost_usd: 0.0004 })], "cost").map((r) => r.id)).toEqual(["x", "y"]);
  });

  test("client-sorted rows page on the client; server rows are the page", () => {
    const rows = Array.from({ length: 60 }, (_, i) => run(`r${String(i).padStart(2, "0")}`));
    expect(visibleRuns({ rows, total: 60, serverPaged: false }, { ...FIRST_RUNS_VIEW, sort: "cost", page: 3 }).map((r) => r.id)).toEqual(rows.slice(50).map((r) => r.id));
    expect(visibleRuns({ rows: rows.slice(0, 50), total: 60, serverPaged: true }, { ...FIRST_RUNS_VIEW, page: 2, perPage: 50 }).length).toBe(50);
  });

  test("the table has the documented columns and renders record text as text", () => {
    expect(RUN_COLUMNS).toEqual(["Select", "Record", "Configuration", "Identity", "Execution validity", "Grades", "Outcome (passed)", "Duration", "Cost", "Inspect"]);
    const hostile = run("h1", { candidate: HOSTILE, grades: [{ evidence: "<b>x</b>" }] });
    const html = render(<RunTable runs={[hostile]} selection={[]} onToggle={() => {}} />);
    const text = textOf(html);
    expect(html).not.toContain("<img");
    expect(html).not.toContain("<b>");
    expect(html).toContain(ESCAPED);
    expect(text).toContain("h1 Campaign: weekly baseline opencode · claude-sonnet-4-5 · " + HOSTILE + " · stale-config-trap valid");
    expect(text).toContain('[{"evidence":"<b>x</b>"}] Yes 1,466,021 ms 0.086 USD Inspect');
    expect(html).toContain('href="#performance?run=h1"');
  });

  test("selection: at most two, other checkboxes disabled at two", () => {
    const [a, b, c] = [run("a"), run("b"), run("c")];
    let selection = toggleSelection([], a);
    selection = toggleSelection(selection, b);
    expect(toggleSelection(selection, c).map((r) => r.id)).toEqual(["a", "b"]);
    expect(toggleSelection(selection, a).map((r) => r.id)).toEqual(["b"]);
    const html = render(<RunTable runs={[a, b, c]} selection={selection} onToggle={() => {}} />);
    const boxes = html.match(/<input[^>]*type="checkbox"[^>]*>/g) ?? [];
    expect(boxes.length).toBe(3);
    expect(boxes.filter((box) => box.includes("disabled")).length).toBe(1);
    expect(boxes[2]).toContain("disabled");
  });

  test("the tray counts the selection and marks entries off the current page", () => {
    const [a, b] = [run("a"), run("b", { config: "with" })];
    expect(trayLabel(b, false)).toBe("b · with · scout (off page)");
    const text = textOf(render(<SelectionTray selection={[a, b]} onPage={new Set(["a"])} onRemove={() => {}} />));
    expect(text).toContain("Selected (2/2)");
    expect(text).toContain("a · baseline · scout");
    expect(text).toContain("b · with · scout (off page)");
    expect(textOf(render(<SelectionTray selection={[]} onPage={new Set()} onRemove={() => {}} />))).toContain("Selected (0/2)");
  });

  test("the area shows the runs, the tray, the comparison and the campaigns; a detail hides the lists", () => {
    const text = textOf(render(<PerformanceView params={{}} />));
    for (const marker of ["Runs", "Search runs", "Configuration", "Sort by", "Loading runs", "Selected (0/2)", "Comparison", "Campaigns", "Loading campaigns"]) {
      expect(text).toContain(marker);
    }
    const detail = render(<PerformanceView params={{ run: "r1" }} />);
    expect(detail).toMatch(/<div hidden="">/);
    expect(textOf(detail)).toContain("Return to runs");
    expect(textOf(detail)).toContain("Loading run events");
    expect(textOf(detail)).toContain("Loading tool calls");
    expect(textOf(detail)).toContain("Loading evidence");
    const campaign = textOf(render(<PerformanceView params={{ campaign: "c1" }} />));
    expect(campaign).toContain("Return to campaigns");
    expect(campaign).toContain("Conformance is not independent output quality; associations are current and can change.");
    expect(campaign).toContain("Loading responses");
    expect(campaign).toContain("Loading campaign assessments");
  });
});

describe("run detail", () => {
  test("metrics, record facts and disclosures", () => {
    const r = run("r1", { checks: [{}, {}], provenance: { tools: [], plugins: [] } });
    const html = render(<RunFacts run={r} />);
    const text = textOf(html);
    expect(text).toContain("Run r1");
    expect(text).toContain(
      "Duration 1,466,021 ms Cost 0.086 USD Input tokens 13 tokens Output tokens 1,006 tokens Cache creation tokens 18,170 tokens Cache read tokens 9,544 tokens Turns 3 turns Passed Yes Skill used No Exit code 0",
    );
    expect(text).toContain("Checks 2 entries Grades 1 entries Provenance tools, plugins");
    expect(text).toContain("Execution validity valid Execution reason producer recorded completed run evidence Preconditions harness, timeout");
    expect(text).toContain("Source time 2026-08-17T13:35:52 Ingestion time 2026-08-18 10:00:00.000Z Source revision Unavailable CLI version 1.18.15");
    expect(text).toContain("Source time is not interpreted when timezone is unknown; ingestion time is separate.");
    expect((html.match(/<details/g) ?? []).length).toBe(3);
    expect(text).toContain("Raw measurement");
  });

  test("events and tool calls open their payload, input and output as text", () => {
    const event = textOf(render(<EventItem event={{ id: "e", seq: 4, role: "tool_call", event_type: "tool_use", tool_name: "write", is_error: false, payload: { a: HOSTILE } }} />));
    expect(event).toContain("Seq 4 · tool_call · tool_use · write");
    expect(event).toContain(HOSTILE);
    const html = render(<ToolCallItem call={{ id: "t", tool_call_id: "call-1", tool_name: "Write", status: "error", is_error: true, input: { content: HOSTILE }, output: null }} />);
    expect(textOf(html)).toContain("Write · call-1 · error · error");
    expect(textOf(html)).toContain("Input");
    expect(textOf(html)).toContain("Output null");
    expect(html).not.toContain("<img");
  });
});

describe("evidence", () => {
  const a = (id: string, sha256: string, byte_size?: unknown): ArtifactRecord => ({ id, sha256, byte_size, blob: `${id}.txt` });

  test("deduplicated by sha256, first kept", () => {
    expect(dedupeBySha([a("1", "s1"), a("2", "s2"), a("3", "s1")]).map((x) => x.id)).toEqual(["1", "2"]);
  });

  test("labels, completeness and the download path", () => {
    expect(evidenceLabel(a("x", "abc", 12))).toBe("x · abc · 12 bytes");
    expect(evidenceLabel(a("x", "abc"))).toBe("x · abc · size unavailable");
    expect(completenessText(true)).toBe("Completeness: complete.");
    expect(completenessText(false)).toBe("Completeness: unknown.");
    expect(evidenceUrl("x1", "c4c7a8074865_ab.png", "t/k")).toBe("/api/files/artifacts/x1/c4c7a8074865_ab.png?token=t%2Fk");
    expect(evidenceFailure({ status: 403 })).toBe("Access denied.");
    expect(evidenceFailure({ status: 404 })).toBe("Access denied.");
    expect(evidenceFailure({ status: 500 })).toBe("Could not access evidence.");
    expect(evidenceFailure(new Error("x"))).toBe("Could not access evidence.");
    expect(idsFilter(offline, ["a", 'b"'])).toBe('id = "a" || id = "b\\""');
  });

  test("the list shows completeness, each artifact with Open evidence, and failures", () => {
    const text = textOf(render(<EvidenceList evidence={{ artifacts: [a("x", "abc", 5001)], complete: false }} open={() => {}} messages={{ x: "Access denied." }} />));
    expect(text).toContain("Completeness: unknown.");
    expect(text).toContain("x · abc · 5001 bytes Open evidence Access denied.");
  });

  test("a newer click on the same artifact supersedes the older one; failures are reported", async () => {
    let calls = 0;
    let status = 200;
    const server = Bun.serve({
      port: 0,
      hostname: "127.0.0.1",
      async fetch() {
        calls += 1;
        if (status !== 200) return Response.json({ message: "no" }, { status });
        if (calls === 1) await Bun.sleep(300);
        return Response.json({ token: `token-${calls}` });
      },
    });
    try {
      const client = new ToolboxClient(`http://127.0.0.1:${server.port}`);
      const visited: string[] = [];
      const reports: [string, string | null][] = [];
      const open = evidenceOpener(client, (url) => visited.push(url), (id, message) => reports.push([id, message]));
      const first = open(a("x", "abc"));
      await Bun.sleep(50);
      const second = open(a("x", "abc"));
      await Promise.all([first, second]);
      expect(visited).toEqual(["/api/files/artifacts/x/x.txt?token=token-2"]);
      expect(client.inFlight).toBe(0);

      status = 403;
      await open(a("y", "def"));
      status = 500;
      await open(a("z", "ghi"));
      await open({ id: "w", sha256: "jkl" });
      expect(reports.filter(([, m]) => m !== null)).toEqual([
        ["y", "Access denied."],
        ["z", "Could not access evidence."],
        ["w", "Could not access evidence."],
      ]);
    } finally {
      server.stop(true);
    }
  });
});

describe("campaign detail", () => {
  test("facts and assessments linking the extender to its documentation and evaluations", () => {
    const facts = textOf(render(<CampaignFacts run={{ id: "c1", slug: "m1-judged", kind: "judged", method: "how", criteria_text: "", status: "complete", notes: HOSTILE }} />));
    expect(facts).toContain("Campaign m1-judged");
    expect(facts).toContain("Slug m1-judged Kind judged Method how Criteria Criteria unavailable Status complete Notes " + HOSTILE);
    const html = render(
      <CampaignAssessment
        assessment={{
          id: "a1",
          extender: "x1",
          framework: "f1",
          element: "e1",
          eval_run: "c1",
          verdict: "partial",
          evidence: HOSTILE,
          assessor: "coverage-v1",
          expand: { extender: { name: "Handoff" }, framework: { name: "JTBD" }, element: { name: "Plan work" } },
        }}
      />,
    );
    expect(html).toContain('href="#documentation?extender=x1"');
    expect(html).toContain('href="#evaluations?extender=x1"');
    expect(textOf(html)).toContain(`Handoff ( evaluations ) · JTBD · Plan work · partial; ${HOSTILE}`);
    expect(html).not.toContain("<img");
  });
});

describe.skipIf(!HAS_POCKETBASE)("performance reads against PocketBase", () => {
  let server: PbServer;
  const email = "perf-reader@example.test";
  const password = "ReaderPassword123";
  const ids = { slow: "", fast: "", hostile: "", owned: "", linked: "", extender: "" };
  let blobContent = "";

  beforeAll(async () => {
    server = await startPocketBase();
    const token = await server.superuserToken();
    const post = async (collection: string, body: unknown) => {
      const r = await api(server, "POST", `/api/collections/${collection}/records`, body, token);
      if (r.status !== 200) throw new Error(`${collection}: ${r.status} ${JSON.stringify(r.body)}`);
      return r.body.id as string;
    };
    const upload = async (fields: Record<string, string>, content: string) => {
      const form = new FormData();
      for (const [key, value] of Object.entries(fields)) form.append(key, value);
      form.append("blob", new File([content], `${fields.sha256!.slice(0, 12)}.txt`, { type: "text/plain" }));
      const res = await fetch(`${server.url}/api/collections/artifacts/records`, { method: "POST", headers: { authorization: token }, body: form });
      if (res.status !== 200) throw new Error(`artifact: ${res.status} ${await res.text()}`);
      return ((await res.json()) as { id: string }).id;
    };
    await post("users", { email, password, passwordConfirm: password, verified: true });
    const measurement = (validity: string, available: Record<string, boolean>) => ({ version: 1, available, execution: { validity } });
    ids.slow = await post("runs", {
      harness: "opencode", campaign: "weekly", candidate: "scout", case: "stale-config-trap", config: "baseline", trial: 0, model: "m",
      duration_ms: 900, cost_usd: 0.2, measurement: measurement("valid", { duration_ms: true, cost_usd: true }),
    });
    ids.fast = await post("runs", {
      harness: "opencode", campaign: "weekly", candidate: "scout", case: "stale-config-trap", config: "with", trial: 0, model: "m",
      duration_ms: 100, cost_usd: 0.1, measurement: measurement("valid", { duration_ms: true, cost_usd: true }),
    });
    ids.hostile = await post("runs", {
      harness: "claude", campaign: "", candidate: HOSTILE, case: "other-case", config: "with", trial: 0, model: "m",
      duration_ms: 0, measurement: measurement("unknown", { duration_ms: false }),
    });
    blobContent = "x".repeat(64);
    ids.owned = await upload({ run: ids.slow, kind: "write_content", mime: "text/plain", sha256: "a".repeat(64), byte_size: "64" }, blobContent);
    ids.linked = await upload({ run: ids.fast, kind: "tool_output", mime: "text/plain", sha256: "b".repeat(64), byte_size: "3" }, "abc");
    await post("run_events", { run: ids.slow, seq: 0, role: "tool_call", vendor: "opencode", artifact: ids.linked, payload: {} });
    await post("run_events", { run: ids.slow, seq: 1, role: "system", vendor: "opencode", artifact: ids.owned, payload: {} });
    await post("tool_calls", { run: ids.slow, tool_call_id: "c1", tool_name: "write", artifact: ids.linked });

    const framework = await post("frameworks", { slug: "jtbd", name: "Jobs", kind: "job-taxonomy" });
    const element = await post("framework_elements", { framework, slug: "plan-work", name: "Plan work", element_kind: "job" });
    const extender = await post("extenders", { slug: "handoff", name: "Handoff", kind: "skill" });
    const evalRun = await post("eval_runs", { slug: "m1-judged", kind: "judged" });
    await post("assessments", { extender, framework, element, eval_run: evalRun, verdict: "present", evidence: "e", assessor: "coverage-v1" });
    ids.extender = extender;
  });

  afterAll(async () => {
    await server?.stop();
  });

  test("runs, assessments, evidence and an evidence file token", async () => {
    const client = new ToolboxClient(server.url);
    expect(await client.signIn(email, password)).toBeNull();
    const signal = new AbortController().signal;

    const all = await loadRuns(client, FIRST_RUNS_VIEW, signal);
    expect(all.serverPaged).toBe(true);
    expect(all.total).toBe(3);
    expect(all.rows.map((r) => r.id)).toEqual([ids.slow, ids.fast, ids.hostile].sort());
    const byCase = await loadRuns(client, { ...FIRST_RUNS_VIEW, query: "OTHER-case" }, signal);
    expect(byCase.rows.map((r) => r.candidate)).toEqual([HOSTILE]);
    const withOnly = await loadRuns(client, { ...FIRST_RUNS_VIEW, config: "with" }, signal);
    expect(withOnly.rows.map((r) => r.id).sort()).toEqual([ids.fast, ids.hostile].sort());
    const injected = await loadRuns(client, { ...FIRST_RUNS_VIEW, query: '" || id != "' }, signal);
    expect(injected.total).toBe(0);
    const byDuration = await loadRuns(client, { ...FIRST_RUNS_VIEW, sort: "duration" }, signal);
    expect(byDuration.serverPaged).toBe(false);
    expect(byDuration.rows.map((r) => r.id)).toEqual([ids.fast, ids.slow, ids.hostile]);
    const pair = comparisonEligibility(byDuration.rows.slice(0, 2));
    expect(pair.eligible).toBe(true);

    const evidence = await loadEvidence(client, ids.slow, signal);
    expect(evidence.complete).toBe(true);
    expect(evidence.artifacts.map((x) => x.id)).toEqual([ids.owned, ids.linked]);
    expect(evidence.artifacts[0]!.blob).toMatch(/^aaaaaaaaaaaa.*\.txt$/);

    const assessments = await client.list<Record<string, unknown>>(
      assessmentsQuery(client.filter("extender = {:e}", { e: ids.extender })),
      signal,
    );
    expect(assessments.items.length).toBe(1);
    expect(assessments.items[0]!.expand).toEqual({ extender: { name: "Handoff" }, framework: { name: "Jobs" }, element: { name: "Plan work" } });

    const blob = evidence.artifacts[0]!;
    const refused = await fetch(`${server.url}/api/files/artifacts/${blob.id}/${blob.blob}`);
    expect(refused.status).not.toBe(200);
    const visited: string[] = [];
    await evidenceOpener(client, (url) => visited.push(url), () => {})(blob);
    expect(visited.length).toBe(1);
    expect(visited[0]).toStartWith(`/api/files/artifacts/${blob.id}/${blob.blob}?token=`);
    const download = await fetch(`${server.url}${visited[0]}`);
    expect(download.status).toBe(200);
    expect(await download.text()).toBe(blobContent);
    client.signOut();
  });
});
