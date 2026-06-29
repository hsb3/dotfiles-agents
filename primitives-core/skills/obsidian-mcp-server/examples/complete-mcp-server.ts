import { createServer, IncomingMessage, ServerResponse } from 'http';
import { Plugin, Notice, TFile } from 'obsidian';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { z } from 'zod';

/**
 * Complete MCP Server Example for Obsidian
 *
 * Hosts a stateless MCP server over Streamable HTTP that exposes
 * vault operations as tools. External AI agents connect via
 * HTTP POST to localhost.
 *
 * Features:
 * - Stateless server (new McpServer per request)
 * - Port retry on EADDRINUSE
 * - Localhost-only binding
 * - Input validation with zod
 * - Plugin lifecycle integration
 */

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

interface McpPluginSettings {
  mcpPort: number;
  enableMcpServer: boolean;
}

const DEFAULT_SETTINGS: McpPluginSettings = {
  mcpPort: 5123,
  enableMcpServer: true,
};

// ---------------------------------------------------------------------------
// MCP Server
// ---------------------------------------------------------------------------

class VaultMcpServer {
  private httpServer: ReturnType<typeof createServer> | null = null;
  private app: Plugin['app'];
  private boundPort: number | null = null;

  constructor(app: Plugin['app']) {
    this.app = app;
  }

  get port(): number | null {
    return this.boundPort;
  }

  async start(port: number): Promise<void> {
    let currentPort = port;
    let attempts = 0;

    while (attempts < 10) {
      try {
        await this.tryListen(currentPort);
        this.boundPort = currentPort;
        console.debug(`MCP server listening on http://127.0.0.1:${currentPort}/mcp`);
        return;
      } catch (error) {
        if ((error as NodeJS.ErrnoException).code === 'EADDRINUSE') {
          currentPort++;
          attempts++;
          continue;
        }
        throw error;
      }
    }

    throw new Error(`Could not bind to any port in range ${port}-${port + 9}`);
  }

  async stop(): Promise<void> {
    if (this.httpServer) {
      this.httpServer.close();
      this.httpServer = null;
      this.boundPort = null;
    }
  }

  private tryListen(port: number): Promise<void> {
    return new Promise((resolve, reject) => {
      const server = createServer((req, res) => this.handleRequest(req, res));
      server.once('error', reject);
      server.listen(port, '127.0.0.1', () => {
        server.removeListener('error', reject);
        this.httpServer = server;
        resolve();
      });
    });
  }

  private async handleRequest(req: IncomingMessage, res: ServerResponse): Promise<void> {
    // Only accept POST /mcp
    if (req.method !== 'POST' || req.url !== '/mcp') {
      res.writeHead(404).end();
      return;
    }

    try {
      const body = await this.readBody(req);
      const parsed = JSON.parse(body);

      // Stateless: fresh server + transport per request
      const mcpServer = this.createMcpServer();
      const transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: undefined, // stateless mode
      });

      await mcpServer.connect(transport);
      await transport.handleRequest(req, res, parsed);
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

    this.registerTools(server);
    return server;
  }

  private registerTools(server: McpServer): void {
    // vault_get_note - Read a note's content and frontmatter
    server.registerTool(
      'vault_get_note',
      {
        title: 'Get vault note',
        description: "Read a note's full content and frontmatter by path",
        inputSchema: {
          path: z.string()
            .min(1)
            .max(500)
            .describe('Path relative to vault root, e.g. "projects/todo.md"'),
        },
      },
      async ({ path }) => {
        if (path.includes('..')) {
          return { content: [{ type: 'text' as const, text: 'Invalid path' }], isError: true };
        }

        const file = this.app.vault.getAbstractFileByPath(path);
        if (!file || !(file instanceof TFile)) {
          return {
            content: [{ type: 'text' as const, text: `File not found: ${path}` }],
            isError: true,
          };
        }

        const content = await this.app.vault.read(file);
        const cache = this.app.metadataCache.getFileCache(file);
        const frontmatter = cache?.frontmatter ?? {};

        return {
          content: [{
            type: 'text' as const,
            text: JSON.stringify({ path: file.path, frontmatter, content }, null, 2),
          }],
        };
      }
    );

    // vault_search - Full-text search across vault
    server.registerTool(
      'vault_search',
      {
        title: 'Search vault',
        description: 'Full-text search across vault notes with optional frontmatter filters',
        inputSchema: {
          query: z.string().min(1).describe('Search text'),
          limit: z.number().int().min(1).max(50).default(10)
            .describe('Max results to return'),
        },
      },
      async ({ query, limit }) => {
        const files = this.app.vault.getMarkdownFiles();
        const results: Array<{ path: string; snippet: string }> = [];

        for (const file of files) {
          if (results.length >= limit) break;

          const content = await this.app.vault.read(file);
          const idx = content.toLowerCase().indexOf(query.toLowerCase());

          if (idx !== -1) {
            const snippet = content.slice(Math.max(0, idx - 50), idx + 150).trim();
            results.push({ path: file.path, snippet });
          }
        }

        return {
          content: [{ type: 'text' as const, text: JSON.stringify(results, null, 2) }],
        };
      }
    );

    // vault_write_note - Create or overwrite a note
    server.registerTool(
      'vault_write_note',
      {
        title: 'Write vault note',
        description: 'Create or overwrite a note at the given path',
        inputSchema: {
          path: z.string().min(1).max(500)
            .describe('Path relative to vault root'),
          content: z.string()
            .describe('Full markdown content including frontmatter'),
        },
      },
      async ({ path, content }) => {
        if (path.includes('..')) {
          return { content: [{ type: 'text' as const, text: 'Invalid path' }], isError: true };
        }

        const existing = this.app.vault.getAbstractFileByPath(path);
        if (existing && existing instanceof TFile) {
          await this.app.vault.modify(existing, content);
        } else {
          await this.app.vault.create(path, content);
        }

        return {
          content: [{ type: 'text' as const, text: `Written: ${path}` }],
        };
      }
    );

    // vault_list_files - List markdown files matching frontmatter criteria
    server.registerTool(
      'vault_list_files',
      {
        title: 'List vault files',
        description: 'List markdown files, optionally filtered by frontmatter fields',
        inputSchema: {
          folder: z.string().optional()
            .describe('Folder prefix to filter by, e.g. "projects/"'),
          type: z.string().optional()
            .describe('Filter by frontmatter "type" field'),
          status: z.string().optional()
            .describe('Filter by frontmatter "status" field'),
        },
      },
      async ({ folder, type, status }) => {
        const files = this.app.vault.getMarkdownFiles();
        const matches: string[] = [];

        for (const file of files) {
          if (folder && !file.path.startsWith(folder)) continue;

          if (type || status) {
            const cache = this.app.metadataCache.getFileCache(file);
            const fm = cache?.frontmatter;
            if (!fm) continue;
            if (type && fm.type !== type) continue;
            if (status && fm.status !== status) continue;
          }

          matches.push(file.path);
        }

        return {
          content: [{ type: 'text' as const, text: JSON.stringify(matches, null, 2) }],
        };
      }
    );
  }
}

// ---------------------------------------------------------------------------
// Plugin
// ---------------------------------------------------------------------------

export default class McpServerPlugin extends Plugin {
  settings: McpPluginSettings;
  private mcpServer: VaultMcpServer | null = null;

  async onload() {
    await this.loadSettings();

    // Command to start/stop MCP server
    this.addCommand({
      id: 'toggle-mcp-server',
      name: 'Toggle MCP server',
      callback: async () => {
        if (this.mcpServer) {
          await this.stopMcpServer();
        } else {
          await this.startMcpServer();
        }
      },
    });

    // Auto-start if enabled
    if (this.settings.enableMcpServer) {
      await this.startMcpServer();
    }
  }

  async onunload() {
    await this.stopMcpServer();
  }

  private async startMcpServer(): Promise<void> {
    if (this.mcpServer) return;

    this.mcpServer = new VaultMcpServer(this.app);
    try {
      await this.mcpServer.start(this.settings.mcpPort);
      new Notice(`MCP server on port ${this.mcpServer.port}`);
    } catch (error) {
      console.error('Failed to start MCP server:', error);
      new Notice('Failed to start MCP server');
      this.mcpServer = null;
    }
  }

  private async stopMcpServer(): Promise<void> {
    if (!this.mcpServer) return;
    await this.mcpServer.stop();
    this.mcpServer = null;
    new Notice('MCP server stopped');
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }
}
