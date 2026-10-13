import { afterEach, beforeEach, expect, test } from "bun:test";
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { appendRow, doneKeys, pythonJson, readRows, resumeKey, type Row } from "../src/ledger.ts";
import { sandbox } from "./helpers/stubs.ts";

let box: ReturnType<typeof sandbox>;
beforeEach(() => {
  box = sandbox();
});
afterEach(() => box.cleanup());

const specRow = readFileSync(join(import.meta.dir, "fixtures/spec-row.json"), "utf8").trimEnd();

test("the spec's example row round-trips byte for byte", () => {
  expect(pythonJson(JSON.parse(specRow))).toBe(specRow);
});

test("keys sort by code point at every depth, with Python separators", () => {
  expect(pythonJson({ b: 1, a: { z: [], y: {} }, B: [1.5, null, true, false, "x"] })).toBe(
    '{"B": [1.5, null, true, false, "x"], "a": {"y": {}, "z": []}, "b": 1}',
  );
  // U+FB01 sorts before U+1F600 by code point, though not by UTF-16 code unit.
  expect(pythonJson({ "\u{1F600}": 1, "ﬁ": 2 })).toBe('{"\\ufb01": 2, "\\ud83d\\ude00": 1}');
});

test("non-ASCII escapes as lowercase UTF-16 units; / is not escaped; numbers print as JS", () => {
  expect(pythonJson("café — ✓ a/b \u{1F600}\n\t\"\\\u0001")).toBe('"caf\\u00e9 \\u2014 \\u2713 a/b \\ud83d\\ude00\\n\\t\\"\\\\\\u0001"');
  expect(pythonJson(0.014100000000000001)).toBe("0.014100000000000001");
  expect(pythonJson(-1)).toBe("-1");
});

test("matches Python's json.dumps when python3 is available", () => {
  const py = Bun.which("python3");
  if (!py) return;
  const value = { "é": ["∅", { "z": 1, "Z": 0.25 }], "a/b": "\u{1F600}\u0000\u007f", "ﬁ": null };
  const r = Bun.spawnSync([py, "-c", "import json,sys; print(json.dumps(json.loads(sys.stdin.read()), sort_keys=True), end='')"], {
    stdin: Buffer.from(JSON.stringify(value)),
  });
  if (r.exitCode !== 0) return;
  expect(pythonJson(value)).toBe(r.stdout.toString());
});

test("appending creates the ledger and its directory, one line per row", () => {
  const path = join(box.root, "deep", "dir", "results.jsonl");
  const row = JSON.parse(specRow) as Row;
  appendRow(path, row);
  appendRow(path, { ...row, trial: 1 });
  const lines = readFileSync(path, "utf8").split("\n");
  expect(lines).toHaveLength(3);
  expect(lines[0]).toBe(specRow);
  expect(lines[2]).toBe("");
});

test("reading skips lines that are not rows; a missing campaign reads as empty", () => {
  const path = join(box.root, "results.jsonl");
  const old = { harness: "claude", model: "m", candidate: "c", case: "k", config: "with", trial: 2 };
  writeFileSync(
    path,
    [specRow, "not json", "[1,2]", '{"harness":"claude"}', JSON.stringify({ ...old, trial: "2" }), JSON.stringify(old), ""].join("\n"),
  );
  const rows = readRows(path);
  expect(rows).toHaveLength(2);
  expect(rows[1]!.campaign).toBe("");
  expect(resumeKey(rows[0]!)).toBe("weekly-20260817|claude|claude-sonnet-4-5|mermaid|add-architecture-diagram|with|0");
  expect([...doneKeys(path)]).toEqual([resumeKey(rows[0]!), "|claude|m|c|k|with|2"]);
  expect(readRows(join(box.root, "missing.jsonl"))).toEqual([]);
});
