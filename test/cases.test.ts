import { afterEach, beforeEach, expect, test } from "bun:test";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { loadCases } from "../src/cases.ts";
import { sandbox } from "./helpers/stubs.ts";

let box: ReturnType<typeof sandbox>;
beforeEach(() => {
  box = sandbox();
});
afterEach(() => box.cleanup());

const SHIPPED = join(import.meta.dir, "..", "cases");

function write(rel: string, body: string): void {
  const path = join(box.root, rel);
  mkdirSync(join(path, ".."), { recursive: true });
  writeFileSync(path, body);
}

test("cases load sorted by id with optional fixture and check.py; dirs without case.json are ignored", () => {
  write("c/zeta/case.json", '{"prompt":"z"}');
  write("c/alpha/case.json", '{"prompt":"a","assertions":[{"id":"a1","text":"t","extra":1}],"other":true}');
  write("c/alpha/fixture/README.md", "x");
  write("c/alpha/check.py", "print('[]')");
  write("c/notes/readme.txt", "x");
  const cases = loadCases(box.root, "c");
  expect(cases.map((c) => c.id)).toEqual(["alpha", "zeta"]);
  expect(cases[0]).toEqual({
    id: "alpha",
    dir: join(box.root, "c/alpha"),
    prompt: "a",
    assertions: [{ id: "a1", text: "t" }],
    fixture: join(box.root, "c/alpha/fixture"),
    check: join(box.root, "c/alpha/check.py"),
  });
  expect(cases[1]).toMatchObject({ assertions: [], fixture: null, check: null });
  expect(loadCases(box.root, "c", "zeta").map((c) => c.id)).toEqual(["zeta"]);
});

test("dataset errors carry the spec messages", () => {
  const root = join(box.root, "c");
  expect(() => loadCases(box.root, "c")).toThrow(`no eval cases at ${root} — copy cases/_template to author some`);
  mkdirSync(join(root, "empty"), { recursive: true });
  expect(() => loadCases(box.root, "c")).toThrow(`no case.json found under ${root}`);
  write("c/one/case.json", '{"prompt":"p"}');
  expect(() => loadCases(box.root, "c", "two")).toThrow(`no case.json found under ${root} for --case two`);
  const file = join(root, "one/case.json");
  for (const [body, msg] of [
    ["{not json", "not valid JSON"],
    ['{"assertions":[]}', "missing required field 'prompt'"],
    ['{"prompt":""}', "missing required field 'prompt'"],
    ['["prompt"]', "missing required field 'prompt'"],
    ['{"prompt":"p","assertions":[{"id":"a1"}]}', "every assertion needs 'id' and 'text'"],
    ['{"prompt":"p","assertions":{"id":"a1","text":"t"}}', "every assertion needs 'id' and 'text'"],
  ] as const) {
    writeFileSync(file, body);
    expect(() => loadCases(box.root, "c")).toThrow(`${file}: ${msg}`);
  }
});

test("the shipped cases load", () => {
  const smoke = loadCases(SHIPPED, "smoke-echo");
  expect(smoke).toHaveLength(1);
  expect(smoke[0]).toMatchObject({ id: "create-file", assertions: [], fixture: null });
  expect(smoke[0]!.check).toBe(join(SHIPPED, "smoke-echo/create-file/check.py"));
  const template = loadCases(SHIPPED, "_template");
  expect(template[0]).toMatchObject({ id: "rename-this-case", assertions: [{ id: "a1" }] });
});
