// The candidate report: pass rates per (campaign, harness, model, case, config)
// cell over every ledger row of the candidate, the with − baseline deltas, and
// the skip rows.
import { readRows, type LedgerRow } from "./ledger.ts";

interface Cell {
  campaign: string;
  harness: string;
  model: string;
  case: string;
  config: string;
  rows: LedgerRow[];
}

const HEADER = ["campaign", "harness", "model", "case", "config", "n", "pass", "p@n", "p^n", "cost", "ms"];

function compareStrings(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

function cellKey(r: LedgerRow): string[] {
  return [r.campaign ?? "", r.harness ?? "", r.model ?? "", r.case ?? "", r.config ?? ""];
}

function meanStdev(values: number[]): [number, number] | null {
  if (values.length === 0) return null;
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  if (values.length === 1) return [mean, 0];
  const variance = values.reduce((a, v) => a + (v - mean) ** 2, 0) / (values.length - 1);
  return [mean, Math.sqrt(variance)];
}

function numbers(rows: LedgerRow[], pick: (r: LedgerRow) => unknown): number[] {
  return rows.map(pick).filter((v): v is number => typeof v === "number" && Number.isFinite(v));
}

function passRate(cell: Cell): number {
  return cell.rows.filter((r) => r.passed === true).length / cell.rows.length;
}

function cellLine(cell: Cell): string[] {
  const cost = meanStdev(numbers(cell.rows, (r) => r.cost_usd));
  const ms = meanStdev(numbers(cell.rows, (r) => r.duration_ms));
  return [
    cell.campaign || "-",
    cell.harness,
    cell.model,
    cell.case,
    cell.config,
    String(cell.rows.length),
    passRate(cell).toFixed(2),
    cell.rows.some((r) => r.passed === true) ? "Y" : "n",
    cell.rows.every((r) => r.passed === true) ? "Y" : "n",
    cost ? `${cost[0].toFixed(4)}±${cost[1].toFixed(4)}` : "-",
    ms ? `${Math.round(ms[0])}±${Math.round(ms[1])}` : "-",
  ];
}

function table(lines: string[][]): string[] {
  const widths = HEADER.map((_, i) => Math.max(...lines.map((l) => l[i]!.length)));
  const render = (l: string[]) => l.map((v, i) => v.padEnd(widths[i]!)).join("  ").trimEnd();
  const header = render(lines[0]!);
  return [header, "-".repeat(header.length), ...lines.slice(1).map(render)];
}

function skipSection(skips: LedgerRow[]): string[] {
  if (skips.length === 0) return [];
  return [
    "",
    `${skips.length} unsupported/skip row(s):`,
    ...skips.map((r) => `  ∅ ${r.campaign ? `[${r.campaign}] ` : ""}${r.harness}/${r.model} ${r.case} ${r.config}: ${r.error ?? ""}`),
  ];
}

/** The report text for `candidate` over its rows (the caller filters by candidate). */
export function formatReport(candidate: string, rows: LedgerRow[]): string {
  if (rows.length === 0) return `no result rows for ${candidate}`;
  const signalled = rows.filter((r) => typeof r.passed === "boolean");
  const skips = rows.filter((r) => typeof r.passed !== "boolean");
  if (signalled.length === 0) {
    return [`${candidate} — ${rows.length} row(s), none with a pass signal`, ...skipSection(skips)].join("\n");
  }
  const cells = new Map<string, Cell>();
  for (const r of signalled) {
    const key = cellKey(r);
    const id = JSON.stringify(key);
    let cell = cells.get(id);
    if (!cell) {
      const [campaign, harness, model, kase, config] = key as [string, string, string, string, string];
      cell = { campaign, harness, model, case: kase, config, rows: [] };
      cells.set(id, cell);
    }
    cell.rows.push(r);
  }
  const sorted = [...cells.values()].sort((a, b) => {
    const ka = [a.campaign, a.harness, a.model, a.case, a.config];
    const kb = [b.campaign, b.harness, b.model, b.case, b.config];
    for (let i = 0; i < ka.length; i++) {
      const d = compareStrings(ka[i]!, kb[i]!);
      if (d !== 0) return d;
    }
    return 0;
  });
  const deltas: string[] = [];
  for (const cell of sorted) {
    if (cell.config !== "with") continue;
    const base = cells.get(JSON.stringify([cell.campaign, cell.harness, cell.model, cell.case, "baseline"]));
    if (!base) continue;
    const d = passRate(cell) - passRate(base);
    const scope = `${cell.campaign ? `${cell.campaign}/` : ""}${cell.harness}/${cell.model}`;
    deltas.push(`delta (with - baseline) [${scope}] ${cell.case}: ${d >= 0 ? "+" : ""}${d.toFixed(2)}`);
  }
  return [
    "",
    `${candidate} — ${rows.length} trial row(s)`,
    ...table([HEADER, ...sorted.map(cellLine)]),
    ...deltas,
    ...skipSection(skips),
  ].join("\n");
}

/** The report for `candidate` over every one of its rows in the ledger. */
export function report(candidate: string, resultsPath: string): string {
  return formatReport(candidate, readRows(resultsPath).filter((r) => r.candidate === candidate));
}
