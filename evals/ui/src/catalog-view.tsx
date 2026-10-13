// The Catalog area: the packaged catalog with its search, the database
// extenders and the explicit distribution membership.
import { Tag } from "@carbon/react";
import { useState } from "react";
import { DataRegion, ExtenderList, PagedList, Pager, pageCount, pageSlice, SearchForm, useLoad, useSearch } from "./api.tsx";

export const CATALOG_PAGE_SIZE = 10;

export interface CatalogPlugin {
  id: string;
  name: string;
  version: string;
  description: string;
  workflows: string[];
}

export interface CatalogWorkflow {
  id: string;
  name: string;
  guidance: string;
  plugins: string[];
}

export interface Catalog {
  plugins: CatalogPlugin[];
  source_snapshot: string;
  workflows: CatalogWorkflow[];
}

export interface CatalogMatch {
  label: "Workflow" | "Plugin";
  id: string;
  name: string;
  text: string;
}

const text = (value: unknown): string => (typeof value === "string" ? value : "");

/** The catalog route's answer, or an error when it is not the documented shape. */
export function parseCatalog(raw: unknown): Catalog {
  const value = raw as Partial<Record<keyof Catalog, unknown>> | null;
  if (typeof value !== "object" || value === null || !Array.isArray(value.plugins) || !Array.isArray(value.workflows)) {
    throw new Error("catalog: unexpected shape");
  }
  return {
    plugins: value.plugins as CatalogPlugin[],
    source_snapshot: text(value.source_snapshot),
    workflows: value.workflows as CatalogWorkflow[],
  };
}

/** Workflows then plugins whose id, name, slug, description or guidance contains the query, case-insensitively. */
export function catalogMatches(catalog: Catalog, query: string): CatalogMatch[] {
  const needle = query.trim().toLowerCase();
  const hit = (record: object) => {
    const fields = record as Record<string, unknown>;
    return ["id", "name", "slug", "description", "guidance"].some((key) => text(fields[key]).toLowerCase().includes(needle));
  };
  return [
    ...catalog.workflows.filter(hit).map((w): CatalogMatch => ({ label: "Workflow", id: w.id, name: text(w.name), text: text(w.guidance) })),
    ...catalog.plugins.filter(hit).map((p): CatalogMatch => ({ label: "Plugin", id: p.id, name: text(p.name), text: text(p.description) })),
  ];
}

/** The packaged matches of a search, 10 per page. */
export function PackagedMatches({ catalog, query }: { catalog: Catalog; query: string }) {
  const [page, setPage] = useState(1);
  const matches = catalogMatches(catalog, query);
  if (matches.length === 0) return <p role="status">No packaged records match this search.</p>;
  const pages = pageCount(matches.length, CATALOG_PAGE_SIZE);
  const current = Math.min(page, pages);
  return (
    <>
      <ul className="toolbox-list">
        {pageSlice(matches, current, CATALOG_PAGE_SIZE).map((match) => (
          <li key={`${match.label}:${match.id}`}>
            <Tag type={match.label === "Workflow" ? "blue" : "teal"} size="sm">
              {match.label}
            </Tag>
            <strong>{match.name}</strong>
            <p>{match.text}</p>
          </li>
        ))}
      </ul>
      <Pager label="Packaged records" page={current} totalPages={pages} onPage={setPage} />
    </>
  );
}

interface DistributionRecord {
  id: string;
  slug: string;
  kind: string;
  version: string;
  members: string[];
}

export function distributionLabel(distribution: Pick<DistributionRecord, "slug" | "members">): string {
  const count = Array.isArray(distribution.members) ? distribution.members.length : 0;
  return `${distribution.slug} · ${count} member record(s)`;
}

function DistributionList() {
  return (
    <PagedList<DistributionRecord>
      subject="distribution membership"
      label="Distributions"
      query={() => ({ collection: "distributions", fields: ["id", "slug", "kind", "version", "members"], sort: ["slug"] })}
      deps={[]}
      item={(distribution) => distributionLabel(distribution)}
    />
  );
}

export function CatalogView() {
  const { query, round, search } = useSearch();
  const state = useLoad((client, signal) => client.get<unknown>("/api/toolbox/catalog", signal).then(parseCatalog), []);
  return (
    <div className="toolbox-area">
      <h1>Catalog</h1>
      <SearchForm label="Search the catalog" onSearch={search} />
      <div className="toolbox-columns">
        <section aria-labelledby="catalog-packaged">
          <h2 id="catalog-packaged">Packaged catalog</h2>
          <DataRegion subject="packaged catalog" state={state} isEmpty={(c) => c.workflows.length + c.plugins.length === 0}>
            {(catalog) => (
              <>
                <p>{`Packaged source snapshot: ${catalog.source_snapshot}.`}</p>
                <PackagedMatches key={round} catalog={catalog} query={query} />
              </>
            )}
          </DataRegion>
        </section>
        <section aria-labelledby="catalog-extenders">
          <h2 id="catalog-extenders">Database extenders</h2>
          <ExtenderList key={round} query={query} />
          <h2>Explicit distribution membership</h2>
          <DistributionList key={round} />
        </section>
      </div>
    </div>
  );
}
