// The Documentation area: the extender search list and, for the chosen
// extender, its entry file, source facts, body and reader files.
import { Link } from "@carbon/react";
import { ExtenderList, hashHref, orUnavailable, PagedList, RecordRegion, safeUrl, SearchForm, useSearch } from "./api.tsx";

export interface ExtenderDocument {
  id: string;
  body: string;
  entry_file: string;
  source: string;
}

export interface SourceFacts {
  id: string;
  name: string;
  url: string;
  publisher_kind: string;
  maintenance: string;
}

export interface ReaderFile {
  id: string;
  extender: string;
  role: string;
  content: string;
  relpath: string;
}

const EXTENDER_FIELDS = ["id", "body", "entry_file", "source"];
const SOURCE_FIELDS = ["id", "name", "url", "publisher_kind", "maintenance"];

export const NO_READER_FILES = "This metadata-only extender has no stored reader files.";

export function sourceSummary(source: Pick<SourceFacts, "publisher_kind" | "maintenance">): string {
  return `${orUnavailable(source.publisher_kind, "Publisher kind")} · ${orUnavailable(source.maintenance, "Maintenance")}`;
}

export function fileLabel(file: Pick<ReaderFile, "role" | "relpath">): string {
  return `${orUnavailable(file.role, "Role")} · ${file.relpath}`;
}

/** A source's name, publisher kind and maintenance, and "Visit source" when its URL is safe. */
export function SourceDetails({ source }: { source: SourceFacts }) {
  const href = safeUrl(source.url);
  return (
    <>
      <p>{`Source: ${orUnavailable(source.name, "Name")}`}</p>
      <p>{sourceSummary(source)}</p>
      <p>{href ? <Link href={href} rel="noreferrer">Visit source</Link> : "Source URL unavailable"}</p>
    </>
  );
}

/** A reader file as "<role> · <relpath>", opening its content as text. */
export function ReaderFileItem({ file }: { file: ReaderFile }) {
  return (
    <details className="toolbox-disclosure">
      <summary>{fileLabel(file)}</summary>
      {file.content ? <pre className="toolbox-text">{file.content}</pre> : <p>No stored content.</p>}
    </details>
  );
}

function ReaderFiles({ extender }: { extender: string }) {
  return (
    <PagedList<ReaderFile>
      subject="reader files"
      label="Reader files"
      query={(client) => ({
        collection: "files",
        fields: ["id", "extender", "role", "content", "relpath"],
        sort: ["relpath"],
        filter: client.filter("extender = {:extender}", { extender }),
      })}
      deps={[extender]}
      emptyText={[NO_READER_FILES, ""]}
      item={(file) => <ReaderFileItem file={file} />}
    />
  );
}

/** One stored extender: entry file, source facts, the assessments link, body and reader files. */
export function ExtenderDetails({ extender }: { extender: ExtenderDocument }) {
  return (
    <article className="toolbox-document">
      <h2>{`Extender ${extender.id}`}</h2>
      <p>{extender.entry_file ? `Entry file: ${extender.entry_file}` : "Entry file unavailable"}</p>
      {extender.source ? (
        <RecordRegion<SourceFacts> subject="source" collection="sources" id={extender.source} fields={SOURCE_FIELDS}>
          {(source) => <SourceDetails source={source} />}
        </RecordRegion>
      ) : (
        <p>Source unavailable</p>
      )}
      <p>
        <Link href={hashHref("evaluations", { extender: extender.id })}>View assessments</Link>
      </p>
      <h3>Body</h3>
      {extender.body ? <pre className="toolbox-text">{extender.body}</pre> : <p>No stored extender body.</p>}
      <h3>Reader files</h3>
      <ReaderFiles extender={extender.id} />
    </article>
  );
}

export function DocumentationView({ params }: { params: Record<string, string> }) {
  const { query, round, search } = useSearch();
  const selected = params.extender ?? "";
  return (
    <div className="toolbox-area">
      <h1>Documentation</h1>
      <div className="toolbox-columns">
        <section aria-labelledby="documentation-extenders">
          <h2 id="documentation-extenders">Database extenders</h2>
          <SearchForm label="Search extenders" onSearch={search} />
          <ExtenderList key={round} query={query} selected={selected} />
        </section>
        <section aria-label="Extender documentation">
          {selected ? (
            <RecordRegion<ExtenderDocument> key={selected} subject="extender documentation" collection="extenders" id={selected} fields={EXTENDER_FIELDS}>
              {(extender) => <ExtenderDetails extender={extender} />}
            </RecordRegion>
          ) : (
            <p>Choose an extender to read its documentation.</p>
          )}
        </section>
      </div>
    </div>
  );
}
