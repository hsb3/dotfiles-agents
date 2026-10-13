import { describe, expect, setDefaultTimeout, test } from "bun:test";
import { chmodSync, existsSync, mkdtempSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fixtureLedger } from "../src/fixture.ts";
import { buildRun, readLedger } from "../src/runs.ts";
import { HAS_POCKETBASE, pocketbaseBinary, REPO_ROOT } from "./pb.ts";

// Tests that spawn the CLI or a real PocketBase take seconds.
setDefaultTimeout(60000);

const HAS_UI = existsSync(join(REPO_ROOT, "ui/dist/index.html"));

function fixtureDirs(): string[] {
  return readdirSync(tmpdir()).filter((n) => n.startsWith("evals-fixture-"));
}

describe("fixture runs", () => {
  test("27 runs with measurement v1; runs 0 and 1 form a valid comparison pair", () => {
    const rows = readLedger(fixtureLedger(), []);
    expect(rows.length).toBe(27);
    const built = rows.map((r) => buildRun(r, { path: null, logPath: null }, null));
    for (const b of built) expect((b.body.measurement as any).version).toBe(1);
    const [a, b] = built as [any, any];
    for (const f of ["campaign", "candidate", "case", "harness", "model", "trial"]) expect(a.body[f]).toBe(b.body[f]);
    expect([a.body.config, a.body.passed, b.body.config, b.body.passed]).toEqual(["baseline", false, "with", true]);
    expect([a.body.measurement.execution.validity, b.body.measurement.execution.validity]).toEqual(["valid", "valid"]);
    expect(built.slice(2).every((x: any) => x.body.campaign === "toolbox-fixture")).toBe(true);
    expect(new Set(built.slice(2).map((x: any) => x.body.harness))).toEqual(new Set(["claude", "opencode", "codex"]));
    expect(built.some((x: any) => x.body.candidate === "fixture-<img src=x onerror=alert(1)>")).toBe(true);
  });
});

async function readUntil(stream: ReadableStream<Uint8Array>, marker: string, ms: number): Promise<string> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let text = "";
  const deadline = Date.now() + ms;
  while (!text.includes(marker) && Date.now() < deadline) {
    const chunk = await Promise.race([reader.read(), Bun.sleep(Math.max(0, deadline - Date.now())).then(() => null)]);
    if (!chunk || chunk.done) break;
    text += decoder.decode(chunk.value);
  }
  reader.releaseLock();
  return text;
}

describe.skipIf(!HAS_POCKETBASE || !HAS_UI)("evals fixture", () => {
  test("serves a seeded instance until SIGINT, then deletes everything", async () => {
    const before = new Set(fixtureDirs());
    const env: Record<string, string> = { PATH: process.env.PATH ?? "", HOME: process.env.HOME ?? "", TMPDIR: tmpdir() };
    const proc = Bun.spawn([process.execPath, join(REPO_ROOT, "src/cli.ts"), "fixture", "--pocketbase", pocketbaseBinary()!], { env, stdout: "pipe", stderr: "pipe" });
    const out = await readUntil(proc.stdout, "deleted on exit.", 30000);
    const lines = out.trim().split("\n");
    expect(lines.length).toBe(4);
    const url = lines[0]!.replace(/^URL=/, "");
    expect(url).toMatch(/^http:\/\/127\.0\.0\.1:\d+$/);
    expect(lines.slice(1)).toEqual(["EMAIL=fixture-user@example.test", "PASSWORD=FixtureUserPassword123", "Fixture runs until Ctrl-C; all data is deleted on exit."]);
    const created = fixtureDirs().filter((d) => !before.has(d));
    expect(created.length).toBe(1);

    const auth = await fetch(`${url}/api/collections/users/auth-with-password`, {
      method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ identity: "fixture-user@example.test", password: "FixtureUserPassword123" }),
    });
    expect(auth.status).toBe(200);
    const token = ((await auth.json()) as any).token;
    const get = async (path: string) => (await (await fetch(`${url}${path}`, { headers: { authorization: token } })).json()) as any;
    const count = async (c: string, filter = "") => (await get(`/api/collections/${c}/records?perPage=1${filter ? `&filter=${encodeURIComponent(filter)}` : ""}`)).totalItems;
    expect(await count("runs")).toBe(27);
    expect(await count("runs", 'campaign = "ui-fixture-campaign"')).toBe(2);
    expect(await count("extenders", 'slug = "ui-fixture-primitive"')).toBe(1);
    expect(await count("files")).toBe(3);
    expect(await count("distributions", 'slug = "ui-fixture-distribution" && kind = "plugin"')).toBe(1);
    expect(await count("eval_runs", 'slug = "ui-fixture-evaluation" && status = "running"')).toBe(1);
    expect(await count("eval_responses")).toBe(1);
    expect(await count("assessments", 'verdict = "present" && score = 1')).toBe(1);
    expect(await count("job_coverage", 'status = "covered"')).toBe(1);
    expect(await count("run_events")).toBe(2);
    expect(await count("tool_calls")).toBe(2);
    const [art] = (await get("/api/collections/artifacts/records")).items;
    expect([art.kind, art.mime]).toEqual(["tool_output", "text/plain"]);
    expect((await fetch(`${url}/api/files/artifacts/${art.id}/${art.blob}`)).status).not.toBe(200);
    const fileToken = ((await (await fetch(`${url}/api/files/token`, { method: "POST", headers: { authorization: token } })).json()) as any).token;
    expect(await (await fetch(`${url}/api/files/artifacts/${art.id}/${art.blob}?token=${fileToken}`)).text()).toBe("fixture protected evidence\n");
    expect((await fetch(`${url}/api/toolbox/catalog`)).status).toBe(401);
    expect((await get("/api/toolbox/catalog")).workflows.length).toBeGreaterThan(0);
    expect((await fetch(`${url}/`)).status).toBe(200);

    proc.kill("SIGINT");
    expect(await proc.exited).toBe(0);
    expect(existsSync(join(tmpdir(), created[0]!))).toBe(false);
    await expect(fetch(`${url}/api/health`)).rejects.toThrow();
  });

  test("exits 1 when the server never answers, leaving nothing behind", async () => {
    const dir = mkdtempSync(join(tmpdir(), "evals-fake-pb-"));
    const fake = join(dir, "pocketbase");
    writeFileSync(fake, "#!/bin/sh\nexec sleep 30\n");
    chmodSync(fake, 0o755);
    const before = new Set(fixtureDirs());
    const proc = Bun.spawn([process.execPath, join(REPO_ROOT, "src/cli.ts"), "fixture", "--pocketbase", fake], { stdout: "pipe", stderr: "pipe" });
    expect(await proc.exited).toBe(1);
    expect(await new Response(proc.stderr).text()).toContain("did not answer");
    expect(fixtureDirs().filter((d) => !before.has(d))).toEqual([]);
    const missing = Bun.spawn([process.execPath, join(REPO_ROOT, "src/cli.ts"), "fixture", "--pocketbase", join(dir, "nope")], { stdout: "pipe", stderr: "pipe" });
    expect(await missing.exited).toBe(1);
    rmSync(dir, { recursive: true, force: true });
  });
});
