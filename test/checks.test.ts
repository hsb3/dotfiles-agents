import { afterEach, beforeEach, expect, test } from "bun:test";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { runChecks } from "../src/checks.ts";
import { installStub, sandbox, stubCalls } from "./helpers/stubs.ts";

let box: ReturnType<typeof sandbox>;
let ws: string;
beforeEach(() => {
  box = sandbox();
  ws = join(box.root, "ws");
  mkdirSync(ws);
});
afterEach(() => box.cleanup());

const SMOKE_CHECK = join(import.meta.dir, "..", "cases/smoke-echo/create-file/check.py");
const TEMPLATE_CHECK = join(import.meta.dir, "..", "cases/_template/rename-this-case/check.py");
const realPython = Bun.which("python3");

test.skipIf(!realPython)("the shipped smoke-echo check.py passes on HELLO.txt and fails without it", async () => {
  const env = { PATH: process.env.PATH ?? "" };
  expect((await runChecks(SMOKE_CHECK, ws, env)).map((c) => c.passed)).toEqual([false, false]);
  writeFileSync(join(ws, "HELLO.txt"), "harness-ok\n");
  expect(await runChecks(SMOKE_CHECK, ws, env)).toEqual([
    { id: "hello-file-exists", passed: true, evidence: "HELLO.txt present" },
    { id: "hello-content", passed: true, evidence: "HELLO.txt content='harness-ok' (want 'harness-ok')" },
  ]);
});

test.skipIf(!realPython)("the shipped template check.py runs", async () => {
  const checks = await runChecks(TEMPLATE_CHECK, ws, { PATH: process.env.PATH ?? "" });
  expect(checks).toEqual([{ id: "c1-file-exists", passed: false, evidence: "README.md missing in workspace" }]);
});

test("check.py runs as python3 <check> with cwd = the workspace; exit code is ignored", async () => {
  installStub(box.bin, "python3", [{ stdout: '[{"id":"c1","passed":true,"evidence":"ok"}]', exit: 3 }]);
  expect(await runChecks("/cases/x/check.py", ws, { PATH: box.bin })).toEqual([{ id: "c1", passed: true, evidence: "ok" }]);
  const [call] = stubCalls(box.bin, "python3");
  expect(call!.argv).toEqual(["/cases/x/check.py"]);
  expect(call!.cwd).toEndWith("/ws");
});

test("every failure becomes one check-error entry", async () => {
  const err = (reason: string) => [{ id: "check.py", passed: false, evidence: `check-error: ${reason}` }];
  expect(await runChecks("c.py", ws, { PATH: box.bin })).toEqual(err("executable not found: python3"));
  installStub(box.bin, "python3", [{ stdout: "Traceback ..." }]);
  expect(await runChecks("c.py", ws, { PATH: box.bin })).toEqual(err("stdout is not JSON"));
  installStub(box.bin, "python3", [{ stdout: '{"id":"c1"}' }]);
  expect(await runChecks("c.py", ws, { PATH: box.bin })).toEqual(err("stdout is not a JSON array"));
  installStub(box.bin, "python3", [{ stdout: '[{"id":"c1"}]' }]);
  expect(await runChecks("c.py", ws, { PATH: box.bin })).toEqual(err("entries must be {id, passed, evidence}"));
});
