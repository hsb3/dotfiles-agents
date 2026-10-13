import { describe, expect, test, setDefaultTimeout } from "bun:test";
import { runCli } from "./cli.ts";

// Tests that spawn the CLI or a real PocketBase take seconds.
setDefaultTimeout(60000);

const COMMANDS = ["ingest", "load-eval-run", "load-verdicts", "compare-verdicts", "load-curation", "load-runs", "report", "package", "fixture"];

describe("usage and errors", () => {
  test("--help on every command prints its usage and exits 0", async () => {
    for (const name of COMMANDS) {
      const r = await runCli([name, "--help"]);
      expect(r.code, name).toBe(0);
      expect(r.stdout, name).toContain(`Usage: evals ${name}`);
    }
    const top = await runCli(["--help"]);
    expect(top.code).toBe(0);
    expect(top.stdout).toContain("Usage: evals <command>");
  });

  test("no subcommand or an unknown one prints usage to stderr and exits 1", async () => {
    for (const args of [[], ["bogus"]]) {
      const r = await runCli(args);
      expect(r.code).toBe(1);
      expect(r.stdout).toBe("");
      expect(r.stderr).toContain("Usage: evals <command>");
    }
  });

  test("an unknown flag, a missing required flag or both modes is a usage error", async () => {
    const cases = [
      ["ingest", "--source-root", "x", "--bogus"],
      ["ingest"],
      ["ingest", "--source-root", "x", "--parse-only", "--dry-run"],
      ["load-runs", "--runs-dir", "x"],
      ["load-curation"],
      ["load-curation", "a.json", "b.json"],
      ["compare-verdicts", "--left", "a.json"],
      ["report", "--out"],
      ["package", "--source-root", "x"],
      ["fixture", "--parse-only"],
    ];
    for (const args of cases) {
      const r = await runCli(args);
      expect(r.code, args.join(" ")).toBe(1);
      expect(r.stderr, args.join(" ")).toContain(`evals ${args[0]}: `);
      expect(r.stderr, args.join(" ")).toContain(`Usage: evals ${args[0]}`);
    }
  });
});
