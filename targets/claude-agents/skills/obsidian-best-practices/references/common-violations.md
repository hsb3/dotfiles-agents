# Common Violations and Fixes

Real-world examples of community plugin review violations with before/after code showing how to fix each one.

## Violation 1: innerHTML Usage

The most common rejection reason. The review bot searches the bundled `main.js` for any occurrence of `innerHTML`, `outerHTML`, or `insertAdjacentHTML`.

### Example 1a: Building a Message List

```typescript
// BEFORE (rejected)
function renderMessages(container: HTMLElement, messages: Message[]) {
  container.innerHTML = '';
  messages.forEach(msg => {
    container.innerHTML += `
      <div class="message ${msg.role}">
        <div class="label">${msg.role}</div>
        <div class="content">${msg.text}</div>
      </div>
    `;
  });
}

// AFTER (accepted)
function renderMessages(container: HTMLElement, messages: Message[]) {
  container.empty();
  messages.forEach(msg => {
    const msgEl = container.createDiv({ cls: `message ${msg.role}` });
    msgEl.createDiv({ cls: 'label', text: msg.role });
    msgEl.createDiv({ cls: 'content', text: msg.text });
  });
}
```

### Example 1b: Rendering Markdown Content

```typescript
// BEFORE (rejected) - using a third-party markdown library
import { marked } from 'marked';

function renderMarkdown(container: HTMLElement, markdown: string) {
  container.innerHTML = marked.parse(markdown);
}

// AFTER (accepted) - using Obsidian's built-in renderer
import { MarkdownRenderer, App, Component } from 'obsidian';

async function renderMarkdown(
  app: App,
  container: HTMLElement,
  markdown: string,
  component: Component
) {
  container.empty();
  await MarkdownRenderer.render(app, markdown, container, '', component);
}
```

### Example 1c: Clearing an Element

```typescript
// BEFORE (rejected)
container.innerHTML = '';

// AFTER (accepted)
container.empty();
```

### Example 1d: Creating Complex Nested UI

```typescript
// BEFORE (rejected)
function createSettingsPanel(container: HTMLElement, config: Config) {
  container.innerHTML = `
    <div class="settings-panel">
      <h3>Settings</h3>
      <div class="setting-item">
        <label>Server URL</label>
        <input type="text" value="${config.serverUrl}" />
      </div>
      <div class="setting-item">
        <label>API Key</label>
        <input type="password" value="${config.apiKey}" />
      </div>
      <button class="save-btn">Save</button>
    </div>
  `;
}

// AFTER (accepted)
function createSettingsPanel(container: HTMLElement, config: Config) {
  container.empty();
  const panel = container.createDiv({ cls: 'settings-panel' });
  panel.createEl('h3', { text: 'Settings' });

  const urlItem = panel.createDiv({ cls: 'setting-item' });
  urlItem.createEl('label', { text: 'Server URL' });
  const urlInput = urlItem.createEl('input', {
    attr: { type: 'text', value: config.serverUrl }
  });

  const keyItem = panel.createDiv({ cls: 'setting-item' });
  keyItem.createEl('label', { text: 'API Key' });
  const keyInput = keyItem.createEl('input', {
    attr: { type: 'password', value: config.apiKey }
  });

  const saveBtn = panel.createEl('button', {
    cls: 'save-btn',
    text: 'Save'
  });

  saveBtn.addEventListener('click', () => {
    config.serverUrl = urlInput.value;
    config.apiKey = keyInput.value;
    void saveConfig(config);
  });
}
```

### Example 1e: innerHTML from Bundled Dependency

```typescript
// BEFORE (rejected) - dependency internally uses innerHTML
import DOMPurify from 'dompurify';

function safeRender(container: HTMLElement, html: string) {
  // Even with sanitization, DOMPurify uses innerHTML internally
  container.innerHTML = DOMPurify.sanitize(html);
}

// AFTER (accepted) - no dependency needed
function safeRender(container: HTMLElement, text: string) {
  container.empty();
  container.setText(text);
}

// Or for markdown content:
async function safeRenderMarkdown(
  app: App,
  container: HTMLElement,
  markdown: string,
  component: Component
) {
  container.empty();
  await MarkdownRenderer.render(app, markdown, container, '', component);
}
```

## Violation 2: Forbidden Console Methods

### Example 2a: Debug Logging

```typescript
// BEFORE (rejected)
export default class MyPlugin extends Plugin {
  async onload() {
    console.log('Plugin loaded');
    console.info('Initializing settings');
  }

  async processFile(file: TFile) {
    console.log(`Processing: ${file.path}`);
    try {
      await this.transform(file);
      console.log('Done');
    } catch (e) {
      console.log('Error:', e);  // Even errors logged with console.log
    }
  }
}

// AFTER (accepted)
export default class MyPlugin extends Plugin {
  async onload() {
    console.debug('Plugin loaded');
    console.debug('Initializing settings');
  }

  async processFile(file: TFile) {
    console.debug(`Processing: ${file.path}`);
    try {
      await this.transform(file);
      console.debug('Done');
    } catch (e) {
      console.error('Error:', e);  // Use console.error for errors
    }
  }
}
```

### Example 2b: Conditional Logging

```typescript
// BEFORE (rejected) - console.log behind a flag still fails static analysis
if (this.settings.debug) {
  console.log('Debug info:', data);
}

// AFTER (accepted)
if (this.settings.debug) {
  console.debug('Debug info:', data);
}
```

## Violation 3: Unhandled Promises

### Example 3a: Event Handlers with Async Calls

```typescript
// BEFORE (rejected) - floating promises in callbacks
export default class MyPlugin extends Plugin {
  async onload() {
    await this.loadSettings();

    this.addCommand({
      id: 'sync-data',
      name: 'Sync data',
      callback: () => {
        this.syncData();  // Floating promise
      }
    });

    this.registerEvent(
      this.app.workspace.on('file-open', (file) => {
        this.analyzeFile(file);  // Floating promise
      })
    );

    this.loadExternalData();  // Floating promise
  }

  async syncData() { /* ... */ }
  async analyzeFile(file: TFile | null) { /* ... */ }
  async loadExternalData() { /* ... */ }
}

// AFTER (accepted) - all promises handled
export default class MyPlugin extends Plugin {
  async onload() {
    await this.loadSettings();

    this.addCommand({
      id: 'sync-data',
      name: 'Sync data',
      callback: () => {
        void this.syncData();  // Explicitly voided
      }
    });

    this.registerEvent(
      this.app.workspace.on('file-open', (file) => {
        void this.analyzeFile(file);  // Explicitly voided
      })
    );

    await this.loadExternalData();  // Awaited
  }

  async syncData() { /* ... */ }
  async analyzeFile(file: TFile | null) { /* ... */ }
  async loadExternalData() { /* ... */ }
}
```

### Example 3b: Promise in Constructor-Like Context

```typescript
// BEFORE (rejected)
class MyView extends ItemView {
  constructor(leaf: WorkspaceLeaf, plugin: MyPlugin) {
    super(leaf);
    this.plugin = plugin;
    this.initialize();  // Floating promise
  }

  async initialize() {
    await this.loadData();
  }
}

// AFTER (accepted) - move async init to onOpen
class MyView extends ItemView {
  constructor(leaf: WorkspaceLeaf, plugin: MyPlugin) {
    super(leaf);
    this.plugin = plugin;
  }

  async onOpen() {
    await this.initialize();
  }

  async initialize() {
    await this.loadData();
  }
}
```

## Violation 4: Command ID Includes Plugin ID

### Example 4a: Redundant Namespacing

```typescript
// BEFORE (rejected)
// Plugin ID in manifest.json: "my-cool-plugin"
this.addCommand({
  id: 'my-cool-plugin:open-view',
  name: 'Open view'
});

this.addCommand({
  id: 'my-cool-plugin-refresh',
  name: 'Refresh data'
});

// AFTER (accepted)
// Obsidian registers as "my-cool-plugin:open-view" automatically
this.addCommand({
  id: 'open-view',
  name: 'Open view'
});

this.addCommand({
  id: 'refresh',
  name: 'Refresh data'
});
```

## Violation 5: Unnecessary Async

### Example 5a: Functions Without Await

```typescript
// BEFORE (rejected)
async getDisplayName(): Promise<string> {
  return this.settings.name || 'Default';
}

async formatMessage(text: string): Promise<string> {
  return `[${new Date().toISOString()}] ${text}`;
}

async isEnabled(): Promise<boolean> {
  return this.settings.enabled;
}

// AFTER (accepted) - remove async when no await is needed
getDisplayName(): string {
  return this.settings.name || 'Default';
}

formatMessage(text: string): string {
  return `[${new Date().toISOString()}] ${text}`;
}

isEnabled(): boolean {
  return this.settings.enabled;
}
```

### Example 5b: Async onunload (Common Mistake)

```typescript
// BEFORE (rejected) - async onunload with no await
async onunload() {
  this.cleanup();  // sync method, no await needed
}

// AFTER (accepted) - remove async
onunload() {
  this.cleanup();
}

// Also accepted - if cleanup is actually async
async onunload() {
  await this.stopServer();
}
```

## Violation 6: Title Case in UI Text

### Example 6a: Command Names

```typescript
// BEFORE (rejected)
this.addCommand({ id: 'open-chat', name: 'Open Chat View' });
this.addCommand({ id: 'sync', name: 'Sync All Notes' });
this.addCommand({ id: 'settings', name: 'Open Plugin Settings' });
this.addCommand({ id: 'import', name: 'Import From JSON' });

// AFTER (accepted)
this.addCommand({ id: 'open-chat', name: 'Open chat view' });
this.addCommand({ id: 'sync', name: 'Sync all notes' });
this.addCommand({ id: 'settings', name: 'Open plugin settings' });
this.addCommand({ id: 'import', name: 'Import from JSON' });  // JSON is an acronym, stays uppercase
```

### Example 6b: Ribbon Tooltips and Notices

```typescript
// BEFORE (rejected)
this.addRibbonIcon('bot', 'Open AI Chat', callback);
new Notice('Settings Saved Successfully');

// AFTER (accepted)
this.addRibbonIcon('bot', 'Open AI chat', callback);
new Notice('Settings saved successfully');
```

## Violation 7: Memory Leaks

### Example 7a: Manual Event Listeners

```typescript
// BEFORE (flagged) - manual listeners leak on unload
export default class MyPlugin extends Plugin {
  private handleResize = () => { /* ... */ };
  private handleKeydown = (e: KeyboardEvent) => { /* ... */ };

  async onload() {
    await this.loadSettings();
    window.addEventListener('resize', this.handleResize);
    document.addEventListener('keydown', this.handleKeydown);
  }

  onunload() {
    // Easy to forget, and if onunload throws, listeners persist
    window.removeEventListener('resize', this.handleResize);
    document.removeEventListener('keydown', this.handleKeydown);
  }
}

// AFTER (accepted) - auto-cleanup via registerDomEvent
export default class MyPlugin extends Plugin {
  async onload() {
    await this.loadSettings();

    this.registerDomEvent(window, 'resize', () => {
      // handle resize
    });

    this.registerDomEvent(document, 'keydown', (e: KeyboardEvent) => {
      // handle keydown
    });
  }
  // No onunload needed - Obsidian cleans up automatically
}
```

### Example 7b: Unmanaged Intervals

```typescript
// BEFORE (flagged)
export default class MyPlugin extends Plugin {
  private pollTimer: number;

  async onload() {
    await this.loadSettings();
    this.pollTimer = window.setInterval(() => {
      void this.poll();
    }, 30000);
  }

  onunload() {
    clearInterval(this.pollTimer);
  }
}

// AFTER (accepted) - auto-cleanup via registerInterval
export default class MyPlugin extends Plugin {
  async onload() {
    await this.loadSettings();
    this.registerInterval(
      window.setInterval(() => {
        void this.poll();
      }, 30000)
    );
  }
}
```

## Violation 8: Build Configuration Errors

### Example 8a: Missing Bundled Dependencies

```javascript
// BEFORE (rejected) - external dependencies won't be available at runtime
esbuild.build({
  entryPoints: ['src/main.ts'],
  bundle: true,
  external: [
    'obsidian',
    'electron',
    'marked',     // This must be bundled
    'uuid',       // This must be bundled
    'lodash',     // This must be bundled
  ],
  format: 'cjs',
  outfile: 'main.js',
});

// AFTER (accepted) - only obsidian and electron are external
esbuild.build({
  entryPoints: ['src/main.ts'],
  bundle: true,
  external: ['obsidian', 'electron'],
  format: 'cjs',
  outfile: 'main.js',
  platform: 'node',
  target: 'es2018',
});
```

### Example 8b: Wrong Module Format

```javascript
// BEFORE (rejected) - ESM format won't load in Obsidian
esbuild.build({
  format: 'esm',  // Wrong
  // ...
});

// AFTER (accepted)
esbuild.build({
  format: 'cjs',  // CommonJS required
  // ...
});
```

## Violation 9: Committed Generated Files

### Example 9a: Missing .gitignore Entries

```gitignore
# BEFORE (flagged) - missing critical entries
node_modules/

# AFTER (accepted) - complete .gitignore
# Build output
main.js
*.js.map

# Dependencies
node_modules/

# OS files
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/

# Environment
.env
```

## Quick Fix Reference

| Violation | Search Pattern | Fix |
|-----------|---------------|-----|
| innerHTML | `innerHTML`, `outerHTML`, `insertAdjacentHTML` | Use `createEl()`, `createDiv()`, `empty()` |
| Console | `console.log`, `console.info`, `console.trace` | Replace with `console.debug()` or `console.error()` |
| Floating promise | Async call without await/void/catch | Add `await`, `void`, or `.catch()` |
| Command ID | Plugin ID in `addCommand({ id: })` | Remove plugin ID prefix |
| Unnecessary async | `async` function with no `await` | Remove `async` keyword |
| Title Case | Capital letters in command names | Use sentence case |
| Memory leak | `addEventListener`, `setInterval` | Use `registerDomEvent`, `registerInterval` |
| Build external | Extra entries in `external` array | Only `['obsidian', 'electron']` |
| Module format | `format: 'esm'` | Use `format: 'cjs'` |
| Committed artifacts | `main.js` in git | Add to `.gitignore` |
