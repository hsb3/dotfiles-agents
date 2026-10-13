import { describe, expect, test } from "bun:test";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { ASSESSMENT_FIELDS, assessmentsQuery, ClientProvider, expandedName, searchFilter, ToolboxClient, type AssessmentRecord } from "../ui/src/api.tsx";
import {
  AssessmentItem,
  assessmentFilter,
  assessmentLead,
  CoverageItem,
  coverageParts,
  EvaluationsView,
  JOB_COVERAGE_FIELDS,
  type JobCoverageRecord,
} from "../ui/src/evaluations-view.tsx";

const HOSTILE = "fixture-<img src=x onerror=alert(1)>";
const client = new ToolboxClient("http://127.0.0.1:1");

function render(node: ReactNode): string {
  return renderToStaticMarkup(<ClientProvider value={client}>{node}</ClientProvider>);
}

function textOf(html: string): string {
  return html
    .replace(/<[^>]+>/g, "")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#x27;/g, "'")
    .replace(/&amp;/g, "&");
}

const ASSESSMENT: AssessmentRecord = {
  id: "a1",
  framework: "f1",
  element: "el1",
  extender: "x1",
  eval_run: "run1",
  verdict: "present",
  evidence: "keeps the handoff current",
  assessor: "coverage-v1",
  expand: { framework: { name: "Jobs to be done" }, element: { name: "Sustain continuity" }, extender: { name: "Handoff" } },
};

const COVERAGE: JobCoverageRecord = {
  id: "c1",
  job: "job1",
  eval_run: "run2",
  status: "partial",
  disposition: "author",
  rationale: "needs a dataviz skill",
  expand: { job: { name: "Produce dataviz" } },
};

describe("assessments", () => {
  test("named fields with the expanded names, by created with id last, filtered by an escaped extender", () => {
    expect(ASSESSMENT_FIELDS).toEqual([
      "id",
      "framework",
      "element",
      "extender",
      "eval_run",
      "verdict",
      "evidence",
      "assessor",
      "expand.extender.name",
      "expand.framework.name",
      "expand.element.name",
    ]);
    const query = assessmentsQuery(assessmentFilter(client, 'x" || id != "'));
    expect(query.collection).toBe("assessments");
    expect(query.sort).toEqual(["created"]);
    expect(query.expand).toBe("extender,framework,element");
    expect(query.filter).toBe('extender = "x\\" || id != \\""');
    expect(assessmentFilter(client, "")).toBeUndefined();
  });

  test("renders the documented line, the eval run linking to its campaign", () => {
    const html = render(<AssessmentItem assessment={ASSESSMENT} />);
    expect(textOf(html)).toBe("Jobs to be done · Sustain continuity · extender Handoff · present; coverage-v1; keeps the handoff current; eval run run1");
    expect(html).toContain('href="#performance?campaign=run1"');
  });

  test("missing values read '<thing> unavailable'", () => {
    const bare: AssessmentRecord = { ...ASSESSMENT, element: "", eval_run: "", evidence: "", assessor: "", expand: {} };
    expect(assessmentLead(bare)).toBe("Framework unavailable · Element unavailable · Extender name unavailable · present; Assessor unavailable; Evidence unavailable; ");
    const html = render(<AssessmentItem assessment={bare} />);
    expect(textOf(html)).toEndWith("Evidence unavailable; Eval run unavailable");
    expect(html).not.toContain("#performance");
  });

  test("record text renders as text", () => {
    const html = render(<AssessmentItem assessment={{ ...ASSESSMENT, evidence: HOSTILE, expand: { extender: { name: HOSTILE } } }} />);
    expect(html).not.toContain("<img");
    expect(html).toContain("fixture-&lt;img src=x onerror=alert(1)&gt;");
  });

  test("expanded names", () => {
    expect(expandedName(ASSESSMENT, "extender")).toBe("Handoff");
    expect(expandedName({ expand: { extender: { name: "" } } }, "extender")).toBeUndefined();
    expect(expandedName({}, "extender")).toBeUndefined();
  });
});

describe("job coverage", () => {
  test("named fields and the documented line", () => {
    expect(JOB_COVERAGE_FIELDS).toEqual(["id", "job", "eval_run", "status", "disposition", "rationale", "expand.job.name"]);
    const html = render(<CoverageItem coverage={COVERAGE} />);
    expect(textOf(html)).toBe("Current job association: job1 · Produce dataviz · eval run run2 · partial · author; needs a dataviz skill");
  });

  test("missing values", () => {
    const [before, after] = coverageParts({ ...COVERAGE, status: "", disposition: "", rationale: "", expand: undefined });
    expect(before).toBe("Current job association: job1 · Job name unavailable · ");
    expect(after).toBe(" · Status unavailable · Disposition unavailable; Rationale unavailable");
  });
});

describe("the area", () => {
  test("without a filter it lists every assessment and the coverage", () => {
    const text = textOf(render(<EvaluationsView params={{}} />));
    expect(text).toContain("Assessments");
    expect(text).toContain("Loading assessments");
    expect(text).toContain("Job coverage");
    expect(text).not.toContain("Showing assessments for extender");
  });

  test("with ?extender it names the filter and links back to all", () => {
    const html = render(<EvaluationsView params={{ extender: HOSTILE }} />);
    expect(textOf(html)).toContain(`Showing assessments for extender ${HOSTILE}.`);
    expect(html).toContain('href="#evaluations"');
    expect(html).not.toContain("<img");
  });

  test("search filters reach PocketBase as escaped parameters", () => {
    expect(searchFilter(client, ["slug", "name"], 'a"b')).toBe('slug ~ "a\\"b" || name ~ "a\\"b"');
    expect(searchFilter(client, ["slug"], "")).toBeUndefined();
  });
});
