import { afterEach, beforeEach, expect, test } from "bun:test";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { runProcess } from "../src/subprocess.ts";
import { installStub, sandbox, stubCalls, stubPath } from "./helpers/stubs.ts";

let box: ReturnType<typeof sandbox>;
beforeEach(() => {
  box = sandbox();
});
afterEach(() => box.cleanup());

const env = () => ({ PATH: stubPath(box.bin), MARKER: "m1" });

function alive(pid: number): boolean {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

test("runs a list-form argv by bare name and captures stdout, stderr and exit code", async () => {
  installStub(box.bin, "claude", [{ stream: "A2-claude-skill-trial.jsonl", stderr: "warn", exit: 3 }]);
  const r = await runProcess(["claude", "-p", "a prompt; with $(shell) chars"], { cwd: box.root, env: env(), timeoutSec: 10 });
  expect(r.exitCode).toBe(3);
  expect(r.timedOut).toBe(false);
  expect(r.notFound).toBe(false);
  expect(r.stdout).toBe(readFileSync(join(import.meta.dir, "fixtures/streams/A2-claude-skill-trial.jsonl"), "utf8"));
  expect(r.stderr).toBe("warn");
  const [call] = stubCalls(box.bin, "claude");
  expect(call!.argv).toEqual(["-p", "a prompt; with $(shell) chars"]);
  expect(call!.env.MARKER).toBe("m1");
});

test("stdin is /dev/null and the child runs in its own process group", async () => {
  const r = await runProcess(
    [process.execPath, "-e", "const s = await Bun.stdin.text(); let leader = true; try { process.kill(-process.pid, 0); } catch { leader = false; } console.log(JSON.stringify({ s, leader }))"],
    { cwd: box.root, env: { PATH: process.env.PATH ?? "" }, timeoutSec: 20 },
  );
  const info = JSON.parse(r.stdout);
  expect(info.s).toBe("");
  // A process group whose id is the child's pid exists only when it leads its own group.
  expect(info.leader).toBe(true);
});

test("a missing executable is reported as notFound with exit -1", async () => {
  const r = await runProcess(["codex", "exec"], { cwd: box.root, env: { PATH: box.bin }, timeoutSec: 5 });
  expect(r).toMatchObject({ notFound: true, exitCode: -1, timedOut: false, stdout: "" });
});

test("a timeout SIGKILLs the whole process group and keeps the partial stdout", async () => {
  const pidFile = join(box.root, "sleeper.pid");
  installStub(box.bin, "opencode", [{ stdout: "partial line\n", sleeperPidFile: pidFile }]);
  const r = await runProcess(["opencode", "run"], { cwd: box.root, env: env(), timeoutSec: 2 });
  expect(r.timedOut).toBe(true);
  expect(r.exitCode).toBe(-1);
  expect(r.stdout).toBe("partial line\n");
  expect(existsSync(pidFile)).toBe(true);
  const sleeper = Number(readFileSync(pidFile, "utf8"));
  // The orphaned descendant is reaped by init shortly after the kill.
  for (let i = 0; i < 50 && alive(sleeper); i++) await Bun.sleep(100);
  expect(alive(sleeper)).toBe(false);
}, 20000);
