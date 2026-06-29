# LangGraph API Reference

API endpoints and request/response formats for LangGraph servers deployed via LangGraph Platform or self-hosted with `langgraph-api`.

## Base URL

LangGraph servers typically run on `http://localhost:8123` during development. The base URL is configurable via plugin settings.

## Authentication

Include a bearer token when the server requires authentication:

```
Authorization: Bearer <api-key>
```

## Endpoints

### POST /threads

Create a new conversation thread.

**Request body:** `{}` (empty object is valid)

**Response:**
```json
{
  "thread_id": "uuid-string",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "metadata": {}
}
```

### POST /threads/{thread_id}/runs/stream

Stream a response from the assistant. This is the primary endpoint for chat interactions.

**Path parameters:**
- `thread_id` - UUID identifying the conversation thread

**Request body:**
```json
{
  "assistant_id": "agent",
  "input": {
    "messages": [
      { "role": "user", "content": "Hello" }
    ]
  },
  "config": {
    "configurable": {
      "thread_id": "uuid-string",
      "custom_field": "value"
    }
  },
  "stream_mode": ["messages-tuple"]
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `assistant_id` | string | Yes | Identifier for the agent/assistant on the server |
| `input.messages` | array | Yes | Array of message objects with `role` and `content` |
| `config.configurable` | object | No | Custom configuration passed to the graph |
| `stream_mode` | string[] | Yes | Must include `"messages-tuple"` for token streaming |

**Response:** SSE event stream (see sse-format.md)

### POST /threads/{thread_id}/runs

Run without streaming. Returns the final result only.

**Request body:** Same as `/runs/stream` but without `stream_mode`.

**Response:**
```json
{
  "run_id": "uuid-string",
  "thread_id": "uuid-string",
  "status": "success",
  "result": {
    "messages": [
      { "role": "assistant", "content": "Response text" }
    ]
  }
}
```

### GET /threads/{thread_id}/state

Get the current state of a thread, including message history.

**Response:**
```json
{
  "values": {
    "messages": [
      { "type": "human", "content": "User message" },
      { "type": "ai", "content": "Assistant response" }
    ]
  },
  "next": [],
  "metadata": {}
}
```

### GET /assistants

List available assistants on the server.

**Response:**
```json
[
  {
    "assistant_id": "agent",
    "graph_id": "agent",
    "name": "Default Agent",
    "config": {}
  }
]
```

## Stream Modes

The `stream_mode` field controls what events the server sends:

| Mode | Description |
|------|-------------|
| `"messages-tuple"` | Individual message chunks with metadata (recommended for chat UIs) |
| `"values"` | Full state snapshots after each node execution |
| `"updates"` | Delta updates from each node |
| `"events"` | LangChain callback events |

For token-by-token streaming in chat UIs, use `["messages-tuple"]`.

## Message Roles

Messages sent to the API use standard roles:

| Role | Description |
|------|-------------|
| `user` | Human input |
| `assistant` | AI response |
| `system` | System instructions (placed before conversation) |

## Config.configurable

The `config.configurable` object passes custom data to the LangGraph graph. Common fields:

- `thread_id` - Thread identifier (usually matches the URL parameter)
- `active_note_path` - Path to the currently active Obsidian note
- `vault_name` - Name of the Obsidian vault
- Any custom fields defined by the graph

## Error Responses

Non-streaming errors return standard HTTP status codes:

| Status | Meaning |
|--------|---------|
| 400 | Bad request (invalid input format) |
| 404 | Thread or assistant not found |
| 422 | Validation error (missing required fields) |
| 500 | Server error |

Error body:
```json
{
  "detail": "Error description string"
}
```

## Rate Limits

LangGraph Platform may enforce rate limits. Self-hosted servers do not impose limits by default. Handle 429 responses with exponential backoff if needed.
