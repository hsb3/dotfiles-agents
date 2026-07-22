# Obsidian API Reference

Complete reference for the Obsidian plugin API surface. This covers the core classes, interfaces, and methods available to plugin developers.

## Plugin Base Class

The `Plugin` class is the entry point for all Obsidian plugins. Every plugin must export a default class extending `Plugin`.

### Lifecycle Methods

```typescript
class Plugin extends Component {
  app: App;
  manifest: PluginManifest;

  // Called when plugin is activated
  async onload(): Promise<void>;

  // Called when plugin is deactivated
  async onunload(): Promise<void>;
}
```

### Data Persistence

```typescript
class Plugin {
  // Load plugin data from disk (data.json in plugin folder)
  async loadData(): Promise<any>;

  // Save plugin data to disk
  async saveData(data: any): Promise<void>;
}
```

Data is stored as JSON in `.obsidian/plugins/<plugin-id>/data.json`. The `loadData()` method returns `null` if no data has been saved yet, which is why the settings pattern uses `Object.assign()` to merge with defaults.

### Command Registration

```typescript
interface Command {
  id: string;              // Unique ID (do NOT include plugin prefix)
  name: string;            // Display name in command palette (sentence case)
  icon?: string;           // Lucide icon name
  hotkeys?: Hotkey[];      // Default hotkeys (user can override)

  // Use ONE of these callback types:
  callback?: () => any;                        // Always available
  checkCallback?: (checking: boolean) => boolean | void;  // Conditionally available
  editorCallback?: (editor: Editor, ctx: MarkdownView | MarkdownFileInfo) => any;  // Editor required
  editorCheckCallback?: (checking: boolean, editor: Editor, ctx: MarkdownView | MarkdownFileInfo) => boolean | void;
}

// Register a command
this.addCommand(command: Command): Command;
```

**Callback types explained:**

- `callback` - Command is always available in the palette.
- `checkCallback` - Called with `checking=true` to test availability. Return `false` to hide from palette. Called again with `checking=false` to execute.
- `editorCallback` - Only available when an editor is focused. Receives `Editor` and view context.
- `editorCheckCallback` - Combines editor requirement with conditional availability.

```typescript
// checkCallback example
this.addCommand({
  id: 'process-selection',
  name: 'Process selected text',
  checkCallback: (checking: boolean) => {
    const view = this.app.workspace.getActiveViewOfType(MarkdownView);
    const hasSelection = view?.editor.somethingSelected();
    if (checking) {
      return !!hasSelection;
    }
    if (hasSelection) {
      const text = view!.editor.getSelection();
      this.processText(text);
    }
  }
});

// editorCallback example
this.addCommand({
  id: 'insert-timestamp',
  name: 'Insert timestamp',
  editorCallback: (editor: Editor) => {
    editor.replaceSelection(new Date().toISOString());
  }
});
```

### Ribbon Icons

```typescript
// Add icon to left sidebar ribbon
this.addRibbonIcon(
  icon: string,      // Lucide icon name
  title: string,     // Tooltip text
  callback: (evt: MouseEvent) => any
): HTMLElement;
```

Returns the ribbon icon element for further customization. Common Lucide icons: `bot`, `message-square`, `settings`, `file-text`, `search`, `dice`, `brain`, `code`, `globe`.

### Settings Tab

```typescript
// Register a settings tab
this.addSettingTab(settingTab: PluginSettingTab): void;
```

### Status Bar

```typescript
// Add element to bottom status bar
this.addStatusBarItem(): HTMLElement;
```

Returns an `HTMLElement` that you can set content on. Automatically removed on unload.

```typescript
const statusEl = this.addStatusBarItem();
statusEl.setText('Plugin active');
// Update later:
statusEl.setText('Processing...');
```

### View Registration

```typescript
// Register a custom view type
this.registerView(
  type: string,                              // Unique view type ID
  viewCreator: (leaf: WorkspaceLeaf) => View // Factory function
): void;
```

### Event Registration

```typescript
// Register event with automatic cleanup on unload
this.registerEvent(eventRef: EventRef): void;

// Register interval with automatic cleanup on unload
this.registerInterval(id: number): number;

// Register DOM event with automatic cleanup
this.registerDomEvent(
  el: HTMLElement | Document | Window,
  type: string,
  callback: (evt: Event) => any,
  options?: boolean | AddEventListenerOptions
): void;
```

Always use `registerEvent()`, `registerInterval()`, and `registerDomEvent()` instead of manual event listeners. Obsidian automatically cleans up registered resources when the plugin unloads.

### Extensions and Post-Processors

```typescript
// Register a CodeMirror 6 editor extension
this.registerEditorExtension(extension: Extension): void;

// Register a markdown post-processor (runs after markdown renders)
this.registerMarkdownPostProcessor(
  postProcessor: MarkdownPostProcessor,
  sortOrder?: number
): MarkdownPostProcessorReference;

// Register a code block processor
this.registerMarkdownCodeBlockProcessor(
  language: string,
  handler: (source: string, el: HTMLElement, ctx: MarkdownPostProcessorContext) => Promise<void> | void,
  sortOrder?: number
): MarkdownPostProcessorReference;
```

## App Object

The `App` object is the root API access point, available via `this.app` in plugins and views.

```typescript
interface App {
  vault: Vault;                    // File system operations
  workspace: Workspace;           // UI layout and view management
  metadataCache: MetadataCache;   // Parsed file metadata
  fileManager: FileManager;       // High-level file operations
  keymap: Keymap;                 // Keyboard shortcut management
  scope: Scope;                   // Current keyboard scope
  lastEvent: UserEvent | null;    // Last user interaction event
}
```

### Vault

Primary interface for file system operations. See `vault-advanced.md` for detailed coverage.

```typescript
interface Vault extends Events {
  // Read
  read(file: TFile): Promise<string>;
  readBinary(file: TFile): Promise<ArrayBuffer>;
  cachedRead(file: TFile): Promise<string>;

  // Write
  create(path: string, data: string, options?: DataWriteOptions): Promise<TFile>;
  createBinary(path: string, data: ArrayBuffer, options?: DataWriteOptions): Promise<TFile>;
  createFolder(path: string): Promise<void>;
  modify(file: TFile, data: string, options?: DataWriteOptions): Promise<void>;
  modifyBinary(file: TFile, data: ArrayBuffer, options?: DataWriteOptions): Promise<void>;
  append(file: TFile, data: string, options?: DataWriteOptions): Promise<void>;

  // Delete
  delete(file: TAbstractFile, force?: boolean): Promise<void>;
  trash(file: TAbstractFile, system: boolean): Promise<void>;

  // Query
  getAbstractFileByPath(path: string): TAbstractFile | null;
  getFileByPath(path: string): TFile | null;
  getFolderByPath(path: string): TFolder | null;
  getMarkdownFiles(): TFile[];
  getFiles(): TFile[];
  getAllLoadedFiles(): TAbstractFile[];

  // Rename / Move
  rename(file: TAbstractFile, newPath: string): Promise<void>;
  copy(file: TFile, newPath: string): Promise<TFile>;

  // Events
  on(name: 'create', callback: (file: TAbstractFile) => any): EventRef;
  on(name: 'modify', callback: (file: TAbstractFile) => any): EventRef;
  on(name: 'delete', callback: (file: TAbstractFile) => any): EventRef;
  on(name: 'rename', callback: (file: TAbstractFile, oldPath: string) => any): EventRef;
}
```

### File Types

```typescript
abstract class TAbstractFile {
  vault: Vault;
  path: string;       // Full path from vault root
  name: string;       // Filename with extension
  parent: TFolder | null;
}

class TFile extends TAbstractFile {
  stat: FileStats;
  basename: string;   // Filename without extension
  extension: string;
}

class TFolder extends TAbstractFile {
  children: TAbstractFile[];
  isRoot(): boolean;
}

interface FileStats {
  ctime: number;   // Created time (ms since epoch)
  mtime: number;   // Modified time (ms since epoch)
  size: number;    // File size in bytes
}
```

### MetadataCache

Provides parsed metadata without reading file contents. See also `vault-advanced.md`.

```typescript
interface MetadataCache extends Events {
  getFileCache(file: TFile): CachedMetadata | null;
  getFirstLinkpathDest(linkpath: string, sourcePath: string): TFile | null;
  resolvedLinks: Record<string, Record<string, number>>;

  // Events
  on(name: 'changed', callback: (file: TFile, data: string, cache: CachedMetadata) => any): EventRef;
  on(name: 'resolved', callback: () => any): EventRef;
}

interface CachedMetadata {
  frontmatter?: FrontMatterCache;
  frontmatterLinks?: FrontmatterLinkCache[];
  frontmatterPosition?: Pos;
  headings?: HeadingCache[];
  links?: LinkCache[];
  embeds?: EmbedCache[];
  tags?: TagCache[];
  sections?: SectionCache[];
  listItems?: ListItemCache[];
}
```

### FileManager

High-level file operations with link updating:

```typescript
interface FileManager {
  // Rename file and update all links pointing to it
  renameFile(file: TAbstractFile, newPath: string): Promise<void>;

  // Process frontmatter with automatic YAML handling
  processFrontMatter(
    file: TFile,
    fn: (frontmatter: any) => void,
    options?: DataWriteOptions
  ): Promise<void>;

  // Generate a unique filename if path already exists
  getNewFileParent(sourcePath: string): TFolder;
  getAvailablePath(dir: string, filename: string): string;
}
```

The `processFrontMatter` method is the recommended way to modify YAML frontmatter. It handles parsing and serialization:

```typescript
await this.app.fileManager.processFrontMatter(file, (fm) => {
  fm.tags = fm.tags || [];
  fm.tags.push('processed');
  fm.lastModified = new Date().toISOString();
});
```

## Component Class

Base class for lifecycle-managed objects. Both `Plugin` and `View` extend `Component`.

```typescript
class Component {
  // Register a child component for lifecycle management
  addChild<T extends Component>(component: T): T;

  // Remove a child component
  removeChild<T extends Component>(component: T): T;

  // Register cleanup callback
  register(cb: () => any): void;

  // Register event listener with auto-cleanup
  registerEvent(eventRef: EventRef): void;

  // Register DOM event with auto-cleanup
  registerDomEvent(el: Window | Document | HTMLElement, type: string, callback: Function, options?: any): void;

  // Register interval with auto-cleanup
  registerInterval(id: number): number;

  // Load/unload lifecycle
  load(): void;
  onload(): void;
  unload(): void;
  onunload(): void;
}
```

## Editor API

Interface for interacting with the CodeMirror 6 editor:

```typescript
interface Editor {
  // Content
  getValue(): string;
  setValue(content: string): void;
  getLine(line: number): string;
  setLine(line: number, text: string): void;
  lineCount(): number;

  // Selection
  getSelection(): string;
  replaceSelection(replacement: string): void;
  somethingSelected(): boolean;

  // Cursor
  getCursor(string?: 'from' | 'to' | 'head' | 'anchor'): EditorPosition;
  setCursor(pos: EditorPosition | number, ch?: number): void;

  // Range operations
  getRange(from: EditorPosition, to: EditorPosition): string;
  replaceRange(replacement: string, from: EditorPosition, to: EditorPosition, origin?: string): void;

  // Transactions
  transaction(tx: EditorTransaction): void;

  // Scrolling
  scrollIntoView(range: EditorRange, center?: boolean): void;

  // Word at position
  wordAt(pos: EditorPosition): EditorRange | null;

  // Focus
  focus(): void;
  hasFocus(): boolean;

  // Undo
  undo(): void;
  redo(): void;
}

interface EditorPosition {
  line: number;
  ch: number;
}

interface EditorRange {
  from: EditorPosition;
  to: EditorPosition;
}
```

## UI Components

### Notice

Display temporary notifications:

```typescript
// Simple notice (default 5 seconds)
new Notice('Operation complete');

// With custom duration (milliseconds, 0 = until dismissed)
new Notice('Important message', 10000);

// With fragment for rich content
const frag = document.createDocumentFragment();
const el = frag.createEl('span', { text: 'Bold message', cls: 'mod-warning' });
new Notice(frag, 8000);
```

### Modal

Create dialog windows:

```typescript
class MyModal extends Modal {
  constructor(app: App) {
    super(app);
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.createEl('h2', { text: 'My Modal' });
    contentEl.createEl('p', { text: 'Modal content here' });

    new Setting(contentEl)
      .addButton((btn) =>
        btn.setButtonText('Confirm')
           .setCta()
           .onClick(() => {
             this.close();
           }));
  }

  onClose() {
    this.contentEl.empty();
  }
}

// Usage
new MyModal(this.app).open();
```

### Setting

Build settings UI elements:

```typescript
class Setting {
  constructor(containerEl: HTMLElement);

  setName(name: string | DocumentFragment): this;
  setDesc(desc: string | DocumentFragment): this;
  setClass(cls: string): this;
  setHeading(): this;
  setDisabled(disabled: boolean): this;

  addText(cb: (component: TextComponent) => any): this;
  addTextArea(cb: (component: TextAreaComponent) => any): this;
  addToggle(cb: (component: ToggleComponent) => any): this;
  addDropdown(cb: (component: DropdownComponent) => any): this;
  addSlider(cb: (component: SliderComponent) => any): this;
  addButton(cb: (component: ButtonComponent) => any): this;
  addExtraButton(cb: (component: ExtraButtonComponent) => any): this;
  addColorPicker(cb: (component: ColorComponent) => any): this;
  addSearch(cb: (component: SearchComponent) => any): this;
}
```

### PluginSettingTab

Base class for plugin settings tabs:

```typescript
abstract class PluginSettingTab extends SettingTab {
  plugin: Plugin;
  constructor(app: App, plugin: Plugin);

  abstract display(): void;
  hide(): void;
}
```

### Setting Component Types

```typescript
// TextComponent
text.setPlaceholder('Enter value...')
    .setValue(currentValue)
    .onChange(async (value) => { /* handle change */ });

// ToggleComponent
toggle.setValue(true)
      .onChange(async (value) => { /* handle change */ });

// DropdownComponent
dropdown.addOption('opt1', 'Option 1')
        .addOption('opt2', 'Option 2')
        .setValue(currentValue)
        .onChange(async (value) => { /* handle change */ });

// SliderComponent
slider.setLimits(0, 100, 1)
      .setValue(50)
      .setDynamicTooltip()
      .onChange(async (value) => { /* handle change */ });

// ButtonComponent
button.setButtonText('Click me')
      .setCta()  // Makes it a call-to-action (accent color)
      .setWarning()  // Makes it red/warning style
      .onClick(async () => { /* handle click */ });
```

## Events System

Obsidian uses a publish-subscribe events pattern:

```typescript
class Events {
  on(name: string, callback: (...data: any) => any, ctx?: any): EventRef;
  off(name: string, callback: (...data: any) => any): void;
  offref(ref: EventRef): void;
  trigger(name: string, ...data: any[]): void;
  tryTrigger(evt: EventRef, args: any[]): void;
}
```

Always use `this.registerEvent()` in plugins to ensure automatic cleanup:

```typescript
// Correct - auto cleanup
this.registerEvent(
  this.app.vault.on('create', (file) => {
    console.log('File created:', file.path);
  })
);

// Wrong - manual cleanup required, easy to leak
const ref = this.app.vault.on('create', (file) => { ... });
// Must manually call this.app.vault.offref(ref) in onunload
```

## requestUrl

Make HTTP requests from plugins (bypasses CORS):

```typescript
async function requestUrl(request: RequestUrlParam | string): Promise<RequestUrlResponse>;

interface RequestUrlParam {
  url: string;
  method?: string;
  contentType?: string;
  body?: string | ArrayBuffer;
  headers?: Record<string, string>;
  throw?: boolean;  // Throw on non-2xx (default: true)
}

interface RequestUrlResponse {
  status: number;
  headers: Record<string, string>;
  arrayBuffer: ArrayBuffer;
  json: any;
  text: string;
}
```

Usage example:

```typescript
import { requestUrl } from 'obsidian';

const response = await requestUrl({
  url: 'https://api.example.com/data',
  method: 'POST',
  contentType: 'application/json',
  body: JSON.stringify({ query: 'test' }),
  headers: {
    'Authorization': 'Bearer token123'
  }
});

const data = response.json;
```

## Utility Functions

```typescript
// Generate unique ID
import { nanoid } from 'obsidian';  // Not available - use crypto

// Normalize path separators
import { normalizePath } from 'obsidian';
normalizePath('folder//subfolder\\file.md'); // 'folder/subfolder/file.md'

// Debounce function calls
import { debounce } from 'obsidian';
const debouncedSave = debounce(this.saveSettings.bind(this), 300, true);

// Platform detection
import { Platform } from 'obsidian';
Platform.isMobile;     // boolean
Platform.isDesktop;    // boolean
Platform.isMacOS;      // boolean
Platform.isPhone;      // boolean
Platform.isTablet;     // boolean

// Parse/stringify YAML
import { parseYaml, stringifyYaml } from 'obsidian';
const obj = parseYaml(yamlString);
const yaml = stringifyYaml(obj);

// HTML sanitization
import { sanitizeHTMLToDom } from 'obsidian';
const safeDom = sanitizeHTMLToDom(htmlString);

// Hex string helpers
import { arrayBufferToHex, hexToArrayBuffer } from 'obsidian';
```

## Type Guards and Checks

Common patterns for type-safe file operations:

```typescript
import { TFile, TFolder, TAbstractFile } from 'obsidian';

function isFile(file: TAbstractFile): file is TFile {
  return file instanceof TFile;
}

function isFolder(file: TAbstractFile): file is TFolder {
  return file instanceof TFolder;
}

// Usage
const abstract = this.app.vault.getAbstractFileByPath('some/path');
if (abstract instanceof TFile) {
  // TypeScript knows this is a TFile
  const content = await this.app.vault.read(abstract);
}
```

## MarkdownView and MarkdownRenderer

```typescript
class MarkdownView extends TextFileView {
  editor: Editor;
  previewMode: MarkdownPreviewView;

  getViewType(): string;
  getDisplayText(): string;
  getMode(): 'source' | 'preview';
}

// Render markdown to HTML element
static MarkdownRenderer.render(
  app: App,
  markdown: string,
  el: HTMLElement,
  sourcePath: string,
  component: Component
): Promise<void>;

// Render inline markdown (no block elements)
static MarkdownRenderer.renderMarkdown(
  markdown: string,
  el: HTMLElement,
  sourcePath: string,
  component: Component
): Promise<void>;
```

## SuggestModal and FuzzySuggestModal

Create searchable suggestion modals:

```typescript
abstract class SuggestModal<T> extends Modal {
  abstract getSuggestions(query: string): T[] | Promise<T[]>;
  abstract renderSuggestion(value: T, el: HTMLElement): void;
  abstract onChooseSuggestion(item: T, evt: MouseEvent | KeyboardEvent): void;

  setPlaceholder(placeholder: string): void;
  setInstructions(instructions: Instruction[]): void;
}

abstract class FuzzySuggestModal<T> extends SuggestModal<FuzzyMatch<T>> {
  abstract getItems(): T[];
  abstract getItemText(item: T): string;
  abstract onChooseItem(item: T, evt: MouseEvent | KeyboardEvent): void;
}
```

Example:

```typescript
class FileSuggestModal extends FuzzySuggestModal<TFile> {
  getItems(): TFile[] {
    return this.app.vault.getMarkdownFiles();
  }

  getItemText(file: TFile): string {
    return file.path;
  }

  onChooseItem(file: TFile, evt: MouseEvent | KeyboardEvent): void {
    new Notice(`Selected: ${file.path}`);
  }
}
```
