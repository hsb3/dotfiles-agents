import { afterEach, beforeEach, expect, test } from "bun:test";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { installStub, sandbox, stubCalls } from "./helpers/stubs.ts";

const SCRIPT = resolve(import.meta.dir, "..", "scripts", "launchd.sh");
const PKG = resolve(import.meta.dir, "..");
const LABEL = "com.hsb3.agent-harness.campaign";
const UID = String(process.getuid?.() ?? "");

let box: ReturnType<typeof sandbox>;
let home: string;
let env: Record<string, string>;
beforeEach(() => {
  box = sandbox();
  home = join(box.root, "home");
  mkdirSync(home);
  env = { HOME: home, PATH: `${box.bin}:/usr/bin:/bin` };
});
afterEach(() => box.cleanup());

function sh(args: string[], extraEnv: Record<string, string> = {}) {
  const r = Bun.spawnSync(["/bin/sh", SCRIPT, ...args], { env: { ...env, ...extraEnv }, stdin: "ignore" });
  return { code: r.exitCode, stdout: r.stdout.toString(), stderr: r.stderr.toString() };
}

test("the script parses as POSIX sh", () => {
  expect(Bun.spawnSync(["sh", "-n", SCRIPT]).exitCode).toBe(0);
});

test("install writes the plist, reloads the agent and prints the kickstart step", () => {
  installStub(box.bin, "launchctl", [{ prefix: ["bootout"], exit: 3 }, {}]);
  const cases = join(box.root, "my cases & more");
  const root = join(box.root, "root");
  mkdirSync(cases);
  mkdirSync(root);
  const r = sh(["install", cases, root]);
  expect(r.code).toBe(0);
  const plist = join(home, "Library/LaunchAgents", `${LABEL}.plist`);
  const xml = readFileSync(plist, "utf8");
  expect(xml).toContain(`<key>Label</key>\n  <string>${LABEL}</string>`);
  expect(xml).toContain(
    `<array>\n    <string>/bin/sh</string>\n    <string>${PKG}/scripts/launchd.sh</string>\n    <string>run</string>\n    <string>${join(box.root, "my cases &amp; more")}</string>\n    <string>${root}</string>\n  </array>`,
  );
  expect(xml).toContain(`<key>WorkingDirectory</key>\n  <string>${PKG}</string>`);
  expect(xml).toContain("<key>Weekday</key>\n    <integer>1</integer>\n    <key>Hour</key>\n    <integer>9</integer>\n    <key>Minute</key>\n    <integer>0</integer>");
  expect(xml).toContain("<key>RunAtLoad</key>\n  <false/>");
  expect(xml).toContain(`<string>${home}/Library/Logs/agent-harness-campaign.out.log</string>`);
  expect(xml).toContain(`<string>${home}/Library/Logs/agent-harness-campaign.err.log</string>`);
  if (process.platform === "darwin") expect(Bun.spawnSync(["plutil", "-lint", plist]).exitCode).toBe(0); // plutil is macOS-only
  expect(stubCalls(box.bin, "launchctl").map((c) => c.argv)).toEqual([
    ["bootout", `gui/${UID}/${LABEL}`],
    ["bootstrap", `gui/${UID}`, plist],
  ]);
  expect(r.stdout).toContain(`launchctl kickstart -k gui/${UID}/${LABEL}`);
});

test("install needs two existing directories", () => {
  installStub(box.bin, "launchctl", [{}]);
  expect(sh(["install", join(box.root, "missing"), box.root]).code).toBe(2);
  expect(sh(["install"]).code).toBe(2);
  expect(stubCalls(box.bin, "launchctl")).toEqual([]);
});

test("uninstall boots the agent out and deletes the plist", () => {
  installStub(box.bin, "launchctl", [{ exit: 5 }]);
  const plist = join(home, "Library/LaunchAgents", `${LABEL}.plist`);
  mkdirSync(join(plist, ".."), { recursive: true });
  writeFileSync(plist, "x");
  expect(sh(["uninstall"]).code).toBe(0);
  expect(existsSync(plist)).toBe(false);
  expect(stubCalls(box.bin, "launchctl").map((c) => c.argv)).toEqual([["bootout", `gui/${UID}/${LABEL}`]]);
});

test("status prints the state, last exit and next fire lines, or that the agent is not loaded", () => {
  installStub(box.bin, "launchctl", [
    { prefix: ["print"], stdout: `gui/${UID}/${LABEL} = {\n\tactive count = 0\n\tstate = not running\n\tprogram = /bin/sh\n\tlast exit code = 0\n\tnext fire = Mon Oct 19 09:00:00 2026\n}\n` },
  ]);
  expect(sh(["status"])).toEqual({ code: 0, stdout: "state = not running\nlast exit code = 0\nnext fire = Mon Oct 19 09:00:00 2026\n", stderr: "" });
  installStub(box.bin, "launchctl", [{ prefix: ["print"], stderr: "Could not find service", exit: 113 }]);
  expect(sh(["status"]).stdout).toBe("agent not loaded\n");
});

test("run fills unset keys from secret without printing them, runs the campaign with bun, notifies and exits with its code", () => {
  // Stubs in $HOME/.bun/bin and $HOME/.local/bin come first on the PATH the script builds.
  const bunBin = join(home, ".bun", "bin");
  const localBin = join(home, ".local", "bin");
  installStub(bunBin, "bun", [{ stdout: "campaign output\n", exit: 1 }]);
  installStub(localBin, "secret", [{ prefix: ["get", "ANTHROPIC_API_KEY"], stdout: "sk-ant-secret\n" }, { stdout: "sk-openai-secret" }]);
  installStub(localBin, "osascript", [{ exit: 1 }]);
  const r = sh(["run", "/cases", "/root"], { OPENAI_API_KEY: "already-set" });
  expect(r.code).toBe(1);
  expect(r.stdout).toBe("campaign output\n");
  expect(r.stdout + r.stderr).not.toContain("sk-ant-secret");
  const [call] = stubCalls(bunBin, "bun");
  expect(call!.argv).toEqual([`${PKG}/src/cli.ts`, "campaign", "--cases-dir", "/cases", "--candidates-root", "/root"]);
  expect(call!.env.ANTHROPIC_API_KEY).toBe("sk-ant-secret");
  expect(call!.env.OPENAI_API_KEY).toBe("already-set");
  expect(call!.env.PATH!.startsWith(`${home}/.bun/bin:${home}/.local/bin:/opt/homebrew/bin:/usr/local/bin:`)).toBe(true);
  expect(stubCalls(localBin, "secret").map((c) => c.argv)).toEqual([["get", "ANTHROPIC_API_KEY"]]);
  expect(stubCalls(localBin, "osascript")[0]!.argv.join(" ")).toContain("agent-harness campaign: failed");

  installStub(bunBin, "bun", [{ exit: 0 }]);
  expect(sh(["run", "/cases", "/root"]).code).toBe(0);
  expect(stubCalls(localBin, "osascript")[1]!.argv.join(" ")).toContain("agent-harness campaign: ok");
});
