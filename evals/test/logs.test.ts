import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { isoToMillis, parseLog, pyStrip, splitLines, type EventRow, type Harness, type ToolCallRow } from "../src/logs.ts";
import { coerceJson } from "../src/store.ts";
import { REPO_ROOT } from "./pb.ts";

const VECTORS = join(REPO_ROOT, "test", "vectors");
const vectorBytes = (name: string) => new Uint8Array(readFileSync(join(VECTORS, name)));
const vectorJson = (name: string): unknown => JSON.parse(readFileSync(join(VECTORS, name), "utf8"));
const vectorLines = (name: string): Record<string, unknown>[] =>
  readFileSync(join(VECTORS, name), "utf8").split("\n").filter((l) => l.trim() !== "").map((l) => JSON.parse(l));

const encode = (text: string) => new TextEncoder().encode(text);
const parseText = (harness: Harness, lines: string[]) => parseLog(harness, encode(lines.join("\n") + "\n"));

// An event row as the vectors list it: non-null fields except payload, and
// `artifacts` only when there are some.
function visibleEvent(row: EventRow): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(row)) {
    if (k === "payload" || v === null || v === undefined) continue;
    if (k === "artifacts" && (v as string[]).length === 0) continue;
    out[k] = v;
  }
  return out;
}

function visibleCall(row: ToolCallRow): Record<string, unknown> {
  const { artifacts, ...rest } = row;
  return artifacts.length > 0 ? { ...rest, artifacts } : rest;
}

describe("splitLines and strip", () => {
  test("split exactly as Python str.splitlines()", () => {
    expect(splitLines("")).toEqual([]);
    expect(splitLines("\n")).toEqual([""]);
    expect(splitLines("a\nb")).toEqual(["a", "b"]);
    expect(splitLines("a\n\nb\n")).toEqual(["a", "", "b"]);
    // Python: "a\v b\f c\x1c d\x1d e\x1e f\x85 g\u2028 h\u2029 i\x1fj\r\r\nk\n".splitlines()
    expect(splitLines("a\v b\f c\x1c d\x1d e\x1e f\x85 g\u2028 h\u2029 i\x1fj\r\r\nk\n"))
      .toEqual(["a", " b", " c", " d", " e", " f", " g", " h", " i\x1fj", "", "k"]);
  });

  test("strip as Python str.strip()", () => {
    // Python: " \x1c\x1f\x85x\ufeff \u3000".strip() == "x\ufeff"
    expect(pyStrip(" \x1c\x1f\x85x\ufeff \u3000")).toBe("x\ufeff");
  });
});

describe("claude timestamps", () => {
  test("convert as trunc(((seconds × 10⁶ + µs) / 10⁶) × 1000)", () => {
    // Reference values computed in Python with the spec's formula.
    expect(isoToMillis("2026-07-21T19:00:48.339Z")).toBe(1784660448339);
    expect(isoToMillis("2026-07-21T21:00:48.339+02:00")).toBe(1784660448339);
    expect(isoToMillis("2026-07-21T19:00:49.000Z")).toBe(1784660449000);
    expect(isoToMillis("2026-07-21T19:00:48.1234567+00:00")).toBe(1784660448123);
    expect(isoToMillis("2026-07-21T14:30:00-04:30")).toBe(1784660400000);
  });

  test("unparseable or zoneless times are null", () => {
    expect(isoToMillis("2026-07-21T19:00:48")).toBeNull();
    expect(isoToMillis("2026-02-30T00:00:00Z")).toBeNull();
    expect(isoToMillis("yesterday")).toBeNull();
    expect(isoToMillis(1784660448339)).toBeNull();
  });
});

describe("seq", () => {
  test("blank and non-object lines count but yield no event; thinking_tokens is dropped", () => {
    const parsed = parseText("claude", [
      "# preconditions: {}",
      "",
      "[1, 2]",
      "null",
      "   ",
      "{not json",
      '{"type": "system", "subtype": "thinking_tokens", "tokens": 3}',
      '{"type": "result", "subtype": "success", "result": "ok", "session_id": "s-r"}',
    ]);
    expect(parsed.events.map((e) => [e.seq, e.event_type])).toEqual([[7, "result/success"]]);
    expect(parsed.sessionId).toBe("s-r");
    expect(parsed.era).toBe("post");
    expect(parsed.provenance).toBeNull();
  });

  test("every Python line break advances seq", () => {
    const text = '# h\r\n{"type":"step_start"}\x85{"type":"text","part":{"text":"a"}}\u2028\r{"type":"step_finish"}';
    const parsed = parseLog("opencode", encode(text));
    expect(parsed.events.map((e) => e.seq)).toEqual([1, 2, 4]);
  });

  test("invalid UTF-8 is replaced, not fatal", () => {
    const bytes = new Uint8Array([...encode('{"type":"text","part":{"text":"a'), 0xff, ...encode('b"}}\n')]);
    expect(parseLog("opencode", bytes).events[0]!.text).toBe("a\ufffdb");
  });
});

describe("claude log (C.3)", () => {
  const parsed = parseLog("claude", vectorBytes("c3-claude.log"));

  test("run meta", () => {
    expect(parsed.era).toBe("legacy");
    expect(parsed.sessionId).toBe("sess-1");
    expect(parsed.provenance).toEqual({ apiKeySource: "apiKeyHelper", plugins: [], tools: ["Bash", "Read", "Skill"] });
    expect(parsed.modelUsage).toEqual({ "claude-sonnet-4-5": { costUSD: 0.01 } });
    expect(parsed.rollup).toBeNull();
  });

  test("event rows", () => {
    expect(parsed.events.map(visibleEvent)).toEqual(vectorLines("c3-claude.events.jsonl"));
  });

  test("payloads of seq 4 and seq 6 after excision and mirror dedup", () => {
    const bySeq = (seq: number) => parsed.events.find((e) => e.seq === seq)!.payload;
    expect([bySeq(4), bySeq(6)]).toEqual(vectorLines("c3-claude.payloads-seq4-seq6.jsonl"));
  });

  test("tool calls", () => {
    expect(parsed.toolCalls.map(visibleCall)).toEqual(vectorLines("c3-claude.tool-calls.jsonl"));
  });

  test("two deduplicated artifacts", () => {
    expect(parsed.artifacts.map((a) => [a.sha256, a.kind, a.mime, a.bytes.length, a.filename])).toEqual([
      ["c4c7a80748655c031bc38b16ba41e13650acfe8f0e5b4b1841d3d2f7a9616450", "screenshot", "image/png", 12, "c4c7a8074865.png"],
      ["89206d01a7a5f7f6d904c37e473b8b9c695376f9bada9711cde47b23aff314f9", "write_content", "text/plain", 5001, "89206d01a7a5.txt"],
    ]);
    expect(new TextDecoder().decode(parsed.artifacts[0]!.bytes.slice(1))).toBe("PNG-fixture");
    expect(parsed.artifacts[0]!.bytes[0]).toBe(0x89);
    expect(parsed.artifacts[0]!.textRef).toBeNull();
    expect(parsed.artifacts[1]!.textRef).toBe("x".repeat(5000));
  });

  test("an edit's new_string over 5000 characters becomes an edit_diff artifact", () => {
    const edit = parseText("claude", [JSON.stringify({
      type: "assistant",
      message: { content: [{ type: "tool_use", id: "t", name: "Edit", input: { new_string: "é".repeat(5001), old_string: "a" } }] },
    })]);
    expect(edit.artifacts.map((a) => [a.kind, a.bytes.length])).toEqual([["edit_diff", 10002]]);
    expect(edit.toolCalls[0]!.input).toEqual({ new_string: { $artifact: edit.artifacts[0]!.sha256 }, old_string: "a" });
    const short = parseText("claude", [JSON.stringify({
      type: "assistant",
      message: { content: [{ type: "tool_use", id: "t", name: "Write", input: { content: "😀".repeat(5000) } }] },
    })]);
    expect(short.artifacts).toEqual([]);
  });
});

describe("opencode log (C.3)", () => {
  const parsed = parseLog("opencode", vectorBytes("c3-opencode.log"));

  test("run meta and rollup", () => {
    expect(parsed.era).toBe("na");
    expect(parsed.sessionId).toBe("ses-oc");
    expect(parsed.rollup).toEqual({ cache_creation_tokens: 44, cache_read_tokens: 33, cost_usd: 0.005, duration_ms: 1500, input_tokens: 11, output_tokens: 22 });
    expect(parsed.artifacts).toEqual([]);
  });

  test("event rows", () => {
    expect(parsed.events.map(visibleEvent)).toEqual(vectorLines("c3-opencode.events.jsonl"));
  });

  test("payload of seq 1 with filediff.patch deduplicated", () => {
    expect(parsed.events.find((e) => e.seq === 1)!.payload).toEqual(vectorJson("c3-opencode.payload-seq1.json"));
  });

  test("tool-call bodies as sent, after json coercion", () => {
    const sent: Record<string, unknown>[] = parsed.toolCalls.map((c) => ({ ...visibleCall(c), output: coerceJson(c.output) }));
    const expected = vectorLines("c3-opencode.tool-calls.jsonl").map(({ run, ...rest }) => rest);
    expect(sent).toEqual(expected);
  });

  test("data: URI attachments and long inputs are excised", () => {
    const content = "c".repeat(5001);
    const log = parseText("opencode", [JSON.stringify({
      type: "tool_use", timestamp: 5, sessionID: "",
      part: { callID: "w", tool: "write", state: {
        status: "completed", input: { filePath: "a", content },
        attachments: [{ url: "data:image/jpeg;base64,iVBORy1maXh0dXJl" }, { url: "data:,%89PNG" }, { url: "https://x/y.png" }],
        time: { start: 1, end: 4 },
      } },
    })]);
    expect(log.artifacts.map((a) => [a.kind, a.mime, a.bytes.length])).toEqual([
      ["screenshot", "image/jpeg", 12], ["screenshot", "image/png", 4], ["write_content", "text/plain", 5001],
    ]);
    const shas = log.artifacts.map((a) => a.sha256);
    expect(log.events[0]!.artifacts).toEqual(shas);
    expect(log.toolCalls[0]!.artifacts).toEqual(shas);
    expect(log.toolCalls[0]!.input).toEqual({ filePath: "a", content: { $artifact: shas[2] } });
    expect((log.events[0]!.payload as any).part.state.attachments).toEqual([
      { url: { $artifact: shas[0] } }, { url: { $artifact: shas[1] } }, { url: "https://x/y.png" },
    ]);
    expect(log.rollup).toEqual({ cost_usd: null, duration_ms: 0, input_tokens: 0, output_tokens: 0, cache_read_tokens: 0, cache_creation_tokens: 0 });
    expect(log.sessionId).toBe("");
  });
});

describe("codex log", () => {
  // The spec's captured log (codex-cli 0.162.1) behind a preconditions header.
  const captured = parseText("codex", [
    '# preconditions: {"harness": "codex"}',
    '{"type":"thread.started","thread_id":"01a132ee-ff13-7c01-8170-7d57383f6262"}',
    '{"type":"item.completed","item":{"id":"item_0","type":"error","message":"`--dangerously-bypass-hook-trust` is enabled. Enabled hooks may run without review for this invocation."}}',
    '{"type":"turn.started"}',
    '{"type":"item.completed","item":{"id":"item_2","type":"agent_message","text":"OK"}}',
    '{"type":"turn.completed","usage":{"input_tokens":12868,"cached_input_tokens":0,"cache_write_input_tokens":12865,"output_tokens":5,"reasoning_output_tokens":0}}',
  ]);

  test("captured log: meta, event rows and rollup", () => {
    expect(captured.sessionId).toBe("01a132ee-ff13-7c01-8170-7d57383f6262");
    expect(captured.era).toBe("na");
    expect(captured.provenance).toBeNull();
    expect(captured.modelUsage).toBeNull();
    expect(captured.events.map(visibleEvent)).toEqual([
      { seq: 1, vendor: "codex", role: "system", event_type: "thread.started" },
      { seq: 2, vendor: "codex", role: "system", event_type: "item.completed/error" },
      { seq: 3, vendor: "codex", role: "system", event_type: "turn.started" },
      { seq: 4, vendor: "codex", role: "assistant", event_type: "item.completed/agent_message", text: "OK" },
      { seq: 5, vendor: "codex", role: "result", event_type: "turn.completed", input_tokens: 12868, output_tokens: 5, cache_read_tokens: 0, cache_write_tokens: 12865 },
    ]);
    expect(captured.events.every((e) => e.ts === null)).toBe(true);
    expect(captured.events[1]!.payload).toEqual({ type: "item.completed", item: { id: "item_0", type: "error", message: "`--dangerously-bypass-hook-trust` is enabled. Enabled hooks may run without review for this invocation." } });
    expect(captured.toolCalls).toEqual([]);
    expect(captured.artifacts).toEqual([]);
    expect(captured.rollup).toEqual({ cost_usd: null, duration_ms: null, input_tokens: 12868, output_tokens: 5, cache_read_tokens: 0, cache_creation_tokens: 12865 });
  });

  // The documented tool-item shapes, plus an unfinished and a failed item.
  const tools = parseText("codex", [
    '{"type":"thread.started","thread_id":"t-1"}',
    '{"type":"thread.started","thread_id":"t-2"}',
    '{"type":"item.started","item":{"id":"item_0","type":"command_execution","command":"/bin/zsh -lc \'cat SKILL.md\'","aggregated_output":"","exit_code":null,"status":"in_progress"}}',
    '{"type":"item.completed","item":{"id":"item_0","type":"command_execution","command":"/bin/zsh -lc \'cat SKILL.md\'","aggregated_output":"---\\nname: mermaid\\n...","exit_code":0,"status":"completed"}}',
    '{"type":"item.completed","item":{"id":"item_2","type":"file_change","changes":[{"path":"/tmp/…/ws/README.md","kind":"update"}],"status":"completed"}}',
    '{"type":"item.started","item":{"id":"item_3","type":"command_execution","command":"sleep 99","aggregated_output":"","exit_code":null,"status":"in_progress"}}',
    '{"type":"item.updated","item":{"id":"item_4","type":"todo_list","items":[]}}',
    '{"type":"item.completed","item":{"id":"item_5","type":"command_execution","command":"false","aggregated_output":"","exit_code":1,"status":"failed"}}',
    '{"type":"item.completed","item":{"id":"item_6","type":"reasoning","text":"' + "r".repeat(5003) + '"}}',
    '{"type":"error","message":"Reconnecting... 1/5"}',
    '{"type":"turn.failed","error":{"message":"unexpected status 401 Unauthorized: Incorrect API key provided"}}',
  ]);

  test("tool items: event types, roles, text and error fields", () => {
    expect(tools.sessionId).toBe("t-1");
    expect(tools.events.map(visibleEvent)).toEqual([
      { seq: 0, vendor: "codex", role: "system", event_type: "thread.started" },
      { seq: 1, vendor: "codex", role: "system", event_type: "thread.started" },
      { seq: 2, vendor: "codex", role: "tool_call", event_type: "item.started/command_execution", tool_call_id: "item_0", tool_name: "command_execution", status: "in_progress", is_error: false },
      { seq: 3, vendor: "codex", role: "tool_call", event_type: "item.completed/command_execution", tool_call_id: "item_0", tool_name: "command_execution", status: "completed", is_error: false },
      { seq: 4, vendor: "codex", role: "tool_call", event_type: "item.completed/file_change", tool_call_id: "item_2", tool_name: "file_change", status: "completed", is_error: false },
      { seq: 5, vendor: "codex", role: "tool_call", event_type: "item.started/command_execution", tool_call_id: "item_3", tool_name: "command_execution", status: "in_progress", is_error: false },
      { seq: 6, vendor: "codex", role: "system", event_type: "item.updated/todo_list" },
      { seq: 7, vendor: "codex", role: "tool_call", event_type: "item.completed/command_execution", tool_call_id: "item_5", tool_name: "command_execution", status: "failed", is_error: true },
      { seq: 8, vendor: "codex", role: "assistant", event_type: "item.completed/reasoning", text: "r".repeat(5000) },
      { seq: 9, vendor: "codex", role: "system", event_type: "error", text: "Reconnecting... 1/5" },
      { seq: 10, vendor: "codex", role: "result", event_type: "turn.failed", text: "unexpected status 401 Unauthorized: Incorrect API key provided", is_error: true },
    ]);
  });

  test("tool calls come from each item's last event; unfinished items are no_result", () => {
    expect(tools.toolCalls).toEqual([
      { tool_call_id: "item_0", tool_name: "command_execution", input: { command: "/bin/zsh -lc 'cat SKILL.md'" },
        output: { aggregated_output: "---\nname: mermaid\n...", exit_code: 0 }, status: "completed", is_error: false,
        wallclock_ms: null, started_ts: null, artifacts: [] },
      { tool_call_id: "item_2", tool_name: "file_change", input: { changes: [{ path: "/tmp/…/ws/README.md", kind: "update" }] },
        output: null, status: "completed", is_error: false, wallclock_ms: null, started_ts: null, artifacts: [] },
      { tool_call_id: "item_3", tool_name: "command_execution", input: { command: "sleep 99" },
        output: { aggregated_output: "", exit_code: null }, status: "no_result", is_error: false,
        wallclock_ms: null, started_ts: null, artifacts: [] },
      { tool_call_id: "item_5", tool_name: "command_execution", input: { command: "false" },
        output: { aggregated_output: "", exit_code: 1 }, status: "failed", is_error: true,
        wallclock_ms: null, started_ts: null, artifacts: [] },
    ]);
    expect(tools.artifacts).toEqual([]);
    expect(tools.rollup).toEqual({ cost_usd: null, duration_ms: null, input_tokens: 0, output_tokens: 0, cache_read_tokens: 0, cache_creation_tokens: 0 });
  });
});
