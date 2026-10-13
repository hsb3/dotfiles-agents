import { afterEach, beforeEach, expect, test } from "bun:test";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { loadCandidate, parseAgent } from "../src/candidate.ts";
import { sandbox } from "./helpers/stubs.ts";

let box: ReturnType<typeof sandbox>;
beforeEach(() => {
  box = sandbox();
});
afterEach(() => box.cleanup());

function files(dir: string, entries: Record<string, string>): string {
  for (const [rel, body] of Object.entries(entries)) {
    mkdirSync(join(dir, rel, ".."), { recursive: true });
    writeFileSync(join(dir, rel), body);
  }
  return dir;
}

const SCOUT = `---
name: scout
description: Read-only investigator. Use before changing unfamiliar code.
model: haiku
tools: Read, Grep, Glob
---
You are a scout. Report what you find with file paths and line numbers.
`;

test("a directory with SKILL.md is a skill named after the directory, even beside plugin and agent files", () => {
  const dir = files(join(box.root, "mermaid"), { "SKILL.md": "x", ".claude-plugin/plugin.json": "{}", "a.md": "x" });
  const c = loadCandidate("mermaid", dir);
  expect(c.kind).toBe("skill");
  expect(c.skillName).toBe("mermaid");
  expect(c.dir).toBe(dir);
});

test("a plugin takes name and version from plugin.json, defaulting to the dir name and 0.0.0", () => {
  const a = files(join(box.root, "p1"), { ".claude-plugin/plugin.json": '{"name":"demo-plugin","version":"1.2.3"}', "x.md": "x" });
  expect(loadCandidate("p", a)).toMatchObject({ kind: "plugin", plugin: { name: "demo-plugin", version: "1.2.3" } });
  const b = files(join(box.root, "p2"), { ".claude-plugin/plugin.json": "{}" });
  expect(loadCandidate("p", b).plugin).toEqual({ name: "p2", version: "0.0.0" });
});

test("agent files are the top-level .md files other than README.md, sorted by filename", () => {
  const dir = files(join(box.root, "agents"), {
    "zeta.md": "Zeta body first line\nmore",
    "README.md": "readme",
    "Readme.MD": "readme too",
    "scout.md": SCOUT,
    "nested/inner.md": "ignored",
  });
  const c = loadCandidate("agents", dir);
  expect(c.kind).toBe("agent");
  expect(c.agents.map((a) => a.file)).toEqual(["scout.md", "zeta.md"]);
  expect(c.agents[0]).toEqual({
    file: "scout.md",
    name: "scout",
    description: "Read-only investigator. Use before changing unfamiliar code.",
    body: "You are a scout. Report what you find with file paths and line numbers.",
    model: "haiku",
    tools: "Read, Grep, Glob",
  });
  expect(c.agents[1]).toMatchObject({ name: "zeta", description: "Zeta body first line", body: "Zeta body first line\nmore", model: null });
});

test("field values are trimmed and stripped of quote characters; empty fields fall back", () => {
  const a = parseAgent("x.md", `---\nname:   "'quoted'"  \ndescription:\nother: 1\n---\n\n  ${"d".repeat(250)}\nline2\n`);
  expect(a.name).toBe("quoted");
  expect(a.description).toBe("d".repeat(200));
  expect(parseAgent("plain.md", "no frontmatter\n---\nstill body").name).toBe("plain");
  expect(parseAgent("plain.md", "no frontmatter\n---\nstill body").body).toBe("no frontmatter\n---\nstill body");
  expect(parseAgent("e.md", "---\nname: \n---\n").name).toBe("e");
});

test("a flat .md file is copied into a temp dir that cleanup removes", () => {
  const path = files(box.root, { "scout.md": SCOUT });
  const c = loadCandidate("scout", join(path, "scout.md"));
  expect(c.kind).toBe("agent");
  expect(c.dir).not.toBe(box.root);
  expect(existsSync(join(c.dir, "scout.md"))).toBe(true);
  c.cleanup();
  expect(existsSync(c.dir)).toBe(false);
});

test("bad candidates fail with the spec messages", () => {
  expect(() => loadCandidate("x", join(box.root, "nope"))).toThrow(`no such candidate path: ${join(box.root, "nope")}`);
  const txt = files(box.root, { "notes.txt": "x" });
  expect(() => loadCandidate("x", join(txt, "notes.txt"))).toThrow(`${join(txt, "notes.txt")}: not a directory or a flat agent .md file`);
  const empty = files(join(box.root, "empty"), { "README.md": "x", "notes.txt": "y" });
  expect(() => loadCandidate("x", empty)).toThrow(`${empty}: not recognizable as skill / agent / plugin`);
  const dup = files(join(box.root, "dup"), { "a.md": "---\nname: scout\n---\nA", "b.md": "---\nname: 'scout'\n---\nB" });
  expect(() => loadCandidate("x", dup)).toThrow("duplicate agent name 'scout': a.md and b.md");
});
