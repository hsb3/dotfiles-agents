import { Column, Grid, Pagination } from "@carbon/react";
import { useEffect, useState } from "react";
import { Session } from "./api";
import { evaluations, jobCoverage, recordScope, type Coverage, type Evaluation } from "./data";
import { Block, PageCrumbs, StateNotice } from "./ui";

type State = "loading" | "access" | "error" | "empty" | "populated";

const expire = (r: { kind: string; status?: number }, done: () => void) => {
  if (r.kind === "access" && r.status === 401) done();
};

export function AssessmentRows({ rows }: { rows: Evaluation[] }) {
  return (
    <ul>
      {rows.map((r) => (
        <li key={r.id}>
          {r.expand?.framework?.name || r.framework} · {r.expand?.element?.name || r.element} · extender {r.expand?.extender?.name || r.extender} · {r.verdict};{" "}
          {r.assessor || "assessor unavailable"}; {r.evidence || "evidence unavailable"}
          {r.eval_run && <>
            ; <a href={`#performance?campaign=${encodeURIComponent(r.eval_run)}`}>eval run {r.eval_run}</a>
          </>}
        </li>
      ))}
    </ul>
  );
}

export function CoverageRows({ rows }: { rows: Coverage[] }) {
  return (
    <ul>
      {rows.map((r) => (
        <li key={r.id}>
          Current job association: {r.expand?.job?.id ?? r.job} ·{" "}
          {r.expand?.job?.name || "job name unavailable"}
          {r.eval_run && <>
            {' · '}<a href={`#performance?campaign=${encodeURIComponent(r.eval_run)}`}>eval run {r.eval_run}</a>
          </>}
          {r.status && ` · ${r.status}`}
          {r.disposition && ` · ${r.disposition}`}
          {r.rationale && `; ${r.rationale}`}
        </li>
      ))}
    </ul>
  );
}

export function Evaluations({ session, onExpired }: { session: Session; onExpired: () => void }) {
  const [a, setA] = useState<Evaluation[]>([]);
  const [c, setC] = useState<Coverage[]>([]);
  const [as, setAs] = useState<State>("loading");
  const [cs, setCs] = useState<State>("loading");
  const [ap, setAp] = useState(1);
  const [cp, setCp] = useState(1);
  const [at, setAt] = useState(0);
  const [ct, setCt] = useState(0);
  const extender = typeof location === "undefined" ? undefined : recordScope(location.hash, "extender");

  useEffect(() => {
    const x = new AbortController();
    evaluations(session, extender, ap, x.signal).then((r) => {
      if (x.signal.aborted) return;
      if (r.kind === "ok") {
        setA(r.data.items);
        setAt(r.data.totalItems);
        setAs(r.data.items.length ? "populated" : "empty");
      } else {
        setAs(r.kind);
        expire(r, onExpired);
      }
    });
    return () => x.abort();
  }, [ap, extender, onExpired, session]);

  useEffect(() => {
    const x = new AbortController();
    jobCoverage(session, cp, x.signal).then((r) => {
      if (x.signal.aborted) return;
      if (r.kind === "ok") {
        setC(r.data.items);
        setCt(r.data.totalItems);
        setCs(r.data.items.length ? "populated" : "empty");
      } else {
        setCs(r.kind);
        expire(r, onExpired);
      }
    });
    return () => x.abort();
  }, [cp, onExpired, session]);

  return (
    <>
      <Block>
        <PageCrumbs current="Evaluations" />
        <h1>Evaluations</h1>
      </Block>
      <Grid fullWidth className="area-grid">
        <Column sm={4} md={8} lg={8}>
          <section className="surface">
            <h2>Assessments</h2>
            {as === "populated" ? (
              <>
                <AssessmentRows rows={a} />
                <Pagination
                  page={ap}
                  pageSize={25}
                  pageSizes={[25]}
                  totalItems={at}
                  onChange={({ page }) => setAp(page)}
                />
              </>
            ) : (
              <StateNotice state={as} subject="assessments" />
            )}
          </section>
        </Column>
        <Column sm={4} md={8} lg={8}>
          <section className="surface">
            <h2>Job coverage</h2>
            {cs === "populated" ? (
              <>
                <CoverageRows rows={c} />
                <Pagination
                  page={cp}
                  pageSize={25}
                  pageSizes={[25]}
                  totalItems={ct}
                  onChange={({ page }) => setCp(page)}
                />
              </>
            ) : (
              <StateNotice state={cs} subject="job coverage" />
            )}
          </section>
        </Column>
      </Grid>
    </>
  );
}
