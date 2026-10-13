import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import { symlink } from "node:fs/promises";
import { join } from "node:path";
import { PortTakenError, resolveRequest, startServer } from "../src/server.ts";
import { tempDir, writeTree } from "./fixture.ts";

let dir: string;
let output: string;
let server: Bun.Server<undefined>;

beforeAll(async () => {
  dir = await tempDir();
  output = join(dir, "out");
  await writeTree(dir, {
    "secret.txt": "outside the output folder",
    "out/index.html": "home",
    "out/README.html": "readme",
    "out/docs/My Notes.html": "notes",
    "out/docs/decisions/index.html": "decisions index",
    "out/assets/site.css": "body {}",
  });
  await symlink(join(dir, "secret.txt"), join(output, "leak.html"));
  server = startServer({ output, base: "/dotfiles-agents", port: 0 });
});

afterAll(() => server.stop(true));

async function get(path: string, method = "GET") {
  const response = await fetch(`http://127.0.0.1:${server.port}${path}`, { method });
  return { status: response.status, body: method === "HEAD" ? "" : await response.text(), type: response.headers.get("content-type") };
}

describe("routing under the base path", () => {
  test("<base>/ and paths ending in / get that folder's index.html", async () => {
    expect(await get("/dotfiles-agents/")).toMatchObject({ status: 200, body: "home" });
    expect(await get("/dotfiles-agents/docs/decisions/")).toMatchObject({ status: 200, body: "decisions index" });
  });

  test("other paths under the base get the file, percent-decoded, with its type", async () => {
    expect(await get("/dotfiles-agents/README.html")).toMatchObject({ status: 200, body: "readme" });
    expect(await get("/dotfiles-agents/docs/My%20Notes.html")).toMatchObject({ status: 200, body: "notes" });
    expect((await get("/dotfiles-agents/assets/site.css")).type).toStartWith("text/css");
    expect(await get("/dotfiles-agents/README.html", "HEAD")).toMatchObject({ status: 200 });
  });

  test("everything else is 404", async () => {
    for (const path of [
      "/",
      "/dotfiles-agents",
      "/other/index.html",
      "/dotfiles-agentsX/index.html",
      "/dotfiles-agents/missing.html",
      "/dotfiles-agents/docs/",
      "/dotfiles-agents/docs",
      "/dotfiles-agents/%2e%2e/secret.txt",
      "/dotfiles-agents/..%2fsecret.txt",
      "/dotfiles-agents/docs%2f..%2f..%2fsecret.txt",
      "/dotfiles-agents/leak.html",
      "/dotfiles-agents/%E0%A4%A",
    ]) {
      expect({ path, status: (await get(path)).status }).toEqual({ path, status: 404 });
    }
  });

  test("other methods are refused", async () => {
    expect((await get("/dotfiles-agents/", "POST")).status).toBe(405);
  });
});

describe("resolveRequest", () => {
  test("dot segments that survive URL parsing are refused", async () => {
    expect(await resolveRequest(output, "/dotfiles-agents", "/dotfiles-agents/docs/../README.html")).toBeUndefined();
    expect(await resolveRequest(output, "/dotfiles-agents", "/dotfiles-agents//README.html")).toBeUndefined();
    expect(await resolveRequest(output, "/dotfiles-agents", "/dotfiles-agents/README.html")).toBe(join(output, "README.html"));
  });
});

test("a taken port is reported", () => {
  expect(() => startServer({ output, base: "/dotfiles-agents", port: server.port! })).toThrow(PortTakenError);
});
