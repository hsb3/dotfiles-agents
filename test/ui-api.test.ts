import { afterAll, beforeAll, describe, expect, setDefaultTimeout, test } from "bun:test";
import { copyFileSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { BaseAuthStore, LocalAuthStore } from "pocketbase";
import {
  extenderSearchFilter,
  failureState,
  hashHref,
  isEmptyData,
  listOptions,
  pageCount,
  pageSlice,
  regionText,
  runLoad,
  safeUrl,
  SIGN_IN_REJECTED,
  SIGN_IN_UNAVAILABLE,
  signInFailure,
  sortWithIdLast,
  tokenExpiry,
  ToolboxClient,
  type Load,
  type Timers,
} from "../ui/src/api.tsx";
import { parseHash, HOME_ROUTE, routeKey } from "../ui/src/app.tsx";
import { catalogMatches, distributionLabel, parseCatalog, type Catalog } from "../ui/src/catalog-view.tsx";
import { fileLabel, orUnavailable, sourceSummary } from "../ui/src/documentation-view.tsx";
import { api, freePort, HAS_POCKETBASE, REPO_ROOT, startPocketBase, type PbServer } from "./pb.ts";

// The live-server block starts PocketBase and waits out its auth rate limit.
setDefaultTimeout(60000);

function b64url(value: unknown): string {
  return Buffer.from(JSON.stringify(value)).toString("base64url");
}

/** An unsigned JWT-shaped token with the given `exp` (seconds). */
function fakeJwt(exp?: number): string {
  return `${b64url({ alg: "HS256", typ: "JWT" })}.${b64url(exp === undefined ? { id: "u1" } : { id: "u1", exp })}.c2ln`;
}

class FakeTimers implements Timers {
  time = 1_000_000_000_000;
  pending: { at: number; callback: () => void; handle: number }[] = [];
  private next = 1;
  set(callback: () => void, ms: number) {
    const handle = this.next++;
    this.pending.push({ at: this.time + ms, callback, handle });
    return handle;
  }
  clear(handle: unknown) {
    this.pending = this.pending.filter((p) => p.handle !== handle);
  }
  now() {
    return this.time;
  }
  advance(ms: number) {
    this.time += ms;
    const due = this.pending.filter((p) => p.at <= this.time);
    this.pending = this.pending.filter((p) => p.at > this.time);
    for (const p of due) p.callback();
  }
}

describe("safe URLs", () => {
  test("links same-origin paths and credential-free http(s) URLs only", () => {
    for (const ok of ["/docs/a", "/", "/api/files?x=1#y", "https://example.com", "http://example.com/a?b=c", "HTTPS://Example.com/x"]) {
      expect(safeUrl(ok)).toBe(ok);
    }
    for (const bad of [
      "//evil.example/x",
      "javascript:alert(1)",
      "data:text/html,hi",
      "mailto:a@example.com",
      "ftp://example.com",
      " https://example.com",
      "https://example.com ",
      "https://example.com\n",
      "https://user:pass@example.com",
      "https://user@example.com",
      "http://@example.com",
      "https://example.com\\@evil",
      "/a\\b",
      "https:example.com",
      "https:///x",
      "relative/path",
      "#documentation",
      "",
      null,
      42,
    ]) {
      expect(safeUrl(bad)).toBeNull();
    }
  });
});

describe("list reads", () => {
  test("id is always the last sort key", () => {
    expect(sortWithIdLast()).toBe("id");
    expect(sortWithIdLast(["slug"])).toBe("slug,id");
    expect(sortWithIdLast(["-created", "id", "slug", "-id"])).toBe("-created,slug,id");
  });

  test("options request only the named fields, disable SDK auto-cancellation and carry the signal", () => {
    const signal = new AbortController().signal;
    const options = listOptions({ collection: "extenders", fields: ["id", "slug"], sort: ["slug"] }, signal);
    expect(options).toEqual({ fields: "id,slug", sort: "slug,id", requestKey: null, signal });
    const filtered = listOptions({ collection: "files", fields: ["id"], filter: "x = 1", expand: "extender" }, signal);
    expect(filtered.filter).toBe("x = 1");
    expect(filtered.expand).toBe("extender");
  });

  test("user text reaches the extender filter only as an escaped literal", () => {
    const client = new ToolboxClient("http://127.0.0.1:1");
    expect(extenderSearchFilter(client, "")).toBeUndefined();
    expect(extenderSearchFilter(client, "mermaid")).toBe('slug ~ "mermaid" || name ~ "mermaid" || description ~ "mermaid"');
    const injected = extenderSearchFilter(client, '" || id != "')!;
    expect(injected).toBe('slug ~ "\\" || id != \\"" || name ~ "\\" || id != \\"" || description ~ "\\" || id != \\""');
  });

  test("paging helpers", () => {
    expect(pageCount(0, 25)).toBe(1);
    expect(pageCount(25, 25)).toBe(1);
    expect(pageCount(26, 25)).toBe(2);
    expect(pageSlice([1, 2, 3, 4, 5], 2, 2)).toEqual([3, 4]);
    expect(pageSlice([1, 2, 3, 4, 5], 3, 2)).toEqual([5]);
  });
});

describe("sign-in and session", () => {
  test("400, 401 and 403 are rejections; anything else is a failure to sign in", () => {
    for (const status of [400, 401, 403]) expect(signInFailure({ status })).toEqual(SIGN_IN_REJECTED);
    for (const error of [{ status: 0 }, { status: 429 }, { status: 500 }, new Error("offline"), null]) {
      expect(signInFailure(error)).toEqual(SIGN_IN_UNAVAILABLE);
    }
    expect(SIGN_IN_REJECTED).toEqual({ title: "Sign-in failed", subtitle: "Sign-in details were not accepted." });
    expect(SIGN_IN_UNAVAILABLE.title).toBe("Could not sign in. Try again.");
  });

  test("the client keeps its token in an in-memory store", () => {
    const client = new ToolboxClient("http://127.0.0.1:1");
    expect(client.pb.authStore).toBeInstanceOf(BaseAuthStore);
    expect(client.pb.authStore).not.toBeInstanceOf(LocalAuthStore);
    expect(client.signedIn).toBe(false);
  });

  test("reads the JWT exp", () => {
    expect(tokenExpiry(fakeJwt(1700000000))).toBe(1700000000000);
    expect(tokenExpiry(fakeJwt())).toBeNull();
    expect(tokenExpiry("not-a-token")).toBeNull();
  });

  test("the session ends when the token's exp passes", () => {
    const timers = new FakeTimers();
    const client = new ToolboxClient("http://127.0.0.1:1", timers);
    let changes = 0;
    client.subscribe(() => changes++);
    client.pb.authStore.save(fakeJwt(timers.time / 1000 + 60));
    client.beginSession();
    expect(client.signedIn).toBe(true);
    timers.advance(59_000);
    expect(client.signedIn).toBe(true);
    timers.advance(1_000);
    expect(client.signedIn).toBe(false);
    expect(changes).toBe(2);
  });

  test("an expiry beyond the timer range is rescheduled, and an expired token ends at once", () => {
    const timers = new FakeTimers();
    const client = new ToolboxClient("http://127.0.0.1:1", timers);
    client.pb.authStore.save(fakeJwt(timers.time / 1000 + 40 * 86400));
    client.beginSession();
    timers.advance(2_147_483_647);
    expect(client.signedIn).toBe(true);
    expect(timers.pending.length).toBe(1);
    timers.advance(40 * 86400 * 1000);
    expect(client.signedIn).toBe(false);

    client.pb.authStore.save(fakeJwt(timers.time / 1000 - 1));
    client.beginSession();
    expect(client.signedIn).toBe(false);
  });

  test("log out cancels every tracked request and clears the expiry timer", () => {
    const timers = new FakeTimers();
    const client = new ToolboxClient("http://127.0.0.1:1", timers);
    client.pb.authStore.save(fakeJwt(timers.time / 1000 + 60));
    client.beginSession();
    const a = client.track();
    const b = client.track();
    expect(client.inFlight).toBe(2);
    client.signOut();
    expect(a.signal.aborted && b.signal.aborted).toBe(true);
    expect(client.inFlight).toBe(0);
    expect(timers.pending).toEqual([]);
    expect(client.pb.authStore.token).toBe("");
  });

  test("an unreachable service is a failure to sign in", async () => {
    const client = new ToolboxClient(`http://127.0.0.1:${await freePort()}`);
    expect(await client.signIn("a@example.test", "x")).toEqual(SIGN_IN_UNAVAILABLE);
    expect(client.signedIn).toBe(false);
  });
});

describe("loads and data regions", () => {
  test("failures map to access or error; aborts show nothing new", () => {
    for (const status of [401, 403, 404]) expect(failureState({ status })).toBe("access");
    for (const status of [0, 400, 500]) expect(failureState({ status })).toBe("error");
    expect(failureState({ isAbort: true, status: 0 })).toBe("aborted");
    expect(failureState(new DOMException("x", "AbortError"))).toBe("aborted");
  });

  test("a superseded read's answer is ignored", async () => {
    const client = new ToolboxClient("http://127.0.0.1:1");
    const reports: Load<number>[] = [];
    let resolve!: (n: number) => void;
    const controller = client.track();
    const done = runLoad(client, () => new Promise<number>((r) => (resolve = r)), controller, (s) => reports.push(s));
    controller.abort();
    resolve(7);
    await done;
    expect(reports).toEqual([]);
    expect(client.inFlight).toBe(0);
  });

  test("a read reports its records or its failure state", async () => {
    const client = new ToolboxClient("http://127.0.0.1:1");
    const reports: Load<number>[] = [];
    await runLoad(client, async () => 3, client.track(), (s) => reports.push(s));
    await runLoad(client, async () => Promise.reject({ status: 403 }), client.track(), (s) => reports.push(s));
    await runLoad(client, async () => Promise.reject({ status: 500 }), client.track(), (s) => reports.push(s));
    await runLoad(client, async () => Promise.reject({ isAbort: true }), client.track(), (s) => reports.push(s));
    expect(reports).toEqual([{ status: "ready", data: 3 }, { status: "access" }, { status: "error" }]);
  });

  test("region texts", () => {
    expect(regionText("loading", "runs")).toEqual(["Loading runs", "Please wait while Toolbox reads the current records."]);
    expect(regionText("access", "runs")).toEqual([
      "Access to runs is unavailable",
      "Your session may have expired or this area may not be available to your account.",
    ]);
    expect(regionText("error", "runs")).toEqual(["Could not load runs", "The service did not return a usable response. Try again."]);
    expect(regionText("empty", "runs")).toEqual(["No runs records", "This accessible source currently has no records."]);
    expect(isEmptyData({ items: [] })).toBe(true);
    expect(isEmptyData({ items: [1] })).toBe(false);
    expect(isEmptyData([])).toBe(true);
    expect(isEmptyData({ plugins: [] })).toBe(false);
  });
});

describe("hash routes", () => {
  test("parses areas and parameters; an unknown fragment keeps the current area", () => {
    expect(parseHash("")).toEqual(HOME_ROUTE);
    expect(parseHash("#")).toEqual(HOME_ROUTE);
    expect(parseHash("#catalog")).toEqual({ area: "catalog", params: {} });
    expect(parseHash("#documentation?extender=abc%20d&x=1")).toEqual({ area: "documentation", params: { extender: "abc d", x: "1" } });
    const current = parseHash("#performance?run=r1");
    expect(parseHash("#nowhere", current)).toBe(current);
    expect(parseHash("#main-content", current)).toBe(current);
    expect(parseHash("#Catalog", current)).toBe(current);
  });

  test("links round-trip through the parser", () => {
    const href = hashHref("documentation", { extender: "a&b=c" });
    expect(href).toBe("#documentation?extender=a%26b%3Dc");
    expect(parseHash(href)).toEqual({ area: "documentation", params: { extender: "a&b=c" } });
    expect(routeKey({ area: "home", params: {} })).toBe("#home");
  });
});

const CATALOG: Catalog = {
  plugins: [
    { id: "bun", name: "bun", version: "0.1.1", description: "Bun as the default JS/TS runtime", workflows: ["implement"] },
    { id: "code-desk", name: "code-desk", version: "", description: "Review desk", workflows: ["release"] },
  ],
  source_snapshot: "abc123",
  workflows: [
    { id: "implement", name: "Implement", guidance: "Use BUN for scripts.", plugins: ["bun"] },
    { id: "release", name: "Release", guidance: "Use its contract workflow before release.", plugins: ["code-desk"] },
  ],
};

describe("catalog and documentation logic", () => {
  test("search is a case-insensitive substring over id, name, description or guidance, workflows first", () => {
    expect(catalogMatches(CATALOG, "").map((m) => `${m.label}:${m.id}`)).toEqual([
      "Workflow:implement",
      "Workflow:release",
      "Plugin:bun",
      "Plugin:code-desk",
    ]);
    expect(catalogMatches(CATALOG, "bun").map((m) => `${m.label}:${m.id}:${m.text}`)).toEqual([
      "Workflow:implement:Use BUN for scripts.",
      "Plugin:bun:Bun as the default JS/TS runtime",
    ]);
    expect(catalogMatches(CATALOG, "REVIEW").map((m) => m.id)).toEqual(["code-desk"]);
    expect(catalogMatches(CATALOG, "nothing-here")).toEqual([]);
  });

  test("the catalog answer must have the documented shape", () => {
    expect(parseCatalog(JSON.parse(JSON.stringify(CATALOG)))).toEqual(CATALOG);
    expect(() => parseCatalog({ plugins: [] })).toThrow();
    expect(() => parseCatalog(null)).toThrow();
  });

  test("labels", () => {
    expect(distributionLabel({ slug: "core", members: ["a", "b"] })).toBe("core · 2 member record(s)");
    expect(orUnavailable("", "Role")).toBe("Role unavailable");
    expect(sourceSummary({ publisher_kind: "first-party", maintenance: "active" })).toBe("first-party · active");
    expect(fileLabel({ role: "entrypoint", relpath: "SKILL.md" })).toBe("entrypoint · SKILL.md");
  });
});

describe.skipIf(!HAS_POCKETBASE)("client against PocketBase", () => {
  let server: PbServer;
  let hooksDir: string;
  let extenderId = "";
  const email = "reader@example.test";
  const password = "ReaderPassword123";

  beforeAll(async () => {
    hooksDir = mkdtempSync(join(tmpdir(), "evals-ui-hooks-"));
    copyFileSync(join(REPO_ROOT, "pb_hooks", "toolbox_catalog.pb.js"), join(hooksDir, "toolbox_catalog.pb.js"));
    writeFileSync(join(hooksDir, "toolbox-catalog.json"), JSON.stringify(CATALOG, null, 2) + "\n");
    server = await startPocketBase({ hooksDir });
    const token = await server.superuserToken();
    const post = async (collection: string, body: unknown) => {
      const r = await api(server, "POST", `/api/collections/${collection}/records`, body, token);
      if (r.status !== 200) throw new Error(`${collection}: ${r.status} ${JSON.stringify(r.body)}`);
      return r.body.id as string;
    };
    await post("users", { email, password, passwordConfirm: password, verified: true });
    const source = await post("sources", { slug: "src", name: "Source One", url: "https://example.com/src", publisher_kind: "first-party", maintenance: "active" });
    extenderId = await post("extenders", { slug: "mermaid", name: "Mermaid", kind: "skill", body: "<img src=x onerror=alert(1)>", entry_file: "SKILL.md", source });
    await post("extenders", { slug: "zeta", name: "Zeta", kind: "agent", description: "maps" });
    await post("files", { extender: extenderId, relpath: "SKILL.md", role: "entrypoint", content: "# Mermaid" });
    await post("files", { extender: extenderId, relpath: "README.md", role: "doc", content: "read me" });
    await post("distributions", { slug: "core", kind: "bundle", members: [extenderId] });
  });

  afterAll(async () => {
    await server?.stop();
    rmSync(hooksDir, { recursive: true, force: true });
  });

  test("signs in against users, reads with named fields and escaped filters, and ends the session on a 401", async () => {
    const client = new ToolboxClient(server.url);
    expect(await client.signIn(email, "wrong-password")).toEqual(SIGN_IN_REJECTED);
    expect(client.signedIn).toBe(false);
    expect(await client.signIn(email, password)).toBeNull();
    expect(client.signedIn).toBe(true);
    expect(tokenExpiry(client.pb.authStore.token)!).toBeGreaterThan(Date.now());

    const signal = new AbortController().signal;
    const all = await client.list<Record<string, unknown>>({ collection: "extenders", fields: ["id", "slug", "kind"], sort: ["slug"] }, signal);
    expect(all.items.map((e) => e.slug)).toEqual(["mermaid", "zeta"]);
    expect(Object.keys(all.items[0]!).sort()).toEqual(["id", "kind", "slug"]);
    expect(all.perPage).toBe(25);

    const found = await client.list<{ slug: string }>(
      { collection: "extenders", fields: ["id", "slug"], sort: ["slug"], filter: extenderSearchFilter(client, "MAPS") },
      signal,
    );
    expect(found.items.map((e) => e.slug)).toEqual(["zeta"]);
    const injected = await client.list({ collection: "extenders", fields: ["id"], filter: extenderSearchFilter(client, '" || id != "') }, signal);
    expect(injected.totalItems).toBe(0);

    const files = await client.list<{ relpath: string }>(
      { collection: "files", fields: ["id", "extender", "role", "content", "relpath"], sort: ["relpath"], filter: client.filter("extender = {:e}", { e: extenderId }) },
      signal,
    );
    expect(files.items.map((f) => f.relpath)).toEqual(["README.md", "SKILL.md"]);
    const extender = await client.one<{ body: string; entry_file: string }>("extenders", extenderId, ["id", "body", "entry_file", "source"], signal);
    expect(extender.body).toBe("<img src=x onerror=alert(1)>");

    expect(parseCatalog(await client.get("/api/toolbox/catalog", signal))).toEqual(CATALOG);

    // A request cancelled by log out is aborted and its answer ignored.
    const reports: unknown[] = [];
    const pending = runLoad(client, (c, s) => c.list({ collection: "extenders", fields: ["id"] }, s), client.track(), (s) => reports.push(s));
    const saved = client.pb.authStore.token;
    client.signOut();
    await pending;
    expect(reports).toEqual([]);

    // A token the server refuses: the catalog route answers 401 and the session ends.
    client.pb.authStore.save(fakeJwt(Math.floor(Date.now() / 1000) + 3600));
    client.beginSession();
    expect(client.signedIn).toBe(true);
    const states: Load<unknown>[] = [];
    await runLoad(client, (c, s) => c.get("/api/toolbox/catalog", s), client.track(), (s) => states.push(s));
    expect(client.signedIn).toBe(false);
    expect(states).toEqual([]); // the session end cancelled the read; the shell is gone
    expect(saved).not.toBe("");
  });
});
