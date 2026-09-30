import { Button, Column, Grid, Pagination, Search } from "@carbon/react";
import { useEffect, useState } from "react";
import { Session } from "./api";
import {
  catalog,
  distributions,
  extenders,
  filterCatalog,
  type Catalog as Snapshot,
  type Extender,
} from "./data";
import { Block, PageCrumbs, StateNotice } from "./ui";

type State = "loading" | "access" | "error" | "empty" | "populated";

const expired = (r: { kind: string; status?: number }, done: () => void) => {
  if (r.kind === "access" && r.status === 401) done();
};

function Database({
  session,
  query,
  page,
  distributionPage,
  onPage,
  onDistributionPage,
  onExpired,
}: {
  session: Session;
  query: string;
  page: number;
  distributionPage: number;
  onPage: (page: number) => void;
  onDistributionPage: (page: number) => void;
  onExpired: () => void;
}) {
  const [state, setState] = useState<State>("loading");
  const [rows, setRows] = useState<Extender[]>([]);
  const [total, setTotal] = useState(0);
  const [dState, setDState] = useState<State>("loading");
  const [members, setMembers] = useState<{ id: string; slug: string; members: string[] }[]>([]);
  const [dTotal, setDTotal] = useState(0);

  useEffect(() => {
    const c = new AbortController();
    extenders(session, query, page, c.signal).then((r) => {
      if (c.signal.aborted) return;
      if (r.kind === "ok") {
        setRows(r.data.items);
        setTotal(r.data.totalItems);
        setState(r.data.items.length ? "populated" : "empty");
      } else {
        setState(r.kind);
        expired(r, onExpired);
      }
    });
    return () => c.abort();
  }, [onExpired, page, query, session]);

  useEffect(() => {
    const c = new AbortController();
    distributions(session, distributionPage, c.signal).then((r) => {
      if (c.signal.aborted) return;
      if (r.kind === "ok") {
        setMembers(r.data.items);
        setDTotal(r.data.totalItems);
        setDState(r.data.items.length ? "populated" : "empty");
      } else {
        setDState(r.kind);
        expired(r, onExpired);
      }
    });
    return () => c.abort();
  }, [distributionPage, onExpired, session]);

  return (
    <section className="surface">
      <h2>Database extenders</h2>
      {state === "populated" ? (
        <>
          <ul>
            {rows.map((row) => (
              <li key={row.id}>
                <a href={`#documentation?extender=${encodeURIComponent(row.id)}`}>
                  {row.name || row.slug}
                </a> · {row.kind}
              </li>
            ))}
          </ul>
          <Pagination
            page={page}
            pageSize={25}
            pageSizes={[25]}
            totalItems={total}
            onChange={({ page }) => onPage(page)}
          />
        </>
      ) : (
        <StateNotice state={state} subject="extender" />
      )}
      <h3>Explicit distribution membership</h3>
      {dState === "populated" ? (
        <>
          <ul>
            {members.map((row) => (
              <li key={row.id}>
                {row.slug} · {row.members.length} member record(s)
              </li>
            ))}
          </ul>
          <Pagination
            page={distributionPage}
            pageSize={25}
            pageSizes={[25]}
            totalItems={dTotal}
            onChange={({ page }) => onDistributionPage(page)}
          />
        </>
      ) : (
        <StateNotice state={dState} subject="distribution" />
      )}
    </section>
  );
}

export function Catalog({ session, onExpired }: { session: Session; onExpired: () => void }) {
  const [state, setState] = useState<State>("loading");
  const [snapshot, setSnapshot] = useState<Snapshot>();
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [databasePage, setDatabasePage] = useState(1);
  const [distributionPage, setDistributionPage] = useState(1);

  useEffect(() => {
    const c = new AbortController();
    catalog(session, c.signal).then((r) => {
      if (c.signal.aborted) return;
      if (r.kind === "ok") {
        setSnapshot(r.data);
        setState("populated");
      } else {
        setState(r.kind);
        expired(r, onExpired);
      }
    });
    return () => c.abort();
  }, [onExpired, session]);

  const combined = [
    ...filterCatalog(snapshot?.workflows ?? [], query).map((row) => ({ ...row, family: "Workflow" })),
    ...filterCatalog(snapshot?.plugins ?? [], query).map((row) => ({ ...row, family: "Plugin" })),
  ];
  const shown = combined.slice((page - 1) * 10, page * 10);
  const resetPages = () => {
    setPage(1);
    setDatabasePage(1);
    setDistributionPage(1);
  };

  return (
    <>
      <Block>
        <PageCrumbs current="Catalog" />
        <h1>Catalog</h1>
        <p>
          {snapshot?.source_snapshot
            ? `Packaged source snapshot: ${snapshot.source_snapshot}.`
            : "Packaged records are separate from database extenders and explicit distribution membership."}
        </p>
        <Search
          id="catalog-search"
          labelText="Search packaged snapshot"
          value={query}
          onChange={(e) => {
            setQuery(e.currentTarget.value);
            resetPages();
          }}
        />
        <Button
          kind="ghost"
          onClick={() => {
            setQuery("");
            resetPages();
          }}
        >
          Reset search
        </Button>
      </Block>
      {state !== "populated" ? (
        <Block>
          <StateNotice state={state} subject="catalog" />
        </Block>
      ) : (
        <>
          <Grid fullWidth className="area-grid">
            <Column sm={4} md={8} lg={8}>
              <section className="surface">
                <h2>Packaged catalog</h2>
                {shown.map((row, i) => (
                  <article key={row.id ?? i}>
                    <p>{row.family}</p>
                    <h3>{row.name ?? row.slug ?? row.id}</h3>
                    <p>{row.guidance ?? row.description}</p>
                  </article>
                ))}
                {!combined.length && <p>No packaged records match this search.</p>}
              </section>
            </Column>
            <Column sm={4} md={8} lg={8}>
              <Database
                session={session}
                query={query}
                page={databasePage}
                distributionPage={distributionPage}
                onPage={setDatabasePage}
                onDistributionPage={setDistributionPage}
                onExpired={onExpired}
              />
            </Column>
          </Grid>
          <Block>
            <Pagination
              page={page}
              pageSize={10}
              pageSizes={[10]}
              totalItems={combined.length}
              onChange={({ page }) => setPage(page)}
            />
          </Block>
        </>
      )}
    </>
  );
}
