import { Button, Column, Grid, Pagination, Search } from "@carbon/react";
import { useEffect, useState } from "react";
import { Session } from "./api";
import {
  documentationFor,
  extenders,
  extenderWithSource,
  recordScope,
  safeHref,
  type DocumentationFile,
  type Extender,
} from "./data";
import { Block, PageCrumbs, StateNotice } from "./ui";

type State = "loading" | "access" | "error" | "empty" | "populated";

const expire = (r: { kind: string; status?: number }, done: () => void) => {
  if (r.kind === "access" && r.status === 401) done();
};

export function DocumentationReader({ parent }: { parent: Extender }) {
  const source = parent.expand?.source;
  const href = source?.url && safeHref(source.url);

  return (
    <>
      <p>Entry file: {parent.entry_file || "Entry file unavailable"}</p>
      <p>Source: {source?.name || "Source unavailable"}</p>
      {source && (
        <p>{[source.publisher_kind, source.maintenance].filter(Boolean).join(" · ") || "Source metadata unavailable"}</p>
      )}
      <p>{href ? <a href={href}>Visit source</a> : "Source URL unavailable"}</p>
      <Button kind="tertiary" href={`#evaluations?extender=${encodeURIComponent(parent.id)}`}>
        View assessments
      </Button>
      <pre>{parent.body || "No stored extender body."}</pre>
    </>
  );
}

export function Documentation({ session, onExpired }: { session: Session; onExpired: () => void }) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [state, setState] = useState<State>("loading");
  const [rows, setRows] = useState<Extender[]>([]);
  const [id, setId] = useState<string | undefined>(() =>
    typeof location === "undefined" ? undefined : recordScope(location.hash, "extender"),
  );
  const [parent, setParent] = useState<Extender>();
  const [parentState, setParentState] = useState<State>("empty");
  const [files, setFiles] = useState<DocumentationFile[]>([]);
  const [file, setFile] = useState<DocumentationFile>();
  const [filePage, setFilePage] = useState(1);
  const [fileTotal, setFileTotal] = useState(0);
  const [fileState, setFileState] = useState<State>("empty");

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
        expire(r, onExpired);
      }
    });
    return () => c.abort();
  }, [onExpired, page, query, session]);

  useEffect(() => {
    if (!id) return;
    const c = new AbortController();
    setParent(undefined);
    setParentState("loading");
    setFiles([]);
    setFile(undefined);
    setFileState("loading");
    extenderWithSource(session, id, c.signal).then((r) => {
      if (c.signal.aborted) return;
      if (r.kind === "ok") {
        setParent(r.data);
        setParentState("populated");
      } else {
        setParentState(r.kind);
        expire(r, onExpired);
      }
    });
    documentationFor(session, id, filePage, c.signal).then((r) => {
      if (c.signal.aborted) return;
      if (r.kind === "ok") {
        setFiles(r.data.items);
        setFileTotal(r.data.totalItems);
        setFileState(r.data.items.length ? "populated" : "empty");
      } else {
        setFileState(r.kind);
        expire(r, onExpired);
      }
    });
    return () => c.abort();
  }, [filePage, id, onExpired, session]);

  const reset = () => {
    setQuery("");
    setPage(1);
    setId(undefined);
    setParent(undefined);
    setParentState("empty");
    setFiles([]);
    setFilePage(1);
    setFileTotal(0);
    setFileState("empty");
    setFile(undefined);
  };

  return (
    <>
      <Block>
        <PageCrumbs current="Documentation" />
        <h1>Documentation</h1>
        <Search
          id="documentation-search"
          labelText="Search extenders"
          value={query}
          onChange={(e) => {
            setQuery(e.currentTarget.value);
            setPage(1);
          }}
        />
        <Button kind="ghost" onClick={reset}>
          Reset search
        </Button>
      </Block>
      <Grid fullWidth className="area-grid">
        <Column sm={4} md={4} lg={5}>
          <section className="surface">
            <h2>Extenders</h2>
            {state === "populated" ? (
              <>
                <ul>
                  {rows.map((row) => (
                    <li key={row.id}>
                      <Button
                        kind="ghost"
                        onClick={() => {
                          setId(row.id);
                          setFilePage(1);
                        }}
                      >
                        {row.name || row.slug}
                      </Button>
                    </li>
                  ))}
                </ul>
                <Pagination
                  page={page}
                  pageSize={25}
                  pageSizes={[25]}
                  totalItems={total}
                  onChange={({ page }) => setPage(page)}
                />
              </>
            ) : (
              <StateNotice state={state} subject="documentation" />
            )}
          </section>
        </Column>
        <Column sm={4} md={4} lg={11}>
          <section className="surface">
            <h2>Reader</h2>
            {parentState === "populated" && parent && <DocumentationReader parent={parent} />}
            {parentState !== "populated" && id && (
              <StateNotice state={parentState} subject="extender" />
            )}
            {fileState === "populated" && (
              <>
                <ul>
                  {files.map((row) => (
                    <li key={row.id}>
                      <Button kind="ghost" onClick={() => setFile(row)}>
                        {row.role} · {row.relpath}
                      </Button>
                    </li>
                  ))}
                </ul>
                <Pagination
                  page={filePage}
                  pageSize={25}
                  pageSizes={[25]}
                  totalItems={fileTotal}
                  onChange={({ page }) => setFilePage(page)}
                />
              </>
            )}
            {fileState === "empty" && id && (
              <p>This metadata-only extender has no stored reader files.</p>
            )}
            {fileState !== "populated" && fileState !== "empty" && (
              <StateNotice state={fileState} subject="stored files" />
            )}
            {file && <pre>{file.content}</pre>}
          </section>
        </Column>
      </Grid>
    </>
  );
}
