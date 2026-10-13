// Trial log parsing for `evals load-runs`: one harness log's bytes in; run
// meta, run events, tool calls, excised artifacts and a rollup out. Pure: no
// database and no filesystem. PocketBase json coercion is the store's job.

export type Harness = "claude" | "opencode" | "codex";

export type ArtifactKind = "write_content" | "edit_diff" | "screenshot" | "tool_output";

export interface LogArtifact {
  sha256: string;
  kind: ArtifactKind;
  mime: string;
  bytes: Uint8Array;
  filename: string; // <first 12 hex>.png for a screenshot, else .txt
  textRef: string | null; // non-screenshots: first 5000 characters of the bytes
}

export interface EventRow {
  seq: number;
  ts: number | null;
  vendor: Harness;
  role: string;
  event_type: string;
  tool_name?: string;
  tool_call_id?: string;
  status?: string;
  is_error?: boolean;
  input_tokens?: number;
  output_tokens?: number;
  cache_read_tokens?: number;
  cache_write_tokens?: number;
  cost_usd?: number;
  wallclock_ms?: number;
  text?: string;
  payload: unknown;
  artifacts: string[]; // shas in order; the first becomes `artifact`
}

export interface ToolCallRow {
  tool_call_id: string;
  tool_name: string;
  input: unknown;
  output: unknown;
  status: string;
  is_error: boolean | null;
  wallclock_ms: number | null;
  started_ts: number | null;
  artifacts: string[];
}

export interface Rollup {
  cost_usd: number | null;
  duration_ms: number | null;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  cache_creation_tokens: number;
}

export interface ParsedLog {
  sessionId: string;
  era: "legacy" | "post" | "na";
  provenance: Record<string, unknown> | null;
  modelUsage: unknown | null;
  events: EventRow[];
  toolCalls: ToolCallRow[];
  artifacts: LogArtifact[]; // deduplicated by sha within the log, first-seen order
  rollup: Rollup | null; // null for claude
}

const TEXT_LIMIT = 5000;

type Obj = Record<string, unknown>;

function isObj(v: unknown): v is Obj {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function objAt(v: unknown, key: string): Obj | undefined {
  if (!isObj(v)) return undefined;
  const child = v[key];
  return isObj(child) ? child : undefined;
}

function str(v: unknown): string | undefined {
  return typeof v === "string" ? v : undefined;
}

function num(v: unknown): number | undefined {
  return typeof v === "number" && Number.isFinite(v) ? v : undefined;
}

// ---------------------------------------------------------------------------
// Text, the Python way

const LINE_BREAK = /\r\n|[\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029]/g;

// Python's str.splitlines(): no empty last element after a final line break.
export function splitLines(text: string): string[] {
  const lines: string[] = [];
  let start = 0;
  for (const m of text.matchAll(LINE_BREAK)) {
    lines.push(text.slice(start, m.index));
    start = m.index + m[0].length;
  }
  if (start < text.length) lines.push(text.slice(start));
  return lines;
}

// Python's str.strip(): its whitespace differs from String.prototype.trim()
// (U+001C..U+001F and U+0085 are whitespace, U+FEFF is not).
const PY_SPACE = "[\\t\\n\\v\\f\\r\\x1c-\\x1f \\x85\\xa0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000]+";
const PY_STRIP = new RegExp(`^${PY_SPACE}|${PY_SPACE}$`, "g");

export function pyStrip(s: string): string {
  return s.replace(PY_STRIP, "");
}

// The end index of the first `n` code points of `s` (Python counts code points).
function codePointEnd(s: string, n: number): number {
  let i = 0;
  for (let count = 0; i < s.length && count < n; count++) i += s.codePointAt(i)! > 0xffff ? 2 : 1;
  return i;
}

function head(s: string): string {
  return s.length <= TEXT_LIMIT ? s : s.slice(0, codePointEnd(s, TEXT_LIMIT));
}

function longerThanLimit(s: string): boolean {
  return s.length > TEXT_LIMIT && codePointEnd(s, TEXT_LIMIT) < s.length;
}

const UTF8 = new TextDecoder("utf-8", { ignoreBOM: true });

function decodeUtf8(bytes: Uint8Array): string {
  return UTF8.decode(bytes);
}

interface LogLine {
  seq: number;
  event: Obj;
}

// Every physical line counts toward seq; only JSON objects yield an event.
function eventLines(text: string): LogLine[] {
  const out: LogLine[] = [];
  splitLines(text).forEach((raw, seq) => {
    const line = pyStrip(raw);
    if (line === "") return;
    let event: unknown;
    try {
      event = JSON.parse(line);
    } catch {
      return;
    }
    if (isObj(event)) out.push({ seq, event });
  });
  return out;
}

// ---------------------------------------------------------------------------
// Timestamps

const ISO_TIME =
  /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2})(?:[.,](\d+))?)?(?:(Z)|([+-])(\d{2}):?(\d{2})?)$/i;

// trunc(((whole seconds since the epoch × 10⁶ + microseconds) / 10⁶) × 1000)
// in IEEE doubles; an ISO-8601 time without a zone, or invalid, is null.
export function isoToMillis(value: unknown): number | null {
  const m = typeof value === "string" ? ISO_TIME.exec(value) : null;
  if (!m) return null;
  const [y, mo, d, h, mi, s] = [1, 2, 3, 4, 5, 6].map((i) => Number(m[i] ?? 0)) as [number, number, number, number, number, number];
  const wall = new Date(Date.UTC(y, mo - 1, d, h, mi, s));
  if (wall.getUTCFullYear() !== y || wall.getUTCMonth() !== mo - 1 || wall.getUTCDate() !== d ||
      wall.getUTCHours() !== h || wall.getUTCMinutes() !== mi || wall.getUTCSeconds() !== s) return null;
  const micros = Number((m[7] ?? "").slice(0, 6).padEnd(6, "0"));
  const offset = m[8] ? 0 : (m[9] === "-" ? -1 : 1) * (Number(m[10]) * 3600 + Number(m[11] ?? 0) * 60);
  const seconds = wall.getTime() / 1000 - offset;
  return Math.trunc(((seconds * 1e6 + micros) / 1e6) * 1000);
}

// ---------------------------------------------------------------------------
// Artifacts

const TEXT_ENCODER = new TextEncoder();

const longTextBytes = (value: string) => (longerThanLimit(value) ? TEXT_ENCODER.encode(value) : null);
const base64Bytes = (value: string): Uint8Array => Buffer.from(value, "base64");

class ArtifactRegistry {
  private readonly bySha = new Map<string, LogArtifact>();

  // Registers the bytes (first sighting wins), records the sha on every sink
  // and returns the marker that replaces the excised value.
  excise(kind: ArtifactKind, mime: string, bytes: Uint8Array, ...sinks: string[][]): { $artifact: string } {
    const sha256 = new Bun.CryptoHasher("sha256").update(bytes).digest("hex");
    if (!this.bySha.has(sha256)) {
      const screenshot = kind === "screenshot";
      this.bySha.set(sha256, {
        sha256, kind, mime, bytes,
        filename: `${sha256.slice(0, 12)}${screenshot ? ".png" : ".txt"}`,
        textRef: screenshot ? null : head(decodeUtf8(bytes)),
      });
    }
    for (const sink of sinks) sink.push(sha256);
    return { $artifact: sha256 };
  }

  // Replaces holder[key] with the marker when it is a string that `bytesOf`
  // turns into artifact bytes.
  exciseField(holder: unknown, key: string, kind: ArtifactKind, mime: string,
              bytesOf: (value: string) => Uint8Array | null, ...sinks: string[][]): void {
    const value = isObj(holder) ? holder[key] : undefined;
    const bytes = typeof value === "string" ? bytesOf(value) : null;
    if (bytes) (holder as Obj)[key] = this.excise(kind, mime, bytes, ...sinks);
  }

  // A string field longer than 5000 characters becomes a text artifact.
  exciseLongText(holder: unknown, key: string, kind: ArtifactKind, ...sinks: string[][]): void {
    this.exciseField(holder, key, kind, "text/plain", longTextBytes, ...sinks);
  }

  list(): LogArtifact[] {
    return [...this.bySha.values()];
  }
}

// Python's urllib.parse.unquote_to_bytes, for a data: URI without ;base64.
function unquoteToBytes(s: string): Uint8Array {
  const raw = TEXT_ENCODER.encode(s);
  const out: number[] = [];
  for (let i = 0; i < raw.length; i++) {
    const hex = raw[i] === 0x25 ? String.fromCharCode(raw[i + 1] ?? 0, raw[i + 2] ?? 0) : "";
    if (/^[0-9a-fA-F]{2}$/.test(hex)) {
      out.push(parseInt(hex, 16));
      i += 2;
    } else out.push(raw[i]!);
  }
  return Uint8Array.from(out);
}

const DATA_URI = /^data:([^,]*),(.*)$/s;

function dataUri(url: string): { mime: string; bytes: Uint8Array } | null {
  const m = DATA_URI.exec(url);
  if (!m) return null;
  const params = m[1]!.split(";");
  const body = m[2]!;
  const base64 = params.slice(1).some((p) => p.trim().toLowerCase() === "base64");
  return { mime: params[0]!.trim() || "image/png", bytes: base64 ? Buffer.from(body, "base64") : unquoteToBytes(body) };
}

// ---------------------------------------------------------------------------
// Rows

type EventFields = Partial<Omit<EventRow, "seq" | "ts" | "vendor" | "role" | "event_type" | "payload" | "artifacts">>;

function eventRow(vendor: Harness, line: LogLine, ts: number | null, role: string, eventType: string,
                  fields: EventFields, artifacts: string[]): EventRow {
  const row: EventRow = { seq: line.seq, ts, vendor, role, event_type: eventType, payload: line.event, artifacts };
  for (const [key, value] of Object.entries(fields)) {
    if (value !== undefined) (row as unknown as Obj)[key] = value;
  }
  return row;
}

function tokenFields(input: unknown, output: unknown, cacheRead: unknown, cacheWrite: unknown): EventFields {
  return { input_tokens: num(input), output_tokens: num(output), cache_read_tokens: num(cacheRead), cache_write_tokens: num(cacheWrite) };
}

// Sums of the rows' token counts, as the opencode and codex rollups take them.
function tokenRollup(rows: EventFields[], cost: number | null, duration: number | null): Rollup {
  const sum = (pick: (r: EventFields) => number | undefined) => rows.reduce((acc, r) => acc + (pick(r) ?? 0), 0);
  return {
    cost_usd: cost,
    duration_ms: duration,
    input_tokens: sum((r) => r.input_tokens),
    output_tokens: sum((r) => r.output_tokens),
    cache_read_tokens: sum((r) => r.cache_read_tokens),
    cache_creation_tokens: sum((r) => r.cache_write_tokens),
  };
}

type HarnessParse = Omit<ParsedLog, "artifacts">;
type Parser = (lines: LogLine[], artifacts: ArtifactRegistry) => HarnessParse;

// ---------------------------------------------------------------------------
// Claude (stream-json)

const CLAUDE_ROLES: Record<string, string> = { assistant: "assistant", user: "tool_result", system: "system", result: "result" };
const CLAUDE_PROVENANCE = ["tools", "plugins", "slash_commands", "apiKeySource", "permissionMode", "capabilities", "memory_paths"];

interface ClaudeUse { block: Obj; artifacts: string[] }
interface ClaudeResult { block: Obj; ts: number | null; artifacts: string[] }

function blocksOf(event: Obj, type: string): Obj[] {
  const content = objAt(event, "message")?.content;
  return Array.isArray(content) ? content.filter((b): b is Obj => isObj(b) && b.type === type) : [];
}

function claudeAssistant(event: Obj, artifacts: ArtifactRegistry, sink: string[], uses: ClaudeUse[]): EventFields {
  const u = objAt(objAt(event, "message"), "usage") ?? {};
  const fields = tokenFields(u.input_tokens, u.output_tokens, u.cache_read_input_tokens, u.cache_creation_input_tokens);
  const texts = blocksOf(event, "text");
  if (texts.length > 0) fields.text = head(texts.map((b) => str(b.text) ?? "").join(""));
  const toolUses = blocksOf(event, "tool_use");
  for (const block of toolUses) {
    const use: ClaudeUse = { block, artifacts: [] };
    artifacts.exciseLongText(block.input, "content", "write_content", use.artifacts, sink);
    artifacts.exciseLongText(block.input, "new_string", "edit_diff", use.artifacts, sink);
    uses.push(use);
  }
  if (toolUses.length === 1) {
    fields.tool_name = str(toolUses[0]!.name);
    fields.tool_call_id = str(toolUses[0]!.id);
  }
  return fields;
}

// Replaces every string leaf found in `strings` with the dedup marker.
function dedupeLeaves(value: unknown, strings: Set<string>): unknown {
  if (typeof value === "string") return strings.has(value) ? { $deduped: "content" } : value;
  if (Array.isArray(value)) return value.map((v) => dedupeLeaves(v, strings));
  if (isObj(value)) {
    for (const [k, v] of Object.entries(value)) value[k] = dedupeLeaves(v, strings);
  }
  return value;
}

function claudeUser(event: Obj, ts: number | null, artifacts: ArtifactRegistry, sink: string[],
                    results: Map<string, ClaudeResult>): EventFields {
  const fields: EventFields = {};
  const toolResults = blocksOf(event, "tool_result");
  const contents = new Set<string>();
  for (const block of toolResults) {
    const result: ClaudeResult = { block, ts, artifacts: [] };
    if (typeof block.content === "string") contents.add(block.content);
    for (const item of Array.isArray(block.content) ? block.content : []) {
      const source = isObj(item) && item.type === "image" ? objAt(item, "source") : undefined;
      artifacts.exciseField(source, "data", "screenshot", str(source?.media_type) ?? "image/png", base64Bytes, result.artifacts, sink);
    }
    const id = str(block.tool_use_id);
    if (id !== undefined && !results.has(id)) results.set(id, result);
  }
  const mirror = objAt(event, "tool_use_result");
  if (mirror) {
    artifacts.exciseField(objAt(mirror, "file"), "base64", "screenshot", "image/png", base64Bytes, sink);
    dedupeLeaves(mirror, contents);
  }
  if (toolResults.length === 1) {
    fields.tool_call_id = str(toolResults[0]!.tool_use_id);
    fields.is_error = typeof toolResults[0]!.is_error === "boolean" ? toolResults[0]!.is_error : undefined;
  }
  return fields;
}

function claudeToolCall(use: ClaudeUse, result: ClaudeResult | undefined): ToolCallRow {
  const failed = result ? result.block.is_error === true : null;
  return {
    tool_call_id: str(use.block.id) ?? "",
    tool_name: str(use.block.name) ?? "",
    input: use.block.input ?? null,
    output: result ? result.block.content ?? null : null,
    status: result ? (failed ? "error" : "ok") : "no_result",
    is_error: failed,
    wallclock_ms: null,
    started_ts: result ? result.ts : null,
    artifacts: [...use.artifacts, ...(result?.artifacts ?? [])],
  };
}

const parseClaude: Parser = (lines, artifacts) => {
  const events: EventRow[] = [];
  const uses: ClaudeUse[] = [];
  const results = new Map<string, ClaudeResult>();
  let init: Obj | undefined;
  let result: Obj | undefined;
  for (const line of lines) {
    const { event } = line;
    const type = str(event.type) ?? "";
    const subtype = str(event.subtype);
    if (type === "system" && subtype === "thinking_tokens") continue;
    if (type === "system" && subtype === "init") init ??= event;
    if (type === "result") result = event;
    const sink: string[] = [];
    let fields: EventFields = {};
    let ts: number | null = null;
    if (type === "assistant") fields = claudeAssistant(event, artifacts, sink, uses);
    if (type === "user") {
      ts = isoToMillis(event.timestamp);
      fields = claudeUser(event, ts, artifacts, sink, results);
    }
    if (type === "result" && typeof event.result === "string") fields.text = head(event.result);
    const eventType = subtype === undefined ? type : `${type}/${subtype}`;
    events.push(eventRow("claude", line, ts, CLAUDE_ROLES[type] ?? "system", eventType, fields, sink));
  }
  const tools = init?.tools;
  return {
    sessionId: str(init?.session_id) || str(result?.session_id) || "",
    era: init && Array.isArray(tools) && tools.length <= 5 ? "legacy" : "post",
    provenance: init ? Object.fromEntries(CLAUDE_PROVENANCE.filter((k) => k in init).map((k) => [k, init[k]])) : null,
    modelUsage: result?.modelUsage ?? null,
    events,
    toolCalls: uses.map((use) => claudeToolCall(use, results.get(str(use.block.id) ?? ""))),
    rollup: null,
  };
};

// ---------------------------------------------------------------------------
// Opencode (JSONL, one fused event per tool call)

const OPENCODE_ROLES: Record<string, string> = { tool_use: "tool_call", text: "assistant", step_start: "system", step_finish: "system" };

function opencodeToolUse(part: Obj | undefined, artifacts: ArtifactRegistry, sink: string[]): ToolCallRow {
  const state = objAt(part, "state") ?? {};
  const metadata = objAt(state, "metadata");
  const filediff = objAt(metadata, "filediff");
  if (filediff && typeof filediff.patch === "string" && filediff.patch === metadata?.diff) filediff.patch = { $deduped: "diff" };
  for (const attachment of Array.isArray(state.attachments) ? state.attachments : []) {
    const uri = isObj(attachment) && typeof attachment.url === "string" ? dataUri(attachment.url) : null;
    if (uri) attachment.url = artifacts.excise("screenshot", uri.mime, uri.bytes, sink);
  }
  artifacts.exciseLongText(state.input, "content", "write_content", sink);
  artifacts.exciseLongText(state.input, "newString", "edit_diff", sink);
  const time = objAt(state, "time");
  const start = num(time?.start);
  const end = num(time?.end);
  const status = str(state.status) ?? "";
  return {
    tool_call_id: str(part?.callID) ?? "",
    tool_name: str(part?.tool) ?? "",
    input: state.input ?? null,
    output: state.output ?? null,
    status,
    is_error: status === "error",
    wallclock_ms: start !== undefined && end !== undefined ? end - start : null,
    started_ts: start ?? null,
    artifacts: [...sink],
  };
}

const parseOpencode: Parser = (lines, artifacts) => {
  const events: EventRow[] = [];
  const toolCalls: ToolCallRow[] = [];
  const steps: EventFields[] = [];
  const stamps: number[] = [];
  let sessionId = "";
  for (const line of lines) {
    const { event } = line;
    const type = str(event.type) ?? "";
    const part = objAt(event, "part");
    const ts = Number.isInteger(event.timestamp) ? (event.timestamp as number) : null;
    if (ts !== null) stamps.push(ts);
    sessionId ||= str(event.sessionID) ?? "";
    const sink: string[] = [];
    let fields: EventFields = {};
    if (type === "tool_use") {
      const call = opencodeToolUse(part, artifacts, sink);
      toolCalls.push(call);
      fields = { tool_name: call.tool_name, tool_call_id: call.tool_call_id, status: call.status, is_error: call.is_error ?? undefined, wallclock_ms: call.wallclock_ms ?? undefined };
    }
    if (type === "text" && typeof part?.text === "string") fields.text = head(part.text);
    if (type === "step_finish") {
      const tokens = objAt(part, "tokens");
      const cache = objAt(tokens, "cache");
      fields = { cost_usd: num(part?.cost), ...tokenFields(tokens?.input, tokens?.output, cache?.read, cache?.write) };
      steps.push(fields);
    }
    events.push(eventRow("opencode", line, ts, OPENCODE_ROLES[type] ?? "system", type, fields, sink));
  }
  const costs = steps.map((s) => s.cost_usd).filter((c) => c !== undefined);
  const cost = costs.length > 0 ? costs.reduce((a, c) => a + c, 0) : null;
  const duration = stamps.length > 0 ? Math.max(...stamps) - Math.min(...stamps) : null;
  return { sessionId, era: "na", provenance: null, modelUsage: null, events, toolCalls, rollup: tokenRollup(steps, cost, duration) };
};

// ---------------------------------------------------------------------------
// Codex (`codex exec --json`)

const ITEM_EVENTS = new Set(["item.started", "item.updated", "item.completed"]);
const CODEX_TOOL_INPUT_DROPPED = new Set(["id", "type", "status", "aggregated_output", "exit_code"]);

function codexRole(type: string, item: Obj | undefined): string {
  if (item) {
    if (item.type === "agent_message" || item.type === "reasoning") return "assistant";
    if (item.type === "error" || item.type === "todo_list") return "system";
    return "tool_call";
  }
  return type === "turn.completed" || type === "turn.failed" ? "result" : "system";
}

function codexIsError(item: Obj): boolean {
  return item.status === "failed" || (Number.isInteger(item.exit_code) && item.exit_code !== 0);
}

function codexToolCall(item: Obj, completed: boolean): ToolCallRow {
  return {
    tool_call_id: str(item.id) ?? "",
    tool_name: str(item.type) ?? "",
    input: Object.fromEntries(Object.entries(item).filter(([k]) => !CODEX_TOOL_INPUT_DROPPED.has(k))),
    output: item.type === "command_execution" ? { aggregated_output: item.aggregated_output, exit_code: item.exit_code } : null,
    status: completed ? str(item.status) ?? "" : "no_result",
    is_error: codexIsError(item),
    wallclock_ms: null,
    started_ts: null,
    artifacts: [],
  };
}

const parseCodex: Parser = (lines) => {
  const events: EventRow[] = [];
  const turns: EventFields[] = [];
  const calls = new Map<string, { item: Obj; completed: boolean }>();
  let sessionId: string | undefined;
  for (const line of lines) {
    const { event } = line;
    const type = str(event.type) ?? "";
    const item = ITEM_EVENTS.has(type) ? objAt(event, "item") ?? {} : undefined;
    const role = codexRole(type, item);
    let fields: EventFields = {};
    if (type === "thread.started") sessionId ??= str(event.thread_id);
    if (role === "assistant" && typeof item?.text === "string") fields.text = head(item.text);
    if (role === "tool_call" && item) {
      const id = str(item.id) ?? "";
      const completed = (calls.get(id)?.completed ?? false) || type === "item.completed";
      calls.set(id, { item, completed });
      fields = { tool_call_id: id, tool_name: str(item.type), status: str(item.status), is_error: codexIsError(item) };
    }
    if (type === "turn.completed") {
      const usage = objAt(event, "usage");
      fields = tokenFields(usage?.input_tokens, usage?.output_tokens, usage?.cached_input_tokens, usage?.cache_write_input_tokens);
      turns.push(fields);
    }
    if (type === "turn.failed") fields = { text: str(objAt(event, "error")?.message), is_error: true };
    if (type === "error") fields.text = str(event.message);
    if (fields.text !== undefined) fields.text = head(fields.text);
    const eventType = item ? `${type}/${str(item.type) ?? ""}` : type;
    events.push(eventRow("codex", line, null, role, eventType, fields, []));
  }
  return {
    sessionId: sessionId ?? "",
    era: "na",
    provenance: null,
    modelUsage: null,
    events,
    toolCalls: [...calls.values()].map((c) => codexToolCall(c.item, c.completed)),
    rollup: tokenRollup(turns, null, null),
  };
};

// ---------------------------------------------------------------------------

const PARSERS: Record<Harness, Parser> = { claude: parseClaude, opencode: parseOpencode, codex: parseCodex };

// Parses one trial log; its bytes are decoded as UTF-8 with replacement.
export function parseLog(harness: Harness, bytes: Uint8Array): ParsedLog {
  const artifacts = new ArtifactRegistry();
  const parsed = PARSERS[harness](eventLines(decodeUtf8(bytes)), artifacts);
  return { ...parsed, artifacts: artifacts.list() };
}
