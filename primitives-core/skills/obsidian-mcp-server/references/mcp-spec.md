# MCP Protocol Reference for Obsidian Plugins

Quick reference for implementing MCP (Model Context Protocol) servers inside Obsidian plugins using the TypeScript SDK.

## Protocol Overview

MCP uses JSON-RPC 2.0 over HTTP. For Obsidian plugins, use Streamable HTTP transport -- the server listens on a single HTTP endpoint and processes each request independently.

### Request Flow

```
Client                          Plugin (MCP Server)
  |                                   |
  |-- POST /mcp (JSON-RPC) ---------->|
  |                                   |-- parse body
  |                                   |-- create McpServer
  |                                   |-- create transport
  |                                   |-- connect + handle
  |<---------- JSON-RPC response -----|
```

### JSON-RPC Message Format

Every MCP message follows JSON-RPC 2.0:

```json
// Request
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": { "name": "vault_get_note", "arguments": { "path": "note.md" } },
  "id": 1
}

// Success response
{
  "jsonrpc": "2.0",
  "result": {
    "content": [{ "type": "text", "text": "note content here" }]
  },
  "id": 1
}

// Error response
{
  "jsonrpc": "2.0",
  "error": { "code": -32602, "message": "Invalid params" },
  "id": 1
}
```

## Key MCP Methods

Clients use these methods to interact with the server:

| Method | Purpose | When called |
|--------|---------|-------------|
| `initialize` | Capability negotiation | First request from client |
| `tools/list` | Discover available tools | Client setup |
| `tools/call` | Execute a tool | Runtime |

The SDK handles `initialize` and `tools/list` automatically. You only implement tool handlers.

## Stateless vs Stateful Servers

### Stateless (recommended for Obsidian)

Create a fresh McpServer and transport per request. No session tracking needed.

```typescript
const transport = new StreamableHTTPServerTransport({
  sessionIdGenerator: undefined,  // disables sessions
});
```

Why stateless works for Obsidian plugins:
- Single user (the vault owner)
- No need to track conversation state server-side
- Simpler error recovery
- No session cleanup required

### Stateful

Use session IDs when you need server-side state across requests:

```typescript
const transport = new StreamableHTTPServerTransport({
  sessionIdGenerator: () => crypto.randomUUID(),
});
```

Stateful mode requires managing a session map and cleanup. Avoid this unless you have a specific need.

## Tool Registration

### McpServer.registerTool()

```typescript
server.registerTool(
  'tool_name',           // unique identifier
  {
    title: 'Human Name', // display name
    description: '...',  // what the tool does (shown to LLMs)
    inputSchema: {       // zod schema for arguments
      param: z.string().describe('Parameter description'),
    },
  },
  async (args) => {      // handler function
    return {
      content: [{ type: 'text', text: 'result' }],
    };
  }
);
```

### Tool Response Format

Tools return a `CallToolResult`:

```typescript
// Success
{
  content: [
    { type: 'text', text: 'string data here' }
  ]
}

// Error (soft - tool ran but failed)
{
  content: [
    { type: 'text', text: 'Error: file not found' }
  ],
  isError: true
}
```

Content types:
- `text` -- plain text or JSON string (most common)
- `image` -- base64-encoded image with mimeType
- `resource` -- embedded resource reference

For vault tools, always use `text` with JSON-serialized data.

### Input Schema with Zod

The SDK uses zod for input validation. Common patterns:

```typescript
inputSchema: {
  // Required string
  path: z.string().min(1).describe('File path'),

  // Optional with default
  limit: z.number().int().default(10).describe('Max results'),

  // Optional field
  folder: z.string().optional().describe('Folder filter'),

  // Enum
  format: z.enum(['json', 'markdown']).default('json'),

  // Nested object
  filters: z.object({
    type: z.string().optional(),
    status: z.string().optional(),
  }).optional(),

  // Record (arbitrary key-value)
  fields: z.record(z.string(), z.unknown()),
}
```

## Transport: StreamableHTTPServerTransport

The transport bridges HTTP requests to MCP protocol messages.

```typescript
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';

const transport = new StreamableHTTPServerTransport({
  sessionIdGenerator: undefined,  // stateless
});

await mcpServer.connect(transport);
await transport.handleRequest(req, res, parsedBody);
```

### Important: The transport writes the HTTP response

`transport.handleRequest()` writes headers and body to the `res` object. Do not write to `res` after calling it.

## HTTP Server Setup

### Minimal HTTP handler

```typescript
import { createServer } from 'http';

const httpServer = createServer(async (req, res) => {
  if (req.method === 'POST' && req.url === '/mcp') {
    // handle MCP request
  } else {
    res.writeHead(404).end();
  }
});

httpServer.listen(port, '127.0.0.1');
```

### Reading the request body

Node's `http` module provides the body as a stream:

```typescript
function readBody(req: IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', (chunk: Buffer) => { data += chunk.toString(); });
    req.on('end', () => resolve(data));
    req.on('error', reject);
  });
}
```

## Error Codes (JSON-RPC)

| Code | Meaning | When to use |
|------|---------|-------------|
| -32700 | Parse error | Malformed JSON |
| -32600 | Invalid request | Not valid JSON-RPC |
| -32601 | Method not found | Unknown method |
| -32602 | Invalid params | Schema validation failed |
| -32603 | Internal error | Server-side failure |

The SDK handles most of these automatically. Use `isError: true` in tool responses for application-level errors.

## Security

### Localhost binding

Always bind to `127.0.0.1`, never `0.0.0.0`:

```typescript
httpServer.listen(port, '127.0.0.1');
```

### Path validation

Prevent path traversal attacks:

```typescript
if (path.includes('..')) {
  return errorResult('Invalid path');
}
```

### Input constraints

Use zod to enforce limits:

```typescript
path: z.string().min(1).max(500),
limit: z.number().int().min(1).max(100),
```

## Testing with curl

```bash
# Initialize (required first call)
curl -s -X POST http://localhost:5123/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-03-26","clientInfo":{"name":"test","version":"1.0"},"capabilities":{}},"id":1}'

# List available tools
curl -s -X POST http://localhost:5123/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":2}'

# Call a tool
curl -s -X POST http://localhost:5123/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"vault_get_note","arguments":{"path":"README.md"}},"id":3}'
```

Note: In stateless mode, each curl call is independent. No session headers needed.

## SDK Import Paths

```typescript
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
```

These are deep imports (subpath exports). The `.js` extension is required even in TypeScript projects.
