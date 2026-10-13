import { afterEach, beforeEach, expect, test } from "bun:test";
import { writeFileSync } from "node:fs";
import { join } from "node:path";
import type { LedgerRow } from "../src/ledger.ts";
import { formatReport, report } from "../src/report.ts";
import { sandbox } from "./helpers/stubs.ts";

let box: ReturnType<typeof sandbox>;
beforeEach(() => {
  box = sandbox();
});
afterEach(() => box.cleanup());

// Three rows whose mean and sample stdev are exactly (mean, sd).
const spread = (mean: number, sd: number) => [mean - sd, mean, mean + sd];

function rows(harness: string, model: string, config: string, passes: boolean[], cost: number[] | null, ms: number[], campaign = "weekly-20261019"): LedgerRow[] {
  return passes.map((passed, trial) => ({
    campaign, harness, model, candidate: "mermaid", case: "add-architecture-diagram", config, trial, passed,
    cost_usd: cost ? cost[trial]! : null, duration_ms: ms[trial]!,
  }));
}

const SPEC_EXAMPLE = `
mermaid — 13 trial row(s)
campaign         harness  model              case                      config    n  pass  p@n  p^n  cost           ms
---------------------------------------------------------------------------------------------------------------------
weekly-20261019  claude   claude-sonnet-4-5  add-architecture-diagram  baseline  3  0.33  Y    n    0.1520±0.0101  40112±3120
weekly-20261019  claude   claude-sonnet-4-5  add-architecture-diagram  with      3  1.00  Y    Y    0.1977±0.0123  44168±2010
weekly-20261019  codex    gpt-6.1-sol        add-architecture-diagram  baseline  3  0.67  Y    n    -              61234±5120
weekly-20261019  codex    gpt-6.1-sol        add-architecture-diagram  with      3  0.67  Y    n    -              58810±4410
delta (with - baseline) [weekly-20261019/claude/claude-sonnet-4-5] add-architecture-diagram: +0.67
delta (with - baseline) [weekly-20261019/codex/gpt-6.1-sol] add-architecture-diagram: +0.00

1 unsupported/skip row(s):
  ∅ [weekly-20261019] opencode/claude-sonnet-4-5 add-architecture-diagram with: unsupported: opencode cannot host kind=plugin`;

const skipRow: LedgerRow = {
  campaign: "weekly-20261019", harness: "opencode", model: "claude-sonnet-4-5", candidate: "mermaid", case: "add-architecture-diagram",
  config: "with", trial: 0, passed: null, error: "unsupported: opencode cannot host kind=plugin",
};

test("reproduces the spec example", () => {
  const all = [
    ...rows("codex", "gpt-6.1-sol", "with", [true, false, true], null, spread(58810, 4410)),
    skipRow,
    ...rows("claude", "claude-sonnet-4-5", "with", [true, true, true], spread(0.1977, 0.0123), spread(44168, 2010)),
    ...rows("claude", "claude-sonnet-4-5", "baseline", [false, true, false], spread(0.152, 0.0101), spread(40112, 3120)),
    ...rows("codex", "gpt-6.1-sol", "baseline", [true, true, false], null, spread(61234, 5120)),
  ];
  expect(formatReport("mermaid", all)).toBe(SPEC_EXAMPLE);
});

test("an empty campaign prints -, drops the campaign from deltas and skip lines; negative deltas keep their sign", () => {
  const all = [
    ...rows("claude", "m", "with", [false], [0.5], [100], ""),
    ...rows("claude", "m", "baseline", [true], null, [200], ""),
    { ...skipRow, campaign: "", error: "unsupported: opencode cannot host kind=plugin" },
  ];
  const lines = formatReport("mermaid", all).split("\n");
  expect(lines[4]).toBe("-         claude   m      add-architecture-diagram  baseline  1  1.00  Y    Y    -              200±0");
  expect(lines[5]).toBe("-         claude   m      add-architecture-diagram  with      1  0.00  n    n    0.5000±0.0000  100±0");
  expect(lines[6]).toBe("delta (with - baseline) [claude/m] add-architecture-diagram: -1.00");
  expect(lines.at(-1)).toBe("  ∅ opencode/claude-sonnet-4-5 add-architecture-diagram with: unsupported: opencode cannot host kind=plugin");
});

test("edge forms: no rows, and rows without a pass signal", () => {
  expect(formatReport("x", [])).toBe("no result rows for x");
  expect(formatReport("mermaid", [skipRow])).toBe(
    "mermaid — 1 row(s), none with a pass signal\n\n1 unsupported/skip row(s):\n  ∅ [weekly-20261019] opencode/claude-sonnet-4-5 add-architecture-diagram with: unsupported: opencode cannot host kind=plugin",
  );
});

test("report reads only the candidate's rows from the ledger", () => {
  const path = join(box.root, "results.jsonl");
  const mine = rows("claude", "m", "with", [true], [0.1], [5]);
  writeFileSync(path, [JSON.stringify(mine[0]), JSON.stringify({ ...mine[0], candidate: "other" }), "junk"].join("\n"));
  expect(report("mermaid", path).split("\n")[1]).toBe("mermaid — 1 trial row(s)");
  expect(report("nobody", join(box.root, "missing.jsonl"))).toBe("no result rows for nobody");
});
