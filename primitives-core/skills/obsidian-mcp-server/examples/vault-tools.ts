import { App, TFile, TFolder } from 'obsidian';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';

/**
 * Vault Tool Patterns for MCP Servers
 *
 * Reusable patterns for exposing Obsidian vault operations as MCP tools.
 * Each function registers one tool onto an McpServer instance.
 *
 * Usage:
 *   const server = new McpServer({ name: 'vault-tools', version: '0.1.0' });
 *   registerGetNote(server, app);
 *   registerUpdateFrontmatter(server, app);
 */

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Resolve a vault path to a TFile, returning an error result if missing. */
function resolveFile(app: App, path: string) {
  if (path.includes('..')) {
    return { error: { content: [{ type: 'text' as const, text: 'Invalid path' }], isError: true as const } };
  }
  const file = app.vault.getAbstractFileByPath(path);
  if (!file || !(file instanceof TFile)) {
    return { error: { content: [{ type: 'text' as const, text: `File not found: ${path}` }], isError: true as const } };
  }
  return { file };
}

function textResult(data: unknown) {
  return { content: [{ type: 'text' as const, text: JSON.stringify(data, null, 2) }] };
}

function errorResult(message: string) {
  return { content: [{ type: 'text' as const, text: message }], isError: true as const };
}

// ---------------------------------------------------------------------------
// Read tools
// ---------------------------------------------------------------------------

/** Read a note's content and frontmatter. */
export function registerGetNote(server: McpServer, app: App): void {
  server.registerTool(
    'vault_get_note',
    {
      title: 'Get vault note',
      description: "Read a note's full content and frontmatter by path",
      inputSchema: {
        path: z.string().min(1).max(500).describe('Path relative to vault root'),
      },
    },
    async ({ path }) => {
      const result = resolveFile(app, path);
      if ('error' in result) return result.error;

      const content = await app.vault.read(result.file);
      const cache = app.metadataCache.getFileCache(result.file);

      return textResult({
        path: result.file.path,
        frontmatter: cache?.frontmatter ?? {},
        content,
      });
    }
  );
}

/** Read only frontmatter from a note (cheaper than full content). */
export function registerGetFrontmatter(server: McpServer, app: App): void {
  server.registerTool(
    'vault_get_frontmatter',
    {
      title: 'Get frontmatter',
      description: 'Read only frontmatter metadata from a note',
      inputSchema: {
        path: z.string().min(1).max(500).describe('Note path'),
      },
    },
    async ({ path }) => {
      const result = resolveFile(app, path);
      if ('error' in result) return result.error;

      const cache = app.metadataCache.getFileCache(result.file);
      return textResult(cache?.frontmatter ?? {});
    }
  );
}

// ---------------------------------------------------------------------------
// Write tools
// ---------------------------------------------------------------------------

/** Create or overwrite a note. */
export function registerWriteNote(server: McpServer, app: App): void {
  server.registerTool(
    'vault_write_note',
    {
      title: 'Write vault note',
      description: 'Create or overwrite a note at the given path',
      inputSchema: {
        path: z.string().min(1).max(500).describe('Note path'),
        content: z.string().describe('Full markdown content'),
      },
    },
    async ({ path, content }) => {
      if (path.includes('..')) return errorResult('Invalid path');

      const existing = app.vault.getAbstractFileByPath(path);
      if (existing && existing instanceof TFile) {
        await app.vault.modify(existing, content);
      } else {
        await app.vault.create(path, content);
      }

      return textResult({ written: path });
    }
  );
}

/** Update specific frontmatter fields without touching body content. */
export function registerUpdateFrontmatter(server: McpServer, app: App): void {
  server.registerTool(
    'vault_update_frontmatter',
    {
      title: 'Update frontmatter',
      description: 'Merge key-value pairs into a note\'s frontmatter',
      inputSchema: {
        path: z.string().min(1).max(500).describe('Note path'),
        fields: z.record(z.string(), z.unknown())
          .describe('Key-value pairs to merge into frontmatter'),
      },
    },
    async ({ path, fields }) => {
      const result = resolveFile(app, path);
      if ('error' in result) return result.error;

      await app.fileManager.processFrontMatter(result.file, (fm) => {
        Object.assign(fm, fields);
      });

      return textResult({ updated: path, fields: Object.keys(fields) });
    }
  );
}

/** Append text to the end of a note. */
export function registerAppendNote(server: McpServer, app: App): void {
  server.registerTool(
    'vault_append_note',
    {
      title: 'Append to note',
      description: 'Append text to the end of an existing note',
      inputSchema: {
        path: z.string().min(1).max(500).describe('Note path'),
        text: z.string().describe('Text to append'),
      },
    },
    async ({ path, text }) => {
      const result = resolveFile(app, path);
      if ('error' in result) return result.error;

      await app.vault.append(result.file, '\n' + text);
      return textResult({ appended: path });
    }
  );
}

// ---------------------------------------------------------------------------
// Search / query tools
// ---------------------------------------------------------------------------

/** Full-text search across vault notes. */
export function registerSearch(server: McpServer, app: App): void {
  server.registerTool(
    'vault_search',
    {
      title: 'Search vault',
      description: 'Full-text search across markdown notes',
      inputSchema: {
        query: z.string().min(1).describe('Search text'),
        limit: z.number().int().min(1).max(50).default(10).describe('Max results'),
      },
    },
    async ({ query, limit }) => {
      const files = app.vault.getMarkdownFiles();
      const results: Array<{ path: string; snippet: string }> = [];
      const lowerQuery = query.toLowerCase();

      for (const file of files) {
        if (results.length >= limit) break;

        const content = await app.vault.read(file);
        const idx = content.toLowerCase().indexOf(lowerQuery);

        if (idx !== -1) {
          const snippet = content.slice(Math.max(0, idx - 50), idx + 150).trim();
          results.push({ path: file.path, snippet });
        }
      }

      return textResult(results);
    }
  );
}

/** Query notes by frontmatter field values. */
export function registerQueryByFrontmatter(server: McpServer, app: App): void {
  server.registerTool(
    'vault_query',
    {
      title: 'Query by frontmatter',
      description: 'Find notes matching frontmatter field values',
      inputSchema: {
        filters: z.record(z.string(), z.string())
          .describe('Frontmatter field-value pairs to match'),
        folder: z.string().optional()
          .describe('Restrict to folder prefix'),
      },
    },
    async ({ filters, folder }) => {
      const files = app.vault.getMarkdownFiles();
      const matches: Array<{ path: string; frontmatter: Record<string, unknown> }> = [];

      for (const file of files) {
        if (folder && !file.path.startsWith(folder)) continue;

        const cache = app.metadataCache.getFileCache(file);
        const fm = cache?.frontmatter;
        if (!fm) continue;

        const allMatch = Object.entries(filters).every(([k, v]) => fm[k] === v);
        if (allMatch) {
          matches.push({ path: file.path, frontmatter: fm });
        }
      }

      return textResult(matches);
    }
  );
}

/** List folder contents with file metadata. */
export function registerListFolder(server: McpServer, app: App): void {
  server.registerTool(
    'vault_list_folder',
    {
      title: 'List folder',
      description: 'List files and subfolders in a vault folder',
      inputSchema: {
        folder: z.string().default('/').describe('Folder path, "/" for root'),
      },
    },
    async ({ folder }) => {
      const normalizedPath = folder === '/' ? '' : folder;
      const abstractFile = normalizedPath
        ? app.vault.getAbstractFileByPath(normalizedPath)
        : app.vault.getRoot();

      if (!abstractFile || !(abstractFile instanceof TFolder)) {
        return errorResult(`Folder not found: ${folder}`);
      }

      const entries = abstractFile.children.map((child) => ({
        name: child.name,
        path: child.path,
        type: child instanceof TFolder ? 'folder' : 'file',
      }));

      return textResult(entries);
    }
  );
}

// ---------------------------------------------------------------------------
// Batch registration
// ---------------------------------------------------------------------------

/** Register all vault tools at once. */
export function registerAllVaultTools(server: McpServer, app: App): void {
  registerGetNote(server, app);
  registerGetFrontmatter(server, app);
  registerWriteNote(server, app);
  registerUpdateFrontmatter(server, app);
  registerAppendNote(server, app);
  registerSearch(server, app);
  registerQueryByFrontmatter(server, app);
  registerListFolder(server, app);
}
