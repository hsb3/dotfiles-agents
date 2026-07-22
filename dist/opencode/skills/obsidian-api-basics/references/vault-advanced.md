# Advanced Vault Operations

Comprehensive reference for advanced file system operations, metadata handling, and content processing in Obsidian plugins.

## Vault Architecture

The Vault is Obsidian's abstraction over the file system. It provides a unified API that works across desktop (Node.js fs) and mobile (Capacitor) platforms. All file operations should go through the Vault API rather than using Node.js `fs` directly to ensure cross-platform compatibility.

### Vault Adapter

The `vault.adapter` provides lower-level file system access when needed:

```typescript
interface DataAdapter {
  getName(): string;                                    // Vault name
  exists(normalizedPath: string): Promise<boolean>;
  read(normalizedPath: string): Promise<string>;
  readBinary(normalizedPath: string): Promise<ArrayBuffer>;
  write(normalizedPath: string, data: string, options?: DataWriteOptions): Promise<void>;
  writeBinary(normalizedPath: string, data: ArrayBuffer, options?: DataWriteOptions): Promise<void>;
  append(normalizedPath: string, data: string, options?: DataWriteOptions): Promise<void>;
  mkdir(normalizedPath: string): Promise<void>;
  trashSystem(normalizedPath: string): Promise<boolean>;
  trashLocal(normalizedPath: string): Promise<void>;
  remove(normalizedPath: string): Promise<void>;
  rmdir(normalizedPath: string, recursive: boolean): Promise<void>;
  list(normalizedPath: string): Promise<ListedFiles>;
  stat(normalizedPath: string): Promise<Stat | null>;
  copy(normalizedPath: string, normalizedNewPath: string): Promise<void>;
  rename(normalizedPath: string, normalizedNewPath: string): Promise<void>;
  getResourcePath(normalizedPath: string): string;      // Get platform URL for resources
  getBasePath(): string;                                 // Absolute path to vault root
}

interface ListedFiles {
  files: string[];    // File paths
  folders: string[];  // Folder paths
}
```

Use `vault.adapter` for operations not covered by the high-level Vault API, such as checking if a path exists or getting the base path:

```typescript
// Check if file exists before creating
const exists = await this.app.vault.adapter.exists('path/to/file.md');
if (!exists) {
  await this.app.vault.create('path/to/file.md', 'Initial content');
}

// Get vault root path (desktop only, useful for spawning processes)
const basePath = this.app.vault.adapter.getBasePath();
```

## Reading Files

### Vault.read vs Vault.cachedRead

```typescript
// Always reads from disk - guaranteed fresh content
const content = await this.app.vault.read(file);

// May return cached content - faster but potentially stale
const cached = await this.app.vault.cachedRead(file);
```

Use `cachedRead` for performance when displaying content, `read` when you need guaranteed freshness (e.g., before modifying a file).

### Reading Binary Files

```typescript
const buffer = await this.app.vault.readBinary(file);

// Convert to useful formats
const text = new TextDecoder().decode(buffer);
const blob = new Blob([buffer]);
const base64 = arrayBufferToBase64(buffer);

// Helper for base64 conversion
function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}
```

## Writing Files

### Create vs Modify

```typescript
// Create a new file - throws if file already exists
const newFile = await this.app.vault.create('path/to/new.md', 'Content here');

// Modify existing file - replaces entire content
await this.app.vault.modify(existingFile, 'New content');

// Append to existing file
await this.app.vault.append(existingFile, '\n\nAppended content');
```

### DataWriteOptions

```typescript
interface DataWriteOptions {
  ctime?: number;   // Override creation time
  mtime?: number;   // Override modification time
}
```

### Safe File Creation Pattern

```typescript
async createOrGet(path: string, content: string): Promise<TFile> {
  const normalized = normalizePath(path);
  const existing = this.app.vault.getFileByPath(normalized);
  if (existing) return existing;

  // Ensure parent folder exists
  const dir = normalized.substring(0, normalized.lastIndexOf('/'));
  if (dir) {
    const folder = this.app.vault.getFolderByPath(dir);
    if (!folder) {
      await this.app.vault.createFolder(dir);
    }
  }

  return await this.app.vault.create(normalized, content);
}
```

### Creating Folders Recursively

The vault's `createFolder` does not create intermediate directories. Use this pattern:

```typescript
async ensureFolderExists(path: string): Promise<void> {
  const parts = path.split('/');
  let current = '';

  for (const part of parts) {
    current = current ? `${current}/${part}` : part;
    const folder = this.app.vault.getFolderByPath(current);
    if (!folder) {
      await this.app.vault.createFolder(current);
    }
  }
}
```

## File Operations

### Rename and Move

```typescript
// Rename a file (updates links if using fileManager)
await this.app.vault.rename(file, 'new-folder/new-name.md');

// Use fileManager for renaming to also update all links
await this.app.fileManager.renameFile(file, 'new-folder/new-name.md');
```

Always prefer `fileManager.renameFile` over `vault.rename` when the file may be linked from other files. The FileManager updates all references automatically.

### Copy

```typescript
const copy = await this.app.vault.copy(file, 'path/to/copy.md');
```

### Delete and Trash

```typescript
// Move to Obsidian trash (.trash folder)
await this.app.vault.trash(file, false);

// Move to system trash (recycle bin)
await this.app.vault.trash(file, true);

// Permanent delete (use with caution)
await this.app.vault.delete(file);

// Force delete even if file is not tracked
await this.app.vault.delete(file, true);
```

Always prefer `trash` over `delete` to give users a chance to recover files.

## Querying Files

### By Path

```typescript
// Returns TAbstractFile (could be file or folder) or null
const abstract = this.app.vault.getAbstractFileByPath('folder/note.md');

// Type-specific lookups (returns null if wrong type or not found)
const file: TFile | null = this.app.vault.getFileByPath('folder/note.md');
const folder: TFolder | null = this.app.vault.getFolderByPath('folder');
```

### Listing Files

```typescript
// All markdown files
const mdFiles = this.app.vault.getMarkdownFiles();

// All files (including images, PDFs, etc.)
const allFiles = this.app.vault.getFiles();

// All files and folders
const everything = this.app.vault.getAllLoadedFiles();
```

### Filtering and Searching

```typescript
// Find files by extension
const images = this.app.vault.getFiles()
  .filter(f => ['png', 'jpg', 'jpeg', 'gif', 'svg'].includes(f.extension));

// Find files in a specific folder
const notesInFolder = this.app.vault.getMarkdownFiles()
  .filter(f => f.path.startsWith('Projects/'));

// Find files modified recently (last 24 hours)
const recent = this.app.vault.getMarkdownFiles()
  .filter(f => (Date.now() - f.stat.mtime) < 86400000);

// Sort by modification time
const sorted = this.app.vault.getMarkdownFiles()
  .sort((a, b) => b.stat.mtime - a.stat.mtime);
```

### Finding Files by Link

```typescript
// Resolve an internal link path to a file
const target = this.app.metadataCache.getFirstLinkpathDest(
  'note-name',    // Link text (without [[]])
  'source/path'   // Source file path for relative link resolution
);

if (target) {
  const content = await this.app.vault.read(target);
}
```

## Frontmatter Operations

### Reading Frontmatter

```typescript
// Via MetadataCache (fast, no file I/O)
const cache = this.app.metadataCache.getFileCache(file);
const frontmatter = cache?.frontmatter;

if (frontmatter) {
  const title = frontmatter.title;
  const tags = frontmatter.tags;    // Array of tags
  const custom = frontmatter.myField;
}
```

### Writing Frontmatter

Use `fileManager.processFrontMatter` for safe YAML manipulation:

```typescript
// Add or update frontmatter fields
await this.app.fileManager.processFrontMatter(file, (fm) => {
  fm.status = 'reviewed';
  fm.reviewDate = new Date().toISOString();

  // Initialize arrays safely
  fm.tags = fm.tags || [];
  if (!fm.tags.includes('processed')) {
    fm.tags.push('processed');
  }
});

// Remove a frontmatter field
await this.app.fileManager.processFrontMatter(file, (fm) => {
  delete fm.oldField;
});
```

This method handles YAML parsing, serialization, and preserves other file content.

### Manual Frontmatter Parsing

For cases where you need to parse frontmatter from raw content:

```typescript
import { parseYaml, stringifyYaml } from 'obsidian';

function extractFrontmatter(content: string): { frontmatter: any; body: string } | null {
  const match = content.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  if (!match) return null;

  return {
    frontmatter: parseYaml(match[1]),
    body: match[2]
  };
}

function replaceFrontmatter(content: string, newFm: any): string {
  const yaml = stringifyYaml(newFm);
  const body = content.replace(/^---\n[\s\S]*?\n---\n/, '');
  return `---\n${yaml}---\n${body}`;
}
```

## MetadataCache Deep Dive

### CachedMetadata Structure

```typescript
interface CachedMetadata {
  // YAML frontmatter as parsed object
  frontmatter?: FrontMatterCache;
  frontmatterPosition?: Pos;
  frontmatterLinks?: FrontmatterLinkCache[];

  // Document structure
  headings?: HeadingCache[];
  sections?: SectionCache[];
  listItems?: ListItemCache[];

  // References
  links?: LinkCache[];           // [[internal links]]
  embeds?: EmbedCache[];         // ![[embedded content]]
  tags?: TagCache[];             // #tags in body (not frontmatter)

  // Blocks
  blocks?: Record<string, BlockCache>;  // ^block-ids
}

interface HeadingCache extends CacheItem {
  heading: string;
  level: number;        // 1-6
}

interface LinkCache extends CacheItem {
  link: string;          // Link target
  original: string;      // Original text including [[]]
  displayText?: string;  // Display alias
}

interface TagCache extends CacheItem {
  tag: string;           // Including # prefix
}

interface ListItemCache extends CacheItem {
  parent: number;        // Line number of parent, -1 if root
  task?: string;         // Task marker character (' ', 'x', etc.)
}

interface CacheItem {
  position: Pos;
}

interface Pos {
  start: Loc;
  end: Loc;
}

interface Loc {
  line: number;
  col: number;
  offset: number;
}
```

### Querying Metadata

```typescript
// Get all tags from a file (both frontmatter and body)
function getAllTags(cache: CachedMetadata): string[] {
  const tags: string[] = [];

  // Frontmatter tags
  if (cache.frontmatter?.tags) {
    const fmTags = cache.frontmatter.tags;
    if (Array.isArray(fmTags)) {
      tags.push(...fmTags.map(t => t.startsWith('#') ? t : `#${t}`));
    } else if (typeof fmTags === 'string') {
      tags.push(fmTags.startsWith('#') ? fmTags : `#${fmTags}`);
    }
  }

  // Body tags
  if (cache.tags) {
    tags.push(...cache.tags.map(t => t.tag));
  }

  return tags;
}

// Obsidian provides a built-in helper:
import { getAllTags } from 'obsidian';
const tags = getAllTags(cache);  // Returns string[] with # prefix
```

```typescript
// Get all outgoing links from a file
function getOutgoingLinks(cache: CachedMetadata): string[] {
  const links: string[] = [];
  if (cache.links) {
    links.push(...cache.links.map(l => l.link));
  }
  if (cache.embeds) {
    links.push(...cache.embeds.map(e => e.link));
  }
  return links;
}
```

### Resolved Links

The `resolvedLinks` map tracks all resolved links between files:

```typescript
// resolvedLinks[sourcePath][targetPath] = linkCount
const resolved = this.app.metadataCache.resolvedLinks;

// Get all files linked from a specific file
const linksFrom = resolved['notes/my-note.md'];
// { 'notes/other.md': 2, 'images/photo.png': 1 }

// Find backlinks to a file
function getBacklinks(targetPath: string, resolvedLinks: Record<string, Record<string, number>>): string[] {
  const backlinks: string[] = [];
  for (const [source, targets] of Object.entries(resolvedLinks)) {
    if (targets[targetPath]) {
      backlinks.push(source);
    }
  }
  return backlinks;
}
```

### Listening for Cache Changes

```typescript
// Triggered when a file's metadata cache is updated
this.registerEvent(
  this.app.metadataCache.on('changed', (file, data, cache) => {
    // file: TFile that changed
    // data: raw file content string
    // cache: updated CachedMetadata
    console.log('Cache updated for:', file.path);
    console.log('Headings:', cache.headings?.length ?? 0);
  })
);

// Triggered when all metadata is resolved (good for startup)
this.registerEvent(
  this.app.metadataCache.on('resolved', () => {
    console.log('All metadata resolved');
    this.buildIndex();
  })
);
```

## Vault Events

```typescript
// File created
this.registerEvent(
  this.app.vault.on('create', (file: TAbstractFile) => {
    if (file instanceof TFile) {
      console.log('File created:', file.path);
    } else if (file instanceof TFolder) {
      console.log('Folder created:', file.path);
    }
  })
);

// File modified
this.registerEvent(
  this.app.vault.on('modify', (file: TAbstractFile) => {
    if (file instanceof TFile) {
      console.log('File modified:', file.path);
    }
  })
);

// File deleted
this.registerEvent(
  this.app.vault.on('delete', (file: TAbstractFile) => {
    console.log('Deleted:', file.path);
  })
);

// File renamed/moved
this.registerEvent(
  this.app.vault.on('rename', (file: TAbstractFile, oldPath: string) => {
    console.log(`Moved: ${oldPath} -> ${file.path}`);
  })
);
```

## Batch Operations

### Processing Multiple Files

```typescript
async processAllMarkdownFiles(): Promise<void> {
  const files = this.app.vault.getMarkdownFiles();
  let processed = 0;

  for (const file of files) {
    try {
      const content = await this.app.vault.read(file);
      const modified = this.transformContent(content);

      if (modified !== content) {
        await this.app.vault.modify(file, modified);
        processed++;
      }
    } catch (error) {
      console.error(`Failed to process ${file.path}:`, error);
    }
  }

  new Notice(`Processed ${processed} of ${files.length} files`);
}
```

### Batching with Delays

For large operations, avoid blocking the UI:

```typescript
async batchProcess(files: TFile[], batchSize = 10): Promise<void> {
  for (let i = 0; i < files.length; i += batchSize) {
    const batch = files.slice(i, i + batchSize);
    await Promise.all(batch.map(f => this.processFile(f)));

    // Yield to UI thread between batches
    if (i + batchSize < files.length) {
      await new Promise(resolve => setTimeout(resolve, 0));
    }
  }
}
```

## Content Manipulation Patterns

### Insert Content at Heading

```typescript
async insertUnderHeading(file: TFile, heading: string, content: string): Promise<void> {
  const cache = this.app.metadataCache.getFileCache(file);
  if (!cache?.headings) return;

  const target = cache.headings.find(h => h.heading === heading);
  if (!target) return;

  const fileContent = await this.app.vault.read(file);
  const lines = fileContent.split('\n');

  // Find the end of this heading's section
  const startLine = target.position.start.line;
  let endLine = lines.length;

  for (const h of cache.headings) {
    if (h.position.start.line > startLine && h.level <= target.level) {
      endLine = h.position.start.line;
      break;
    }
  }

  // Insert content before the next heading
  lines.splice(endLine, 0, content);
  await this.app.vault.modify(file, lines.join('\n'));
}
```

### Replace Content Between Markers

```typescript
async replaceMarkedSection(file: TFile, marker: string, newContent: string): Promise<void> {
  const content = await this.app.vault.read(file);
  const startTag = `<!-- ${marker}-start -->`;
  const endTag = `<!-- ${marker}-end -->`;

  const startIdx = content.indexOf(startTag);
  const endIdx = content.indexOf(endTag);

  if (startIdx === -1 || endIdx === -1) {
    console.warn(`Markers not found: ${marker}`);
    return;
  }

  const before = content.substring(0, startIdx + startTag.length);
  const after = content.substring(endIdx);
  const modified = `${before}\n${newContent}\n${after}`;

  await this.app.vault.modify(file, modified);
}
```

### Daily Notes Integration

```typescript
// Access daily notes functionality (requires the built-in daily notes plugin)
// The daily notes API is available through the community plugin API

// Get today's daily note path
function getDailyNotePath(format: string = 'YYYY-MM-DD'): string {
  // Use moment (bundled with Obsidian)
  return (window as any).moment().format(format) + '.md';
}

// Find or create daily note
async function ensureDailyNote(vault: Vault, folder: string, format: string): Promise<TFile> {
  const filename = (window as any).moment().format(format);
  const path = normalizePath(`${folder}/${filename}.md`);

  const existing = vault.getFileByPath(path);
  if (existing) return existing;

  return await vault.create(path, `# ${filename}\n\n`);
}
```

## Path Utilities

```typescript
import { normalizePath } from 'obsidian';

// Normalize path separators and remove redundancies
normalizePath('folder//subfolder\\file.md');  // 'folder/subfolder/file.md'
normalizePath('./relative/../path/file.md');  // 'path/file.md'
normalizePath('/leading/slash');              // 'leading/slash'

// Extract parts of a path
function getDirectory(path: string): string {
  const lastSlash = path.lastIndexOf('/');
  return lastSlash >= 0 ? path.substring(0, lastSlash) : '';
}

function getFilename(path: string): string {
  const lastSlash = path.lastIndexOf('/');
  return lastSlash >= 0 ? path.substring(lastSlash + 1) : path;
}

function getExtension(path: string): string {
  const lastDot = path.lastIndexOf('.');
  return lastDot >= 0 ? path.substring(lastDot + 1) : '';
}
```

## Error Handling Patterns

### Defensive File Operations

```typescript
async safeRead(path: string): Promise<string | null> {
  const file = this.app.vault.getFileByPath(normalizePath(path));
  if (!file) {
    console.warn(`File not found: ${path}`);
    return null;
  }

  try {
    return await this.app.vault.read(file);
  } catch (error) {
    console.error(`Failed to read ${path}:`, error);
    new Notice(`Could not read file: ${path}`);
    return null;
  }
}

async safeWrite(path: string, content: string): Promise<TFile | null> {
  try {
    const normalized = normalizePath(path);
    const existing = this.app.vault.getFileByPath(normalized);

    if (existing) {
      await this.app.vault.modify(existing, content);
      return existing;
    }

    // Ensure directory exists
    const dir = normalized.substring(0, normalized.lastIndexOf('/'));
    if (dir && !this.app.vault.getFolderByPath(dir)) {
      await this.app.vault.createFolder(dir);
    }

    return await this.app.vault.create(normalized, content);
  } catch (error) {
    console.error(`Failed to write ${path}:`, error);
    new Notice(`Could not write file: ${path}`);
    return null;
  }
}
```

## Performance Considerations

- **Use `cachedRead` over `read`** when you only need to display content and staleness is acceptable.
- **Batch file operations** to avoid overwhelming the file system, especially on mobile.
- **Avoid `getAllLoadedFiles()`** in hot paths -- it returns every file and folder in the vault.
- **Use `getFileByPath` over `getAbstractFileByPath`** when you know you want a file -- it avoids type checking.
- **Listen to specific events** rather than polling. The vault and metadataCache emit events for all changes.
- **Debounce operations** triggered by file change events to avoid redundant work when multiple files change in quick succession.

```typescript
import { debounce } from 'obsidian';

const debouncedUpdate = debounce(
  () => this.rebuildIndex(),
  500,
  true  // Run on leading edge
);

this.registerEvent(
  this.app.vault.on('modify', () => debouncedUpdate())
);
```
