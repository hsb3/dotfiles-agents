// The UI side of PocketBase and the rendering pieces every Toolbox area shares:
// one SDK client whose token lives in memory only, sign-in and session end,
// cancellable paged reads, the five-state data region, safe links and a pager.
import PocketBase, { BaseAuthStore, getTokenPayload, type ListResult } from "pocketbase";
import { Button, Link, Select, SelectItem, TextInput } from "@carbon/react";
import { createContext, useContext, useEffect, useId, useState, type FormEvent, type ReactNode } from "react";

export const PAGE_SIZE = 25;
const MAX_TIMER_MS = 2_147_483_647;

// ---------------------------------------------------------------- sign-in

export interface Notice {
  title: string;
  subtitle: string;
}

export const SIGN_IN_REJECTED: Notice = { title: "Sign-in failed", subtitle: "Sign-in details were not accepted." };
export const SIGN_IN_UNAVAILABLE: Notice = { title: "Could not sign in. Try again.", subtitle: "" };

/** The HTTP status an SDK error carries, or 0 when it carries none. */
export function statusOf(error: unknown): number {
  if (typeof error !== "object" || error === null) return 0;
  const status = (error as { status?: unknown }).status;
  return typeof status === "number" ? status : 0;
}

/** True for a request the client or the browser cancelled. */
export function isAbort(error: unknown): boolean {
  if (typeof error !== "object" || error === null) return false;
  const e = error as { isAbort?: unknown; name?: unknown };
  return e.isAbort === true || e.name === "AbortError";
}

/** The message a failed sign-in shows: 400, 401 or 403 is a rejection, anything else a failure to reach the service. */
export function signInFailure(error: unknown): Notice {
  const status = statusOf(error);
  return status === 400 || status === 401 || status === 403 ? SIGN_IN_REJECTED : SIGN_IN_UNAVAILABLE;
}

/** The JWT `exp` of a token in epoch milliseconds, or null when it has none. */
export function tokenExpiry(token: string): number | null {
  const exp = getTokenPayload(token).exp;
  return typeof exp === "number" && Number.isFinite(exp) ? exp * 1000 : null;
}

// ---------------------------------------------------------------- client

export interface Timers {
  set(callback: () => void, ms: number): unknown;
  clear(handle: unknown): void;
  now(): number;
}

const browserTimers: Timers = {
  set: (callback, ms) => setTimeout(callback, ms),
  clear: (handle) => clearTimeout(handle as ReturnType<typeof setTimeout>),
  now: () => Date.now(),
};

export interface ListQuery {
  collection: string;
  /** The named fields; only these are requested. */
  fields: readonly string[];
  /** Sort keys; `id` is always appended as the last one. */
  sort?: readonly string[];
  /** A filter built with `ToolboxClient.filter`, never by string concatenation. */
  filter?: string;
  expand?: string;
  page?: number;
  perPage?: number;
}

/** The sort keys with any `id` key removed and `id` appended last. */
export function sortWithIdLast(keys: readonly string[] = []): string {
  return [...keys.filter((key) => key.replace(/^[-+]/, "") !== "id"), "id"].join(",");
}

/** The SDK options of a list read: named fields, id-last sort, no SDK auto-cancellation, the caller's signal. */
export function listOptions(query: ListQuery, signal: AbortSignal) {
  return {
    fields: query.fields.join(","),
    sort: sortWithIdLast(query.sort),
    requestKey: null,
    signal,
    ...(query.filter ? { filter: query.filter } : {}),
    ...(query.expand ? { expand: query.expand } : {}),
  };
}

/**
 * One PocketBase SDK client with an in-memory auth store. The session ends on
 * `signOut`, when the token's `exp` passes and on any 401 answer; ending it
 * cancels every tracked request.
 */
export class ToolboxClient {
  readonly pb: PocketBase;
  private readonly controllers = new Set<AbortController>();
  private readonly listeners = new Set<() => void>();
  private expiryHandle: unknown = null;

  constructor(
    baseUrl: string,
    private readonly timers: Timers = browserTimers,
  ) {
    this.pb = new PocketBase(baseUrl, new BaseAuthStore());
    this.pb.autoCancellation(false);
    this.pb.beforeSend = (url, options) => {
      if (this.signedIn && this.expired()) this.signOut();
      return { url, options };
    };
    this.pb.afterSend = (response: Response, data: unknown) => {
      if (response.status === 401 && this.signedIn) this.signOut();
      return data;
    };
  }

  get signedIn(): boolean {
    return this.pb.authStore.token !== "";
  }

  /** Registers a listener for session changes; returns its removal. */
  readonly subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  readonly isSignedIn = (): boolean => this.signedIn;

  /** Signs in against `users`; returns the notice to show, or null on success. */
  async signIn(email: string, password: string): Promise<Notice | null> {
    try {
      await this.pb.collection("users").authWithPassword(email, password, { requestKey: null });
    } catch (error) {
      this.pb.authStore.clear();
      return signInFailure(error);
    }
    this.beginSession();
    return this.signedIn ? null : SIGN_IN_UNAVAILABLE;
  }

  /** Starts the session the auth store now holds: schedules its end at the token's `exp`. */
  beginSession(): void {
    this.scheduleExpiry();
    this.notify();
  }

  /** Ends the session: cancels tracked requests, clears the token and the expiry timer. */
  signOut(): void {
    for (const controller of this.controllers) controller.abort();
    this.controllers.clear();
    if (this.expiryHandle !== null) this.timers.clear(this.expiryHandle);
    this.expiryHandle = null;
    this.pb.authStore.clear();
    this.notify();
  }

  /** A request controller that `signOut` aborts. */
  track(): AbortController {
    const controller = new AbortController();
    this.controllers.add(controller);
    return controller;
  }

  release(controller: AbortController): void {
    this.controllers.delete(controller);
  }

  /** Number of tracked requests still in flight. */
  get inFlight(): number {
    return this.controllers.size;
  }

  /** A filter whose values reach PocketBase only as escaped literals. */
  filter(expression: string, params: Record<string, unknown>): string {
    return this.pb.filter(expression, params);
  }

  list<T>(query: ListQuery, signal: AbortSignal): Promise<ListResult<T>> {
    return this.pb.collection(query.collection).getList<T>(query.page ?? 1, query.perPage ?? PAGE_SIZE, listOptions(query, signal));
  }

  one<T>(collection: string, id: string, fields: readonly string[], signal: AbortSignal, expand?: string): Promise<T> {
    return this.pb.collection(collection).getOne<T>(id, {
      fields: fields.join(","),
      requestKey: null,
      signal,
      ...(expand ? { expand } : {}),
    });
  }

  /** A GET of any API path, such as the catalog route. */
  get<T>(path: string, signal: AbortSignal): Promise<T> {
    return this.pb.send<T>(path, { method: "GET", requestKey: null, signal });
  }

  private expired(): boolean {
    const expiry = tokenExpiry(this.pb.authStore.token);
    return expiry === null || expiry <= this.timers.now();
  }

  private scheduleExpiry(): void {
    if (this.expiryHandle !== null) this.timers.clear(this.expiryHandle);
    this.expiryHandle = null;
    if (!this.signedIn) return;
    const expiry = tokenExpiry(this.pb.authStore.token);
    const remaining = expiry === null ? 0 : expiry - this.timers.now();
    if (remaining <= 0) {
      this.signOut();
      return;
    }
    this.expiryHandle = this.timers.set(() => this.scheduleExpiry(), Math.min(remaining, MAX_TIMER_MS));
  }

  private notify(): void {
    for (const listener of [...this.listeners]) listener();
  }
}

const ClientContext = createContext<ToolboxClient | null>(null);
export const ClientProvider = ClientContext.Provider;

export function useClient(): ToolboxClient {
  const client = useContext(ClientContext);
  if (!client) throw new Error("Toolbox client missing");
  return client;
}

// ---------------------------------------------------------------- loads

export type Load<T> = { status: "loading" } | { status: "access" } | { status: "error" } | { status: "ready"; data: T };
export type Loader<T> = (client: ToolboxClient, signal: AbortSignal) => Promise<T>;

/** Which non-record state a failed read shows; "aborted" shows nothing new. */
export function failureState(error: unknown): "access" | "error" | "aborted" {
  if (isAbort(error)) return "aborted";
  const status = statusOf(error);
  return status === 401 || status === 403 || status === 404 ? "access" : "error";
}

/** Runs one read and reports its outcome, unless the controller was aborted first (a superseded answer is ignored). */
export async function runLoad<T>(
  client: ToolboxClient,
  load: Loader<T>,
  controller: AbortController,
  report: (state: Load<T>) => void,
): Promise<void> {
  try {
    const data = await load(client, controller.signal);
    if (!controller.signal.aborted) report({ status: "ready", data });
  } catch (error) {
    const state = failureState(error);
    if (!controller.signal.aborted && state !== "aborted") report({ status: state });
  } finally {
    client.release(controller);
  }
}

/** Reads on mount and whenever `deps` change; the previous read is cancelled and its answer ignored. */
export function useLoad<T>(load: Loader<T>, deps: readonly unknown[]): Load<T> {
  const client = useClient();
  const [state, setState] = useState<Load<T>>({ status: "loading" });
  useEffect(() => {
    const controller = client.track();
    setState({ status: "loading" });
    void runLoad(client, load, controller, setState);
    return () => controller.abort();
  }, [client, ...deps]);
  return state;
}

// ---------------------------------------------------------------- data region

export type RegionKind = "loading" | "access" | "error" | "empty";

/** The heading and sentence a data region shows in each non-record state. */
export function regionText(kind: RegionKind, subject: string): [string, string] {
  switch (kind) {
    case "loading":
      return [`Loading ${subject}`, "Please wait while Toolbox reads the current records."];
    case "access":
      return [`Access to ${subject} is unavailable`, "Your session may have expired or this area may not be available to your account."];
    case "error":
      return [`Could not load ${subject}`, "The service did not return a usable response. Try again."];
    case "empty":
      return [`No ${subject} records`, "This accessible source currently has no records."];
  }
}

/** True for an empty list result or array. */
export function isEmptyData(data: unknown): boolean {
  if (Array.isArray(data)) return data.length === 0;
  if (typeof data === "object" && data !== null && Array.isArray((data as { items?: unknown }).items)) {
    return (data as { items: unknown[] }).items.length === 0;
  }
  return false;
}

export function RegionMessage({ kind, subject, text }: { kind: RegionKind; subject: string; text?: [string, string] }) {
  const [title, body] = text ?? regionText(kind, subject);
  const alert = kind === "access" || kind === "error";
  return (
    <div className={`toolbox-region__message toolbox-region__message--${kind}`} role={alert ? "alert" : "status"}>
      <p className="toolbox-region__title">{title}</p>
      {body ? <p>{body}</p> : null}
    </div>
  );
}

/** Shows exactly one of loading, access, error, empty or the records. */
export function DataRegion<T>({
  subject,
  state,
  isEmpty = isEmptyData,
  emptyText,
  children,
}: {
  subject: string;
  state: Load<T>;
  isEmpty?: (data: T) => boolean;
  emptyText?: [string, string];
  children: (data: T) => ReactNode;
}) {
  let content: ReactNode;
  if (state.status !== "ready") content = <RegionMessage kind={state.status} subject={subject} />;
  else if (isEmpty(state.data)) content = <RegionMessage kind="empty" subject={subject} text={emptyText} />;
  else content = children(state.data);
  return (
    <section className="toolbox-region" aria-label={subject} aria-busy={state.status === "loading"}>
      {content}
    </section>
  );
}

// ---------------------------------------------------------------- links

/**
 * The URL when it is safe to link: a same-origin path (`/…`, not `//…`) or an
 * http/https URL without credentials, with no surrounding whitespace and no
 * backslash. Anything else returns null and is shown as text.
 */
export function safeUrl(value: unknown): string | null {
  if (typeof value !== "string" || value === "" || value !== value.trim() || value.includes("\\")) return null;
  if (/[\u0000-\u001f\u007f]/.test(value)) return null;
  if (value.startsWith("/")) return value.startsWith("//") ? null : value;
  const scheme = /^(https?):\/\/([^/?#]*)/i.exec(value);
  if (!scheme || scheme[2] === undefined || scheme[2] === "" || scheme[2].includes("@")) return null;
  try {
    const url = new URL(value);
    if ((url.protocol !== "http:" && url.protocol !== "https:") || url.username || url.password) return null;
  } catch {
    return null;
  }
  return value;
}

/** A link when the URL is safe, else the text (the URL itself unless `fallback` is given). */
export function SafeLink({ url, label, fallback }: { url: unknown; label?: string; fallback?: string }) {
  const href = safeUrl(url);
  if (href) return <Link href={href} rel="noreferrer">{label ?? href}</Link>;
  return <span>{fallback ?? (typeof url === "string" ? url : "")}</span>;
}

/** The hash route of an area with its parameters, e.g. `#documentation?extender=<id>`. */
export function hashHref(area: string, params: Record<string, string> = {}): string {
  const query = new URLSearchParams(params).toString();
  return query ? `#${area}?${query}` : `#${area}`;
}

// ---------------------------------------------------------------- paging and search

export function pageCount(totalItems: number, perPage: number): number {
  return Math.max(1, Math.ceil(totalItems / perPage));
}

/** One client-side page of a list (pages count from 1). */
export function pageSlice<T>(items: readonly T[], page: number, perPage: number): T[] {
  return items.slice((page - 1) * perPage, page * perPage);
}

export function Pager({
  label,
  page,
  totalPages,
  onPage,
  pageSize,
  pageSizes,
  onPageSize,
}: {
  label: string;
  page: number;
  totalPages: number;
  onPage: (page: number) => void;
  pageSize?: number;
  pageSizes?: readonly number[];
  onPageSize?: (size: number) => void;
}) {
  const sizeId = useId();
  return (
    <nav className="toolbox-pager" aria-label={`${label} pages`}>
      <Button kind="ghost" size="sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        Previous page
      </Button>
      <span>{`Page ${page} of ${totalPages}`}</span>
      <Button kind="ghost" size="sm" disabled={page >= totalPages} onClick={() => onPage(page + 1)}>
        Next page
      </Button>
      {pageSizes && onPageSize ? (
        <Select id={sizeId} size="sm" inline labelText="Per page" value={String(pageSize ?? pageSizes[0])} onChange={(e) => onPageSize(Number(e.target.value))}>
          {pageSizes.map((size) => (
            <SelectItem key={size} value={String(size)} text={String(size)} />
          ))}
        </Select>
      ) : null}
    </nav>
  );
}

/**
 * A list read through the API one page at a time, each record an item of a
 * list, with its pager. Key it by the search round so a new search returns to page 1.
 */
export function PagedList<T extends { id: string }>({
  subject,
  label,
  query,
  deps,
  item,
  emptyText,
}: {
  subject: string;
  label: string;
  query: (client: ToolboxClient) => Omit<ListQuery, "page">;
  deps: readonly unknown[];
  item: (record: T) => ReactNode;
  emptyText?: [string, string];
}) {
  const [page, setPage] = useState(1);
  const state = useLoad((client, signal) => client.list<T>({ ...query(client), page }, signal), [...deps, page]);
  return (
    <DataRegion subject={subject} state={state} emptyText={emptyText}>
      {(result) => (
        <>
          <ul className="toolbox-list">
            {result.items.map((record) => (
              <li key={record.id}>{item(record)}</li>
            ))}
          </ul>
          <Pager label={label} page={result.page} totalPages={Math.max(1, result.totalPages)} onPage={setPage} />
        </>
      )}
    </DataRegion>
  );
}

/** One record read by id with the named fields, shown in a data region. */
export function RecordRegion<T>({
  subject,
  collection,
  id,
  fields,
  expand,
  children,
}: {
  subject: string;
  collection: string;
  id: string;
  fields: readonly string[];
  expand?: string;
  children: (record: T) => ReactNode;
}) {
  const state = useLoad((client, signal) => client.one<T>(collection, id, fields, signal, expand), [collection, id, expand]);
  return (
    <DataRegion subject={subject} state={state}>
      {children}
    </DataRegion>
  );
}

/** The current search text and a round that grows on every search, so keyed pagers reset. */
export function useSearch(): { query: string; round: number; search: (query: string) => void } {
  const [state, setState] = useState({ query: "", round: 0 });
  return { ...state, search: (query) => setState((prev) => ({ query: query.trim(), round: prev.round + 1 })) };
}

export function SearchForm({ label, onSearch }: { label: string; onSearch: (query: string) => void }) {
  const id = useId();
  const [text, setText] = useState("");
  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSearch(text);
  };
  return (
    <form role="search" className="toolbox-search" onSubmit={submit}>
      <TextInput id={id} labelText={label} value={text} onChange={(event) => setText(event.target.value)} />
      <Button type="submit" size="md">
        Search
      </Button>
      <Button
        type="button"
        kind="secondary"
        size="md"
        onClick={() => {
          setText("");
          onSearch("");
        }}
      >
        Reset search
      </Button>
    </form>
  );
}

// ---------------------------------------------------------------- extenders

export interface ExtenderSummary {
  id: string;
  slug: string;
  name?: string;
  kind: string;
}

export const EXTENDER_LIST_FIELDS = ["id", "slug", "name", "kind", "description", "body", "entry_file", "source"] as const;

/** The extender search `slug ~ q || name ~ q || description ~ q`, or none for an empty query. */
export function extenderSearchFilter(client: ToolboxClient, query: string): string | undefined {
  return query ? client.filter("slug ~ {:q} || name ~ {:q} || description ~ {:q}", { q: query }) : undefined;
}

export function extenderLabel(extender: ExtenderSummary): string {
  return `${extender.name || extender.slug} · ${extender.kind}`;
}

/** The "Database extenders" list: the extender search, by slug, each linking to its documentation. */
export function ExtenderList({ query, selected }: { query: string; selected?: string }) {
  return (
    <PagedList<ExtenderSummary>
      subject="database extenders"
      label="Database extenders"
      query={(client) => ({ collection: "extenders", fields: EXTENDER_LIST_FIELDS, sort: ["slug"], filter: extenderSearchFilter(client, query) })}
      deps={[query]}
      item={(extender) => (
        <Link href={hashHref("documentation", { extender: extender.id })} aria-current={extender.id === selected ? "true" : undefined}>
          {extenderLabel(extender)}
        </Link>
      )}
    />
  );
}
