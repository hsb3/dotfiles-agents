import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import {
  applyPlans, CommandError, coerceJson, connect, diff, fetchAll, formatParseOnly, formatPlan, sameValue, type Connection, type Rec,
} from "../src/store.ts";
import { HAS_POCKETBASE, startPocketBase, type PbServer } from "./pb.ts";

describe("json coercion", () => {
  test("follows the spec examples", () => {
    expect(coerceJson("7853\n")).toBe(7853);
    expect(coerceJson("[1, 2]")).toEqual([1, 2]);
    expect(coerceJson('"x"')).toBe("x");
    expect(coerceJson('{"a":1} ')).toEqual({ a: 1 });
    expect(coerceJson("     266")).toBe("     266");
    expect(coerceJson("abc")).toBe("abc");
    expect(coerceJson(' {"a":1}')).toBe(' {"a":1}');
    expect(coerceJson("")).toBe("");
    expect(coerceJson("true")).toBe(true);
    expect(coerceJson("nope")).toBe("nope");
    expect(coerceJson({ a: "1" })).toEqual({ a: "1" });
  });
});

describe("record comparison", () => {
  test("text, select and relation treat missing, null and empty as equal", () => {
    expect(sameValue("extenders", "description", undefined, "")).toBe(true);
    expect(sameValue("extenders", "description", null, "")).toBe(true);
    expect(sameValue("extenders", "source", "", null)).toBe(true);
    expect(sameValue("extenders", "description", "a", "b")).toBe(false);
  });
  test("numbers numerically, booleans strictly, lists in order", () => {
    expect(sameValue("extenders", "file_count", 2, 2.0)).toBe(true);
    expect(sameValue("extenders", "file_count", 2, 3)).toBe(false);
    expect(sameValue("extenders", "retired", false, false)).toBe(true);
    expect(sameValue("extenders", "retired", true, false)).toBe(false);
    expect(sameValue("distributions", "members", ["a", "b"], ["a", "b"])).toBe(true);
    expect(sameValue("distributions", "members", ["a", "b"], ["b", "a"])).toBe(false);
    expect(sameValue("distributions", "members", [], null)).toBe(true);
  });
  test("json canonically after coercion", () => {
    expect(sameValue("extenders", "frontmatter", { b: 1, a: [1, 2] }, { a: [1, 2], b: 1 })).toBe(true);
    expect(sameValue("runs", "checks", "[1, 2]", [1, 2])).toBe(true);
    expect(sameValue("extenders", "frontmatter", { a: 1 }, { a: 2 })).toBe(false);
  });
});

describe("plans", () => {
  const existing: Rec[] = [
    { id: "aaaaaaaaaaaaaaa", slug: "same", name: "Same", kind: "principles" },
    { id: "bbbbbbbbbbbbbbb", slug: "changed", name: "Old", kind: "principles" },
    { id: "ccccccccccccccc", slug: "untouched", name: "U", kind: "principles", notes: "kept" },
  ];
  const desired = [
    { key: "same", body: { slug: "same", name: "Same", kind: "principles" } },
    { key: "changed", body: { slug: "changed", name: "New", kind: "principles" } },
    { key: "new", body: { slug: "new", name: "New", kind: "principles" } },
  ];
  test("diff creates, updates and leaves unsent fields and records alone", () => {
    const plan = diff("frameworks", desired, existing, (r) => String(r.slug));
    expect(plan.creates.map((c) => c.key)).toEqual(["new"]);
    expect(plan.creates[0]!.id).toMatch(/^[a-z0-9]{15}$/);
    expect(plan.updates.map((u) => [u.id, u.key])).toEqual([["bbbbbbbbbbbbbbb", "changed"]]);
    expect(plan.unchanged).toBe(1);
    expect(plan.ids.get("untouched")).toBe("ccccccccccccccc");
    expect(plan.ids.get("new")).toBe(plan.creates[0]!.id);
  });
  test("plan block", () => {
    const a = diff("frameworks", desired, existing, (r) => String(r.slug));
    const files = diff("files", [], [], () => "", { showDelete: true });
    const ext = diff("extenders", [], [], () => "", { showRetire: true });
    expect(formatPlan([a, files, ext], "dry-run")).toEqual([
      "[dry-run] plan (create / update / unchanged):",
      "  frameworks 1 create / 1 update / 1 unchanged",
      "  files 0 create / 0 update / 0 unchanged / 0 delete",
      "  extenders 0 create / 0 update / 0 unchanged / 0 retire",
      "  no writes made",
    ]);
    expect(formatPlan([a], "applied")).toEqual(["applied (create / update / unchanged):", "  frameworks 1 create / 1 update / 1 unchanged"]);
    expect(formatParseOnly([["runs", 3]], ["w1"])).toEqual(["[parse-only] planned records (no DB connection):", "  runs: 3", "warnings (1):", "  - w1"]);
  });
});

describe("connection", () => {
  test("missing credentials name the variables", async () => {
    await expect(connect({})).rejects.toThrow("missing environment variables PB_ADMIN_EMAIL and PB_ADMIN_PASSWORD");
    await expect(connect({ PB_ADMIN_EMAIL: "a@b.c" })).rejects.toThrow("missing environment variable PB_ADMIN_PASSWORD");
  });

  test("a 429 on authentication is retried after 1.5 s", async () => {
    let calls = 0;
    const stub = Bun.serve({
      port: 0,
      hostname: "127.0.0.1",
      fetch(req) {
        if (new URL(req.url).pathname === "/api/collections/_superusers/auth-with-password") {
          calls++;
          if (calls <= 2) return Response.json({ status: 429, message: "Too Many Requests.", data: {} }, { status: 429 });
          return Response.json({ token: "t", record: { id: "x", collectionName: "_superusers" } });
        }
        return new Response("no", { status: 404 });
      },
    });
    const started = Date.now();
    const conn = await connect({ PB_URL: `http://127.0.0.1:${stub.port}`, PB_ADMIN_EMAIL: "a@b.c", PB_ADMIN_PASSWORD: "secret-pw" });
    expect(conn.pb.authStore.token).toBe("t");
    expect(calls).toBe(3);
    expect(Date.now() - started).toBeGreaterThanOrEqual(2900);
    calls = -10; // always 429 now
    const err = await connect({ PB_URL: `http://127.0.0.1:${stub.port}`, PB_ADMIN_EMAIL: "a@b.c", PB_ADMIN_PASSWORD: "secret-pw" }).catch((e) => e);
    stub.stop(true);
    expect(err).toBeInstanceOf(CommandError);
    expect(String(err.message)).not.toContain("secret-pw");
  }, 15000);
});

describe.skipIf(!HAS_POCKETBASE)("store against PocketBase", () => {
  let server: PbServer;
  let conn: Connection;
  beforeAll(async () => {
    server = await startPocketBase();
    conn = await connect({ PB_URL: server.url, PB_ADMIN_EMAIL: server.email, PB_ADMIN_PASSWORD: server.password });
  });
  afterAll(async () => {
    await server?.stop();
  });

  test("stores coerced json values as the spec says (0.40.x)", async () => {
    const values = ["7853\n", "[1, 2]", '"x"', '{"a":1} ', "     266", "abc", ' {"a":1}', ""];
    const rec = await conn.pb.collection("runs").create({ harness: "claude", candidate: "c", case: "json", trial: 0 });
    const stored: unknown[] = [];
    for (const v of values) {
      const r = await conn.pb.collection("runs").update(rec.id, { checks: v });
      stored.push(r.checks);
    }
    expect(stored).toEqual(values.map(coerceJson));
  });

  test("applies a plan, converges, and names the key of a failed write", async () => {
    const desired = [
      { key: "fw-a", body: { slug: "fw-a", name: "A", kind: "principles", applies_to: ["skill", "any"] } },
      { key: "fw-b", body: { slug: "fw-b", name: "B", kind: "rule-that-is-not-valid" } },
    ];
    const first = diff("frameworks", desired.slice(0, 1), await fetchAll(conn, "frameworks"), (r) => String(r.slug));
    await applyPlans(conn, [first]);
    const again = diff("frameworks", desired.slice(0, 1), await fetchAll(conn, "frameworks"), (r) => String(r.slug));
    expect([again.creates.length, again.updates.length, again.unchanged]).toEqual([0, 0, 1]);
    const bad = diff("frameworks", desired, await fetchAll(conn, "frameworks"), (r) => String(r.slug));
    const err = await applyPlans(conn, [bad]).catch((e) => e);
    expect(err).toBeInstanceOf(CommandError);
    expect(err.message).toContain("write failed in frameworks for fw-b: ");
    expect(err.message).toContain("kind");
  });
});
