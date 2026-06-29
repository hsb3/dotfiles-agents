# SSE Format Reference

Server-Sent Events (SSE) protocol details as used by LangGraph's streaming endpoints.

## SSE Protocol Basics

SSE is a text-based protocol where the server pushes events over a single HTTP connection. Each event consists of one or more fields followed by a blank line.

### Event Structure

```
event: <event-type>
data: <json-data>

```

- Lines starting with `event:` specify the event type
- Lines starting with `data:` contain the payload (JSON for LangGraph)
- A blank line (`\n\n`) terminates each event
- Lines starting with `:` are comments (used as keepalives)

### Multi-line Data

Data can span multiple `data:` lines. They are concatenated with newlines:

```
data: line one
data: line two
```

Yields: `"line one\nline two"`

LangGraph typically sends single-line data fields.

## Why Not EventSource

The browser's `EventSource` API only supports GET requests. LangGraph's streaming endpoint requires POST with a JSON body, so you must use `fetch()` with manual SSE parsing.

```typescript
// EventSource cannot send POST with body
// Use fetch + ReadableStream instead
const response = await fetch(url, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload),
});

const reader = response.body.getReader();
```

## LangGraph Event Types

When using `stream_mode: ["messages-tuple"]`, the server sends these event types:

### metadata

Sent once at the start of a stream.

```
event: metadata
data: {"run_id": "1efd8e68-abcd-1234-efgh-567890abcdef", "attempt": 1}
```

### messages

Sent for each message chunk. The data is a two-element JSON array: `[chunk, metadata]`.

```
event: messages
data: [{"content":"Hello","type":"AIMessageChunk","id":"run-abc-0","tool_calls":[],"usage_metadata":null},{"langgraph_node":"agent"}]
```

**Chunk fields (index 0):**

| Field | Type | Description |
|-------|------|-------------|
| `content` | string | The token text (empty string for non-text chunks) |
| `type` | string | `"AIMessageChunk"`, `"HumanMessage"`, `"ToolMessage"` |
| `id` | string | Unique chunk identifier |
| `tool_calls` | array | Tool call objects (empty when streaming text) |
| `usage_metadata` | object/null | Token usage info (usually null during streaming) |

**Metadata fields (index 1):**

| Field | Type | Description |
|-------|------|-------------|
| `langgraph_node` | string | The graph node that produced this chunk |

### end

Sent when the stream completes.

```
event: end
data: null
```

### error

Sent when a server-side error occurs during streaming.

```
event: error
data: {"message": "Error description"}
```

## Message Chunk Types

### AIMessageChunk (text)

Regular text output from the LLM:

```json
{
  "content": "partial token",
  "type": "AIMessageChunk",
  "tool_calls": [],
  "usage_metadata": null
}
```

### AIMessageChunk (tool call)

When the LLM invokes a tool:

```json
{
  "content": "",
  "type": "AIMessageChunk",
  "tool_calls": [
    {
      "name": "search_notes",
      "args": { "query": "meeting notes" },
      "id": "call_abc123"
    }
  ]
}
```

Tool call arguments may arrive across multiple chunks. Only the first chunk for a given tool call contains the `name` field.

### ToolMessage

Result from a tool execution:

```json
{
  "content": "Found 3 matching notes...",
  "type": "ToolMessage",
  "name": "search_notes",
  "tool_call_id": "call_abc123"
}
```

## Parsing Algorithm

```
1. Read bytes from response.body
2. Decode with TextDecoder (stream: true)
3. Append to buffer
4. Split buffer on "\n\n"
5. Keep last element as new buffer (may be incomplete)
6. For each complete part:
   a. Extract "event:" line -> eventType
   b. Extract "data:" line -> eventData
   c. Skip if either is missing
   d. Parse based on eventType
7. Repeat until reader.done
```

## Content-Type

The streaming response uses:

```
Content-Type: text/event-stream
```

The request must use:

```
Content-Type: application/json
```

## Connection Handling

- The connection stays open until the server sends the `end` event or closes it
- Network interruptions will cause `reader.read()` to throw
- Use `AbortController` to cancel the stream from the client side
- Always call `reader.releaseLock()` in a `finally` block
