---
name: obsidian-mcp-server
description: This skill should be used when the user asks to "add MCP server", "Model Context Protocol", "expose vault tools", "Streamable HTTP", "MCP tools", or mentions integrating MCP servers in Obsidian plugins to expose vault operations.
---

# Obsidian MCP Server

Provides guidance for setting up MCP (Model Context Protocol) servers inside Obsidian plugins using Streamable HTTP transport, enabling AI agents to access vault operations.

## Architecture

The plugin hosts an MCP server that external agents connect to:

```
AI Agent / LangGraph (MCP Client)
    |
    | HTTP POST to localhost:5123/mcp
    v
Obsidian Plugin (MCP Server)
    |
    | app.vault, app.metadataCache
    v
Obsidian Vault
```

**Connection direction:** Agent → Plugin (not plugin → agent)

## SDK Setup

Install MCP SDK v2:

```bash
npm install @modelcontextprotocol/sdk zod
```

**Dependencies:**
- `@modelcontextprotocol/sdk` - MCP server and transports
- `zod` - Required peer dependency (v3.25+)

## Stateless Server Pattern

For single-user plugins, create a new server per request:

```typescript
import { createServer, IncomingMessage, ServerResponse } from 'http';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { z } from 'zod';
import { App } from 'obsidian';

export class VaultMcpServer {
  private httpServer: ReturnType<typeof createServer> | null = null;
  private app: App;

  constructor(app: App) {
    this.app = app;
  }

  async start(port: number): Promise<void> {
    this.httpServer = createServer(async (req: IncomingMessage, res: ServerResponse) => {
      if (req.method === 'POST' && req.url === '/mcp') {
        await this.handleMcpRequest(req, res);
      } else {
        res.writeHead(404).end();
      }
    });

    this.httpServer.listen(port, '127.0.0.1');
    console.debug(`MCP server listening on http://127.0.0.1:${port}/mcp`);
  }

  async stop(): Promise<void> {
    if (this.httpServer) {
      this.httpServer.close();
      this.httpServer = null;
    }
  }

  private async handleMcpRequest(
    req: IncomingMessage,
    res: ServerResponse
  ): Promise<void> {
    try {
      const body = await this.readBody(req);
      const parsedBody = JSON.parse(body);

      // Create fresh server + transport per request (stateless)
      const mcpServer = this.createMcpServer();
      const transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: undefined,  // Stateless mode
      });

      await mcpServer.connect(transport);
      await transport.handleRequest(req, res, parsedBody);
    } catch (error) {
      console.error('MCP request error:', error);
      if (!res.headersSent) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
          jsonrpc: '2.0',
          error: { code: -32603, message: 'Internal server error' },
          id: null,
        }));
      }
    }
  }

  private readBody(req: IncomingMessage): Promise<string> {
    return new Promise((resolve, reject) => {
      let data = '';
      req.on('data', (chunk: Buffer) => { data += chunk.toString(); });
      req.on('end', () => resolve(data));
      req.on('error', reject);
    });
  }

  private createMcpServer(): McpServer {
    const server = new McpServer({
      name: 'vault-tools',
      version: '0.1.0',
    });

    this.registerVaultTools(server);

    return server;
  }

  private registerVaultTools(server: McpServer): void {
    // Tool registration here
  }
}
```

## Tool Registration

Register vault operation tools:

```typescript
private registerVaultTools(server: McpServer): void {
  // vault_get_note - Read note content and frontmatter
  server.registerTool(
    'vault_get_note',
    {
      title: 'Get vault note',
      description: 'Read a note\'s full content and frontmatter by path',
      inputSchema: {
        path: z.string().describe(
          'Path to note relative to vault root, e.g. "projects/note.md"'
        ),
      },
    },
    async ({ path }) => {
      const file = this.app.vault.getAbstractFileByPath(path);

      if (!file || !(file instanceof TFile)) {
        return {
          content: [{
            type: 'text',
            text: `Error: File not found: ${path}`
          }],
          isError: true,
        };
      }

      const content = await this.app.vault.read(file);
      const cache = this.app.metadataCache.getFileCache(file);
      const frontmatter = cache?.frontmatter ?? {};

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            path: file.path,
            frontmatter,
            content,
          }, null, 2),
        }],
      };
    }
  );

  // vault_search - Search vault content
  server.registerTool(
    'vault_search',
    {
      title: 'Search vault',
      description: 'Full-text search across vault notes',
      inputSchema: {
        query: z.string().describe('Search query'),
        filters: z.object({
          type: z.string().optional(),
          status: z.string().optional(),
        }).optional().describe('Frontmatter filters'),
      },
    },
    async ({ query, filters }) => {
      const files = this.app.vault.getMarkdownFiles();
      const results: Array<{ path: string; snippet: string }> = [];

      for (const file of files) {
        const content = await this.app.vault.read(file);

        // Apply filters if provided
        if (filters) {
          const cache = this.app.metadataCache.getFileCache(file);
          const fm = cache?.frontmatter;

          if (filters.type && fm?.type !== filters.type) continue;
          if (filters.status && fm?.status !== filters.status) continue;
        }

        // Simple text search
        if (content.toLowerCase().includes(query.toLowerCase())) {
          const index = content.toLowerCase().indexOf(query.toLowerCase());
          const snippet = content.slice(Math.max(0, index - 50), index + 150);

          results.push({
            path: file.path,
            snippet: snippet.trim(),
          });
        }
      }

      return {
        content: [{
          type: 'text',
          text: JSON.stringify(results, null, 2),
        }],
      };
    }
  );
}
```

## Lifecycle Management

Integrate with plugin lifecycle:

```typescript
export default class MyPlugin extends Plugin {
  private mcpServer: VaultMcpServer | null = null;

  async onload() {
    await this.loadSettings();

    // Don't start MCP server immediately
    // Start lazily when first needed
  }

  async onunload() {
    // Stop MCP server
    if (this.mcpServer) {
      await this.mcpServer.stop();
    }
  }

  async startMcpServer(): Promise<void> {
    if (this.mcpServer) return;  // Already started

    this.mcpServer = new VaultMcpServer(this.app);

    try {
      await this.mcpServer.start(this.settings.mcpPort);
      new Notice(`MCP server started on port ${this.settings.mcpPort}`);
    } catch (error) {
      console.error('Failed to start MCP server:', error);
      new Notice('Failed to start MCP server. See console for details.');
    }
  }
}
```

## Port Configuration

Make port configurable with fallback:

```typescript
async start(port: number): Promise<void> {
  let currentPort = port;
  let attempts = 0;

  while (attempts < 10) {
    try {
      this.httpServer = createServer(this.handleRequest.bind(this));
      this.httpServer.listen(currentPort, '127.0.0.1');
      console.debug(`MCP server on http://127.0.0.1:${currentPort}/mcp`);
      return;
    } catch (error) {
      if ((error as any).code === 'EADDRINUSE') {
        currentPort++;
        attempts++;
        continue;
      }
      throw error;
    }
  }

  throw new Error(`Could not bind to any port in range ${port}-${port + 10}`);
}
```

## Security Considerations

**Always bind to localhost:**

```typescript
// ✅ CORRECT - localhost only
this.httpServer.listen(port, '127.0.0.1');

// ❌ WRONG - exposed to network
this.httpServer.listen(port, '0.0.0.0');
```

**Validate all inputs:**

```typescript
server.registerTool(
  'vault_get_note',
  {
    inputSchema: {
      path: z.string()
        .min(1)
        .max(500)
        .regex(/^[a-zA-Z0-9\/_\-\.]+$/)  // Safe paths only
        .describe('Note path'),
    },
  },
  async ({ path }) => {
    // Additional validation
    if (path.includes('..')) {
      return { content: [{ type: 'text', text: 'Invalid path' }], isError: true };
    }

    // ... implementation
  }
);
```

## Common Vault Tools

Useful tool patterns:

### Get Frontmatter Only

```typescript
server.registerTool(
  'vault_get_frontmatter',
  {
    title: 'Get frontmatter',
    description: 'Read only frontmatter from a note',
    inputSchema: {
      path: z.string(),
    },
  },
  async ({ path }) => {
    const file = this.app.vault.getAbstractFileByPath(path);
    if (!file || !(file instanceof TFile)) {
      return { content: [{ type: 'text', text: 'File not found' }], isError: true };
    }

    const cache = this.app.metadataCache.getFileCache(file);
    const frontmatter = cache?.frontmatter ?? {};

    return {
      content: [{
        type: 'text',
        text: JSON.stringify(frontmatter, null, 2),
      }],
    };
  }
);
```

### List Files by Query

```typescript
server.registerTool(
  'vault_list_by_query',
  {
    title: 'List files by frontmatter query',
    description: 'Query notes by frontmatter fields',
    inputSchema: {
      filters: z.object({
        type: z.string().optional(),
        status: z.string().optional(),
        project: z.string().optional(),
      }),
    },
  },
  async ({ filters }) => {
    const files = this.app.vault.getMarkdownFiles();
    const matches: string[] = [];

    for (const file of files) {
      const cache = this.app.metadataCache.getFileCache(file);
      const fm = cache?.frontmatter;

      if (!fm) continue;

      let match = true;
      if (filters.type && fm.type !== filters.type) match = false;
      if (filters.status && fm.status !== filters.status) match = false;
      if (filters.project && fm.project !== filters.project) match = false;

      if (match) matches.push(file.path);
    }

    return {
      content: [{
        type: 'text',
        text: JSON.stringify(matches, null, 2),
      }],
    };
  }
);
```

## Error Handling

Handle errors gracefully:

```typescript
async ({ path }) => {
  try {
    const file = this.app.vault.getAbstractFileByPath(path);
    if (!file || !(file instanceof TFile)) {
      return {
        content: [{ type: 'text', text: `File not found: ${path}` }],
        isError: true,
      };
    }

    const content = await this.app.vault.read(file);
    return {
      content: [{ type: 'text', text: content }],
    };
  } catch (error) {
    console.error('Tool error:', error);
    return {
      content: [{
        type: 'text',
        text: `Error: ${error instanceof Error ? error.message : 'Unknown'}`
      }],
      isError: true,
    };
  }
}
```

## Testing

Test MCP server with curl:

```bash
# Test vault_get_note tool
curl -X POST http://localhost:5123/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "vault_get_note",
      "arguments": {
        "path": "README.md"
      }
    },
    "id": 1
  }'
```

## Additional Resources

### Examples

Working examples in `examples/`:
- **`complete-mcp-server.ts`** - Full MCP server implementation
- **`vault-tools.ts`** - Common vault tool patterns

### Reference Files

For detailed information:
- **`references/mcp-spec.md`** - MCP protocol details
- **`references/tool-patterns.md`** - Advanced tool patterns

### Official Resources

- [MCP Specification](https://modelcontextprotocol.io/)
- [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)

## Next Steps

After setting up MCP server:
1. Connect from LangGraph with `langgraph-sse-client` skill
2. Test tools from AI agents
3. Add more vault operations as needed
