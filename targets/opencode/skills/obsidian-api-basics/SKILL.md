---
name: obsidian-api-basics
description: This skill should be used when the user asks to "create an Obsidian plugin", "plugin lifecycle", "plugin settings", "vault API", "register command", "add ribbon icon", or mentions Obsidian plugin fundamentals like onload, onunload, saveData, or loadData.
---

# Obsidian API Basics

Provides foundational guidance for building Obsidian plugins, covering the plugin lifecycle, settings patterns, vault operations, and command registration.

## Core Concepts

### Plugin Class Structure

Every Obsidian plugin extends the `Plugin` base class and implements lifecycle methods:

```typescript
import { Plugin } from 'obsidian';

export default class MyPlugin extends Plugin {
  async onload() {
    // Plugin initialization
    console.debug('Plugin loaded');
  }

  async onunload() {
    // Cleanup
    console.debug('Plugin unloaded');
  }
}
```

**Critical rules:**
- Keep `main.ts` small - delegate functionality to separate modules
- Use `onload()` for initialization, registration, and setup
- Use `onunload()` for cleanup (most cleanup happens automatically)
- Never use the plugin instance as a Component to avoid memory leaks

### Settings Pattern

Implement user-configurable settings with persistence:

```typescript
interface MyPluginSettings {
  serverUrl: string;
  apiKey: string;
  enabled: boolean;
}

const DEFAULT_SETTINGS: MyPluginSettings = {
  serverUrl: 'http://localhost:3000',
  apiKey: '',
  enabled: true,
};

export default class MyPlugin extends Plugin {
  settings: MyPluginSettings;

  async onload() {
    await this.loadSettings();
    this.addSettingTab(new MySettingTab(this.app, this));
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }
}
```

**Pattern guidelines:**
- Define interface for settings structure
- Provide sensible defaults
- Use `Object.assign()` to merge defaults with saved data
- Call `loadSettings()` in `onload()`
- Call `saveSettings()` after any settings change

### Command Registration

Register commands that appear in the command palette:

```typescript
this.addCommand({
  id: 'open-view',  // Do NOT include plugin ID - Obsidian namespaces automatically
  name: 'Open my view',  // Use sentence case
  callback: () => {
    void this.activateView();
  }
});
```

**Command rules:**
- **Never** include plugin ID in command `id` field
- Use sentence case for `name`, not Title Case
- Handle promises properly: await, catch, or void
- Keep callback logic minimal - delegate to methods

### Ribbon Icons

Add icons to the left sidebar ribbon:

```typescript
this.addRibbonIcon('dice', 'Open my plugin', () => {
  void this.openView();
});
```

**Icon options:**
- Use Lucide icon names (https://lucide.dev)
- Common icons: 'bot', 'message-square', 'settings', 'file-text'
- Keep tooltip text concise and descriptive

### Vault Operations

Access vault files and content through the App API:

```typescript
// Get active file
const activeFile = this.app.workspace.getActiveFile();
if (activeFile) {
  // Read file content
  const content = await this.app.vault.read(activeFile);

  // Modify file
  await this.app.vault.modify(activeFile, newContent);
}

// Get all markdown files
const files = this.app.vault.getMarkdownFiles();

// Get file by path
const file = this.app.vault.getAbstractFileByPath('folder/note.md');
```

**Vault API patterns:**
- Always check if file exists before operations
- Use `TFile` type for files, `TFolder` for folders
- Handle errors gracefully with try/catch
- Respect user's vault - confirm destructive operations

### Metadata Cache

Access parsed frontmatter and metadata without file I/O:

```typescript
const file = this.app.workspace.getActiveFile();
if (file) {
  const cache = this.app.metadataCache.getFileCache(file);
  const frontmatter = cache?.frontmatter;
  const links = cache?.links;
  const headings = cache?.headings;
}
```

**Cache considerations:**
- Cache updates asynchronously after file changes
- May be stale immediately after writing
- Listen to `metadataCache.on('changed')` for updates
- Frontmatter is automatically parsed from YAML

### Event Registration

Register and auto-cleanup event listeners:

```typescript
this.registerEvent(
  this.app.workspace.on('active-leaf-change', () => {
    // Handle active file change
  })
);

this.registerInterval(
  window.setInterval(() => {
    // Periodic task
  }, 5000)
);
```

**Cleanup patterns:**
- Use `registerEvent()` for workspace events
- Use `registerInterval()` for timers
- Obsidian automatically cleans up on unload
- Avoid manual event removal

## File Structure Best Practices

Organize plugin code for maintainability:

```
src/
  main.ts           # Plugin entry point - lifecycle ONLY
  settings.ts       # Settings interface and tab
  constants.ts      # Constants, view type IDs
  api/              # External API clients
  ui/               # UI components, views
  commands/         # Command implementations
  types.ts          # TypeScript interfaces
```

**Organization principles:**
- `main.ts` should be <100 lines
- Split files when they exceed 200-300 lines
- Group related functionality in directories
- Use clear, descriptive module names

## Build Configuration

Standard esbuild setup for Obsidian plugins:

```javascript
// esbuild.config.mjs
import esbuild from 'esbuild';

const production = process.argv.includes('--production');

esbuild.build({
  entryPoints: ['src/main.ts'],
  bundle: true,
  external: ['obsidian', 'electron'],
  format: 'cjs',
  target: 'es2018',
  outfile: 'main.js',
  platform: 'node',
  minify: production,
  sourcemap: production ? false : 'inline',
}).catch(() => process.exit(1));
```

**Build requirements:**
- Bundle ALL dependencies except 'obsidian' and 'electron'
- Output to `main.js` in plugin root
- Use CommonJS format, not ESM
- Never commit `main.js` or `node_modules/`

## Release Artifacts

Required files for distribution:

- `main.js` - Bundled plugin code
- `manifest.json` - Plugin metadata
- `styles.css` - Optional styles

**Manifest structure:**
```json
{
  "id": "my-plugin",
  "name": "My Plugin",
  "version": "1.0.0",
  "minAppVersion": "0.15.0",
  "description": "Brief description",
  "author": "Your Name",
  "authorUrl": "https://yoursite.com",
  "isDesktopOnly": false
}
```

## Common Patterns

### Async Initialization

Handle async setup in onload:

```typescript
async onload() {
  await this.loadSettings();

  // Initialize async resources
  await this.initializeServer();

  // Register components
  this.registerView(VIEW_TYPE, (leaf) => new MyView(leaf, this));
  this.addCommand({...});
}
```

### Error Handling

Handle errors gracefully:

```typescript
try {
  await this.performOperation();
} catch (error) {
  console.error('Operation failed:', error);
  new Notice('Operation failed. See console for details.');
}
```

Use `Notice` for user-facing errors, `console.error` for debugging.

### Resource Cleanup

Clean up resources in onunload:

```typescript
async onunload() {
  // Stop servers
  await this.stopServer();

  // Clear timers (if not using registerInterval)
  if (this.timer) {
    clearInterval(this.timer);
  }

  // Most cleanup is automatic via register* methods
}
```

## Additional Resources

### Reference Files

For detailed information:
- **`references/api-reference.md`** - Complete Obsidian API surface
- **`references/workspace-api.md`** - Workspace and view management
- **`references/vault-advanced.md`** - Advanced vault operations

### Examples

Working examples in `examples/`:
- **`minimal-plugin.ts`** - Minimal viable plugin
- **`settings-example.ts`** - Complete settings implementation

### Official Documentation

Reference the official Obsidian resources:
- [Obsidian Sample Plugin](https://github.com/obsidianmd/obsidian-sample-plugin)
- [Obsidian API Docs](https://docs.obsidian.md/Plugins)
- [Obsidian API Types](https://github.com/obsidianmd/obsidian-api)

## Next Steps

After mastering these basics:
1. Learn safe DOM manipulation with `obsidian-dom-helpers` skill
2. Understand community review requirements with `obsidian-best-practices` skill
3. Build chat interfaces with `obsidian-chat-ui` skill
4. Integrate MCP servers with `obsidian-mcp-server` skill
