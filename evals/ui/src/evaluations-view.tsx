// The Evaluations area: current assessments (optionally for one extender),
// each linking its eval run to the campaign, and the current job coverage.
import { Link } from "@carbon/react";
import type { ReactNode } from "react";
import { assessmentsQuery, expandedName, hashHref, orUnavailable, PagedList, type AssessmentRecord, type ToolboxClient } from "./api.tsx";

export interface JobCoverageRecord {
  id: string;
  job: string;
  eval_run: string;
  status: string;
  disposition: string;
  rationale: string;
  expand?: Record<string, unknown>;
}

export const JOB_COVERAGE_FIELDS = ["id", "job", "eval_run", "status", "disposition", "rationale", "expand.job.name"] as const;

/** The filter of assessments for one extender, or none without one. */
export function assessmentFilter(client: Pick<ToolboxClient, "filter">, extender: string): string | undefined {
  return extender ? client.filter("extender = {:extender}", { extender }) : undefined;
}

/** "<framework> · <element> · extender <name> · <verdict>; <assessor>; <evidence>; " — the text before the eval run. */
export function assessmentLead(assessment: AssessmentRecord): string {
  const extender = expandedName(assessment, "extender");
  return [
    `${orUnavailable(expandedName(assessment, "framework"), "Framework")} · `,
    `${orUnavailable(expandedName(assessment, "element"), "Element")} · `,
    `${extender ? `extender ${extender}` : "Extender name unavailable"} · `,
    `${orUnavailable(assessment.verdict, "Verdict")}; `,
    `${orUnavailable(assessment.assessor, "Assessor")}; `,
    `${orUnavailable(assessment.evidence, "Evidence")}; `,
  ].join("");
}

/** The text of a job coverage association, split around its eval run. */
export function coverageParts(coverage: JobCoverageRecord): [string, string] {
  return [
    `Current job association: ${orUnavailable(coverage.job, "Job id")} · ${orUnavailable(expandedName(coverage, "job"), "Job name")} · `,
    ` · ${orUnavailable(coverage.status, "Status")} · ${orUnavailable(coverage.disposition, "Disposition")}; ${orUnavailable(coverage.rationale, "Rationale")}`,
  ];
}

/** "eval run <id>" linking to its campaign, or "Eval run unavailable". */
export function EvalRunLink({ id }: { id: string }) {
  if (!id) return <>Eval run unavailable</>;
  return <Link href={hashHref("performance", { campaign: id })}>{`eval run ${id}`}</Link>;
}

export function AssessmentItem({ assessment }: { assessment: AssessmentRecord }): ReactNode {
  return (
    <p>
      {assessmentLead(assessment)}
      <EvalRunLink id={assessment.eval_run} />
    </p>
  );
}

export function CoverageItem({ coverage }: { coverage: JobCoverageRecord }): ReactNode {
  const [before, after] = coverageParts(coverage);
  return (
    <p>
      {before}
      <EvalRunLink id={coverage.eval_run} />
      {after}
    </p>
  );
}

export function EvaluationsView({ params }: { params: Record<string, string> }) {
  const extender = params.extender ?? "";
  return (
    <div className="toolbox-area">
      <h1>Evaluations</h1>
      <section aria-labelledby="evaluations-assessments">
        <h2 id="evaluations-assessments">Assessments</h2>
        {extender ? (
          <p>
            {`Showing assessments for extender ${extender}. `}
            <Link href={hashHref("evaluations")}>Show all assessments</Link>
          </p>
        ) : null}
        <PagedList<AssessmentRecord>
          key={extender}
          subject="assessments"
          label="Assessments"
          query={(client) => assessmentsQuery(assessmentFilter(client, extender))}
          deps={[extender]}
          item={(assessment) => <AssessmentItem assessment={assessment} />}
        />
      </section>
      <section aria-labelledby="evaluations-coverage">
        <h2 id="evaluations-coverage">Job coverage</h2>
        <PagedList<JobCoverageRecord>
          subject="job coverage"
          label="Job coverage"
          query={() => ({ collection: "job_coverage", fields: JOB_COVERAGE_FIELDS, sort: ["created"], expand: "job" })}
          deps={[]}
          item={(coverage) => <CoverageItem coverage={coverage} />}
        />
      </section>
    </div>
  );
}
