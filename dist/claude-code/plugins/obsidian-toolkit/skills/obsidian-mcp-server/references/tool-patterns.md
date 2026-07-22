# MCP Tool Patterns for Obsidian Vaults

Patterns and conventions for designing MCP tools that expose Obsidian vault operations.

## Tool Naming

Use `vault_` prefix with snake_case verb-noun format:

```
vault_get_note        -- read a single note
vault_search          -- search across notes
vault_write_note      -- create or overwrite
vault_append_note     -- append to existing
vault_list_folder     -- list directory contents
vault_query           -- query by metadata
vault_update_frontmatter -- modify frontmatter
vault_delete_note     -- remove a note
```

Keep names short and predictable. LLMs use tool names to decide which tool to call, so clarity matters.

## Tool Description Guidelines

Descriptions are shown to LLMs. Write them for an AI agent, not a human developer:

```typescript
// Good: tells the agent what it gets back
description: "Read a note's full markdown content and frontmatter metadata by path"

// Bad: too vague
description: "Gets a note"

// Good: explains constraints
description: "Full-text search across markdown notes. Returns up to `limit` results with surrounding context snippets."

// Bad: implementation detail
description: "Iterates through vault files and uses indexOf"
```

## Common Tool Shapes

### Read single resource

Pattern: accept a path, return structured data.

```typescript
server.registerTool(
  'vault_get_note',
  {
    title: 'Get vault note',
    description: "Read a note's content and frontmatter by path",
    inputSchema: {
      path: z.string().min(1).max(500).describe('Note path relative to vault root'),
    },
  },
  async ({ path }) => {
    // 1. Validate
    if (path.includes('..')) return errorResult('Invalid path');

    // 2. Resolve
    const file = app.vault.getAbstractFileByPath(path);
    if (!file || !(file instanceof TFile)) return errorResult(`Not found: ${path}`);

    // 3. Read
    const content = await app.vault.read(file);
    const cache = app.metadataCache.getFileCache(file);

    // 4. Return structured
    return textResult({
      path: file.path,
      frontmatter: cache?.frontmatter ?? {},
      content,
    });
  }
);
```

### Write / mutate

Pattern: accept path + data, return confirmation.

```typescript
server.registerTool(
  'vault_write_note',
  {
    title: 'Write vault note',
    description: 'Create or overwrite a note',
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
```

### Search / query

Pattern: accept query params, return array of matches.

```typescript
server.registerTool(
  'vault_search',
  {
    title: 'Search vault',
    description: 'Search note content, returns matching paths with snippets',
    inputSchema: {
      query: z.string().min(1).describe('Search text'),
      limit: z.number().int().min(1).max(50).default(10).describe('Max results'),
    },
  },
  async ({ query, limit }) => {
    const files = app.vault.getMarkdownFiles();
    const results: Array<{ path: string; snippet: string }> = [];
    const lower = query.toLowerCase();

    for (const file of files) {
      if (results.length >= limit) break;
      const content = await app.vault.read(file);
      const idx = content.toLowerCase().indexOf(lower);
      if (idx !== -1) {
        results.push({
          path: file.path,
          snippet: content.slice(Math.max(0, idx - 50), idx + 150).trim(),
        });
      }
    }

    return textResult(results);
  }
);
```

### List / enumerate

Pattern: accept optional filters, return array of paths or metadata.

```typescript
server.registerTool(
  'vault_list_folder',
  {
    title: 'List folder',
    description: 'List files and subfolders in a vault directory',
    inputSchema: {
      folder: z.string().default('/').describe('Folder path'),
    },
  },
  async ({ folder }) => {
    const target = folder === '/'
      ? app.vault.getRoot()
      : app.vault.getAbstractFileByPath(folder);

    if (!target || !(target instanceof TFolder)) {
      return errorResult(`Folder not found: ${folder}`);
    }

    const entries = target.children.map((child) => ({
      name: child.name,
      path: child.path,
      type: child instanceof TFolder ? 'folder' : 'file',
    }));

    return textResult(entries);
  }
);
```

## Frontmatter Operations

### Reading frontmatter

Use `metadataCache` for parsed frontmatter (avoids re-parsing YAML):

```typescript
const cache = app.metadataCache.getFileCache(file);
const frontmatter = cache?.frontmatter ?? {};
```

### Writing frontmatter

Use `processFrontMatter` for safe frontmatter mutations:

```typescript
await app.fileManager.processFrontMatter(file, (fm) => {
  fm.status = 'done';
  fm.updated = new Date().toISOString();
});
```

This method handles YAML serialization, preserves field order, and avoids corrupting the note body.

### Querying by frontmatter

Filter files by frontmatter values using the metadata cache:

```typescript
const files = app.vault.getMarkdownFiles();
const matches = [];

for (const file of files) {
  const cache = app.metadataCache.getFileCache(file);
  const fm = cache?.frontmatter;
  if (fm?.type === 'task' && fm?.status === 'active') {
    matches.push(file.path);
  }
}
```

## Error Handling Pattern

Use `isError: true` for application errors. Throw only for unexpected failures.

```typescript
async ({ path }) => {
  try {
    // Validation errors -> isError response
    if (path.includes('..')) {
      return { content: [{ type: 'text', text: 'Invalid path' }], isError: true };
    }

    const file = app.vault.getAbstractFileByPath(path);
    if (!file || !(file instanceof TFile)) {
      return { content: [{ type: 'text', text: `Not found: ${path}` }], isError: true };
    }

    // Happy path
    const content = await app.vault.read(file);
    return { content: [{ type: 'text', text: content }] };

  } catch (error) {
    // Unexpected errors -> also isError, but log for debugging
    console.error('vault_get_note error:', error);
    return {
      content: [{ type: 'text', text: `Error: ${error instanceof Error ? error.message : 'Unknown'}` }],
      isError: true,
    };
  }
}
```

The `isError` flag tells the LLM client that the tool invocation failed, so it can retry or adjust its approach.

## Helper Functions

Extract common patterns into helpers to keep tool handlers focused:

```typescript
function resolveFile(app: App, path: string) {
  if (path.includes('..')) {
    return { error: errorResult('Invalid path') };
  }
  const file = app.vault.getAbstractFileByPath(path);
  if (!file || !(file instanceof TFile)) {
    return { error: errorResult(`Not found: ${path}`) };
  }
  return { file };
}

function textResult(data: unknown) {
  return { content: [{ type: 'text' as const, text: JSON.stringify(data, null, 2) }] };
}

function errorResult(message: string) {
  return { content: [{ type: 'text' as const, text: message }], isError: true as const };
}
```

## Tool Composition

For complex operations, compose vault API calls within a single tool rather than creating many fine-grained tools. LLMs work better with fewer, more capable tools.

```typescript
// Good: one tool that handles the full operation
server.registerTool('vault_update_frontmatter', ...);

// Avoid: splitting into get-frontmatter + set-frontmatter + save
// which forces the LLM to orchestrate multiple calls
```

However, keep read and write tools separate. An LLM should be able to read without risking mutation.

## Performance Considerations

### Avoid reading all files

For large vaults, reading every file is slow. Use `metadataCache` for metadata queries and only read file content when necessary:

```typescript
// Fast: metadata cache lookup
const cache = app.metadataCache.getFileCache(file);
const title = cache?.frontmatter?.title;

// Slow: reading full content
const content = await app.vault.read(file);
```

### Add result limits

Always cap search results to prevent massive responses:

```typescript
inputSchema: {
  limit: z.number().int().min(1).max(50).default(10),
}
```

### Return concise data

LLMs have context limits. Return only what the agent needs:

```typescript
// Good: path + snippet
results.push({ path: file.path, snippet });

// Avoid: full content of every matching file
results.push({ path: file.path, fullContent: content });
```
