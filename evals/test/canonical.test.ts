import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { canonicalJson, canonicalSha256, compareCodePoints, parseJson, plain, pythonFloatRepr } from "../src/canonical.ts";
import { REPO_ROOT } from "./pb.ts";

const vector = (name: string) => readFileSync(join(REPO_ROOT, "test/vectors", name), "utf8").replace(/\n$/, "");

describe("canonical JSON (Appendix C.1)", () => {
  test("synthetic number and escaping cases", () => {
    const row = parseJson(vector("c1-synthetic.jsonl"));
    expect(canonicalJson(row)).toBe(vector("c1-synthetic.canonical.json"));
    expect(canonicalSha256(row)).toBe("8073810cd9dc23e3254f0fef9c77dc68726e52639f0a93fb4ef6f47be46ad57e");
  });

  test.each([
    ["c1-ledger-line-24.jsonl", "379d29aaac065468505cb4b01fa896a040177d63ffffe6ccb970fd8ed063825d"],
    ["c1-ledger-line-58.jsonl", "fa5978f82d55751f1dd3324463cff039ead7fd01d9a9bac1012743454669b593"],
    ["c1-ledger-line-188.jsonl", "88db541a672c82ebbad6a7c7282188393eeeb9637e14be5ee129fcb6e0dfc66f"],
  ])("record_sha256 of %s", (file, sha) => {
    expect(canonicalSha256(parseJson(vector(file)))).toBe(sha);
  });

  test("Python float repr", () => {
    const cases: [number, string][] = [
      [1, "1.0"], [0.0001, "0.0001"], [1e-5, "1e-05"], [2.5e-7, "2.5e-07"], [1e16, "1e+16"], [123456789012345, "123456789012345.0"],
      [-0, "-0.0"], [0.047738249999999996, "0.047738249999999996"], [1.5e300, "1.5e+300"], [-12.25, "-12.25"], [9999999999999998, "9999999999999998.0"],
    ];
    for (const [x, want] of cases) expect(pythonFloatRepr(x)).toBe(want);
  });

  test("integers keep their digits and plain numbers serialise like Python", () => {
    expect(canonicalJson(parseJson("[12345678901234567890, -0, 0, 7]"))).toBe("[12345678901234567890,0,0,7]");
    expect(canonicalJson({ b: 1, a: 0.5, c: [true, null, " /"] })).toBe('{"a":0.5,"b":1,"c":[true,null," /"]}');
    expect(plain(parseJson('{"x": 1.0, "y": [2e3]}'))).toEqual({ x: 1, y: [2000] });
  });

  test("keys sort by code point, not UTF-16 unit", () => {
    expect(["\u{1F600}", "￿", "a"].sort(compareCodePoints)).toEqual(["a", "￿", "\u{1F600}"]);
  });

  test("rejects malformed JSON", () => {
    expect(() => parseJson("{")).toThrow();
    expect(() => parseJson("[1,]")).toThrow();
    expect(() => parseJson("01")).toThrow();
  });
});
