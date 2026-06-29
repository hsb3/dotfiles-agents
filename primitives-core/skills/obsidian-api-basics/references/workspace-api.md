# Workspace API Reference

Complete reference for Obsidian's Workspace and view management system. The Workspace controls the layout of panes, tabs, sidebars, and all visual components of the Obsidian interface.

## Workspace Overview

The Workspace is a hierarchical container system:

```
Workspace
  +-- Left Sidebar (WorkspaceSidedock)
  |     +-- WorkspaceTabs
  |           +-- WorkspaceLeaf (file explorer, search, etc.)
  +-- Root Split (WorkspaceSplit)
  |     +-- WorkspaceTabs
  |           +-- WorkspaceLeaf (editors, custom views)
  +-- Right Sidebar (WorkspaceSidedock)
        +-- WorkspaceTabs
              +-- WorkspaceLeaf (backlinks, outline, etc.)
```

Each `WorkspaceLeaf` contains exactly one `View`. Leaves are grouped into tab groups (`WorkspaceTabs`), which are arranged in splits (`WorkspaceSplit`).

## Workspace Class

```typescript
interface Workspace extends Events {
  // Active state
  activeLeaf: WorkspaceLeaf | null;         // Deprecated - use getActiveViewOfType
  activeEditor: MarkdownFileInfo | null;    // Currently active editor info

  // Layout containers
  leftSplit: WorkspaceSidedock;
  rightSplit: WorkspaceSidedock;
  leftRibbon: WorkspaceRibbon;
  rightRibbon: WorkspaceRibbon;
  rootSplit: WorkspaceSplit;

  // Layout state
  layoutReady: boolean;
  requestSaveLayout: Debouncer<[], Promise<void>>;
}
```

## Getting Active Content

### getActiveViewOfType

The recommended way to access the currently active view:

```typescript
getActiveViewOfType<T extends View>(type: Constructor<T>): T | null;
```

```typescript
import { MarkdownView } from 'obsidian';

// Get active markdown editor
const view = this.app.workspace.getActiveViewOfType(MarkdownView);
if (view) {
  const editor = view.editor;
  const file = view.file;
  const content = editor.getValue();
}
```

### getActiveFile

Get the currently active file (works even when the view is not a MarkdownView):

```typescript
// Returns TFile or null
const file = this.app.workspace.getActiveFile();
```

### getMostRecentLeaf

```typescript
getMostRecentLeaf(root?: WorkspaceParent): WorkspaceLeaf | null;
```

Returns the most recently active leaf, optionally scoped to a specific parent container.

## Creating and Managing Leaves

### getLeaf

Create or reuse a leaf for displaying content:

```typescript
getLeaf(newLeaf?: boolean | PaneType): WorkspaceLeaf;
```

The `newLeaf` parameter controls placement:

| Value | Behavior |
|-------|----------|
| `false` (default) | Reuse the current active leaf |
| `true` | Create a new tab in the active tab group |
| `'tab'` | Create a new tab in the active tab group |
| `'split'` | Split the current pane and create a new leaf |
| `'window'` | Open in a new pop-out window |

```typescript
// Open a file in a new tab
const leaf = this.app.workspace.getLeaf('tab');
await leaf.openFile(file);

// Open in split pane
const leaf = this.app.workspace.getLeaf('split');
await leaf.openFile(file);

// Open in new window
const leaf = this.app.workspace.getLeaf('window');
await leaf.openFile(file);
```

### getLeaf vs createLeafInParent

For sidebar views, do not use `getLeaf()`. Instead, use `getLeftLeaf` or `getRightLeaf`:

```typescript
// Get or create a leaf in the left sidebar
getLeftLeaf(split: boolean): WorkspaceLeaf | null;

// Get or create a leaf in the right sidebar
getRightLeaf(split: boolean): WorkspaceLeaf | null;
```

```typescript
// Open view in right sidebar
const leaf = this.app.workspace.getRightLeaf(false);
if (leaf) {
  await leaf.setViewState({
    type: MY_VIEW_TYPE,
    active: true,
  });
  this.app.workspace.revealLeaf(leaf);
}
```

### revealLeaf

Make a leaf visible and active:

```typescript
revealLeaf(leaf: WorkspaceLeaf): void;
```

This expands the sidebar if the leaf is in a sidebar, and activates the tab.

## Iterating Over Leaves

### iterateAllLeaves

Visit every leaf in the workspace:

```typescript
iterateAllLeaves(callback: (leaf: WorkspaceLeaf) => any): void;
```

### iterateRootLeaves

Visit only leaves in the main content area (not sidebars):

```typescript
iterateRootLeaves(callback: (leaf: WorkspaceLeaf) => any): void;
```

### getLeavesOfType

Get all leaves showing a specific view type:

```typescript
getLeavesOfType(viewType: string): WorkspaceLeaf[];
```

```typescript
// Find all open markdown editors
const markdownLeaves = this.app.workspace.getLeavesOfType('markdown');

// Find leaves with our custom view
const myLeaves = this.app.workspace.getLeavesOfType(MY_VIEW_TYPE);
if (myLeaves.length > 0) {
  // View already open, reveal it
  this.app.workspace.revealLeaf(myLeaves[0]);
} else {
  // Create new leaf
  const leaf = this.app.workspace.getRightLeaf(false);
  await leaf?.setViewState({ type: MY_VIEW_TYPE, active: true });
}
```

## View Registration Pattern

### Registering a Custom View

```typescript
// In plugin onload()
this.registerView(
  MY_VIEW_TYPE,
  (leaf: WorkspaceLeaf) => new MyView(leaf)
);
```

### Activating a View (Singleton Pattern)

A common pattern for views that should only have one instance:

```typescript
const VIEW_TYPE = 'my-custom-view';

async activateView(): Promise<void> {
  const { workspace } = this.app;

  // Check if view is already open
  let leaf = workspace.getLeavesOfType(VIEW_TYPE)[0];

  if (!leaf) {
    // Create in right sidebar
    const newLeaf = workspace.getRightLeaf(false);
    if (!newLeaf) return;
    leaf = newLeaf;
    await leaf.setViewState({
      type: VIEW_TYPE,
      active: true,
    });
  }

  // Reveal and focus
  workspace.revealLeaf(leaf);
}
```

### Detaching Views on Unload

Clean up custom views when the plugin is disabled:

```typescript
onunload() {
  // Close all leaves showing our view
  this.app.workspace.detachLeavesOfType(MY_VIEW_TYPE);
}
```

```typescript
detachLeavesOfType(viewType: string): void;
```

## WorkspaceLeaf

A container for a single view instance.

```typescript
interface WorkspaceLeaf extends WorkspaceItem {
  view: View;

  // Open a file in this leaf
  openFile(file: TFile, openState?: OpenViewState): Promise<void>;

  // Set the view state (switch view types)
  setViewState(viewState: ViewState, eState?: any): Promise<void>;

  // Get current view state
  getViewState(): ViewState;

  // Detach (close) this leaf
  detach(): void;

  // Set pinned state
  setPinned(pinned: boolean): void;

  // Set the ephemeral (preview) state
  setEphemeralState(state: any): void;

  // Get the display text shown in the tab
  getDisplayText(): string;
}

interface ViewState {
  type: string;         // View type ID
  state?: any;          // View-specific state
  active?: boolean;     // Whether to activate
  pinned?: boolean;     // Whether tab is pinned
  group?: WorkspaceLeaf;
}

interface OpenViewState {
  state?: any;
  eState?: any;          // Ephemeral state (scroll position, cursor, etc.)
  active?: boolean;
}
```

## View Base Class

All views extend the `View` class:

```typescript
abstract class View extends Component {
  app: App;
  leaf: WorkspaceLeaf;
  containerEl: HTMLElement;
  contentEl: HTMLElement;    // Main content container
  icon: string;              // Lucide icon name for the tab

  // Must implement
  abstract getViewType(): string;
  abstract getDisplayText(): string;

  // Lifecycle
  async onOpen(): Promise<void>;
  async onClose(): Promise<void>;

  // State management
  getState(): any;
  setState(state: any, result: ViewStateResult): Promise<void>;
  getEphemeralState(): any;
  setEphemeralState(state: any): void;

  // Navigation
  navigation: boolean;  // Whether this view supports back/forward navigation
}
```

### ItemView

Base class for views that display non-file content:

```typescript
abstract class ItemView extends View {
  contentEl: HTMLElement;

  addAction(icon: string, title: string, callback: (evt: MouseEvent) => any): HTMLElement;
}
```

The `addAction` method adds action buttons to the view header (top right corner of the pane).

```typescript
class MyView extends ItemView {
  getViewType(): string { return MY_VIEW_TYPE; }
  getDisplayText(): string { return 'My View'; }

  async onOpen(): Promise<void> {
    const container = this.contentEl;
    container.empty();
    container.addClass('my-view-container');

    // Add header action buttons
    this.addAction('refresh-cw', 'Refresh', () => {
      this.refresh();
    });

    this.addAction('settings', 'Settings', () => {
      // Open settings
    });

    // Build UI
    container.createEl('h2', { text: 'My Custom View' });
  }

  async onClose(): Promise<void> {
    this.contentEl.empty();
  }
}
```

### TextFileView

Base class for views that edit text files:

```typescript
abstract class TextFileView extends EditableFileView {
  data: string;           // Current file content
  requestSave(): void;    // Request debounced save

  abstract getViewData(): string;
  abstract setViewData(data: string, clear: boolean): void;
  abstract clear(): void;
}
```

## Workspace Events

The workspace emits events for layout and navigation changes:

```typescript
// Leaf/view changes
workspace.on('active-leaf-change', (leaf: WorkspaceLeaf | null) => void);
workspace.on('leaf-change', (leaf: WorkspaceLeaf) => void);  // Deprecated

// File events
workspace.on('file-open', (file: TFile | null) => void);
workspace.on('file-menu', (menu: Menu, file: TAbstractFile, source: string, leaf?: WorkspaceLeaf) => void);

// Editor events
workspace.on('editor-change', (editor: Editor, info: MarkdownView | MarkdownFileInfo) => void);
workspace.on('editor-paste', (evt: ClipboardEvent, editor: Editor, info: MarkdownView | MarkdownFileInfo) => void);
workspace.on('editor-drop', (evt: DragEvent, editor: Editor, info: MarkdownView | MarkdownFileInfo) => void);
workspace.on('editor-menu', (menu: Menu, editor: Editor, info: MarkdownView | MarkdownFileInfo) => void);

// Layout events
workspace.on('layout-change', () => void);
workspace.on('resize', () => void);
workspace.on('layout-ready', () => void);
workspace.on('window-open', (win: WorkspaceWindow, window: Window) => void);
workspace.on('window-close', (win: WorkspaceWindow, window: Window) => void);

// Quick preview (hover preview)
workspace.on('hover-link', (info: HoverLinkInfo) => void);

// CSS theme changes
workspace.on('css-change', () => void);

// Click/navigation events
workspace.on('url-menu', (menu: Menu, url: string) => void);
```

### Registering Workspace Events

Always use `registerEvent` for auto-cleanup:

```typescript
// In onload()
this.registerEvent(
  this.app.workspace.on('active-leaf-change', (leaf) => {
    if (leaf) {
      const viewType = leaf.view.getViewType();
      console.log('Switched to:', viewType);
    }
  })
);

this.registerEvent(
  this.app.workspace.on('file-open', (file) => {
    if (file) {
      console.log('Opened:', file.path);
    }
  })
);
```

## Layout Ready

The workspace layout may not be ready during plugin load. Use `onLayoutReady` for operations that need the full workspace:

```typescript
async onload() {
  // Safe to register commands, views, etc.
  this.registerView(MY_VIEW_TYPE, (leaf) => new MyView(leaf));

  // Wait for layout to be ready before manipulating workspace
  this.app.workspace.onLayoutReady(() => {
    this.initializeView();
  });
}
```

```typescript
onLayoutReady(callback: () => any): void;
```

If the layout is already ready when called, the callback executes immediately.

## Menu API

Create context menus and dropdown menus:

```typescript
class Menu {
  addItem(cb: (item: MenuItem) => any): this;
  addSeparator(): this;
  showAtMouseEvent(evt: MouseEvent): this;
  showAtPosition(position: Point): this;
  hide(): this;
}

class MenuItem {
  setTitle(title: string | DocumentFragment): this;
  setIcon(icon: string | null): this;
  setChecked(checked: boolean | null): this;
  setDisabled(disabled: boolean): this;
  setIsLabel(isLabel: boolean): this;
  setSection(section: string): this;
  onClick(callback: (evt: MouseEvent | KeyboardEvent) => any): this;
  setSubmenu(): Menu;
}
```

### Adding to File Menu

```typescript
this.registerEvent(
  this.app.workspace.on('file-menu', (menu, file, source) => {
    menu.addItem((item) => {
      item.setTitle('Process file')
          .setIcon('zap')
          .onClick(async () => {
            if (file instanceof TFile) {
              await this.processFile(file);
            }
          });
    });
  })
);
```

### Adding to Editor Menu

```typescript
this.registerEvent(
  this.app.workspace.on('editor-menu', (menu, editor, info) => {
    menu.addItem((item) => {
      item.setTitle('Transform selection')
          .setIcon('wand')
          .setDisabled(!editor.somethingSelected())
          .onClick(() => {
            const text = editor.getSelection();
            editor.replaceSelection(this.transform(text));
          });
    });
  })
);
```

## Workspace Layouts and Serialization

Save and restore workspace layout state:

```typescript
// Get current layout
const layout = this.app.workspace.getLayout();

// Restore layout
await this.app.workspace.changeLayout(layout);
```

Views should implement `getState()` and `setState()` to persist their state across sessions:

```typescript
class MyView extends ItemView {
  currentFilter: string = '';

  getState(): any {
    return { filter: this.currentFilter };
  }

  async setState(state: any, result: ViewStateResult): Promise<void> {
    if (state.filter) {
      this.currentFilter = state.filter;
      this.applyFilter();
    }
    return super.setState(state, result);
  }
}
```

## Common Patterns

### Open or Reveal a View

```typescript
async ensureViewOpen(viewType: string): Promise<View | null> {
  const { workspace } = this.app;
  const leaves = workspace.getLeavesOfType(viewType);

  if (leaves.length > 0) {
    workspace.revealLeaf(leaves[0]);
    return leaves[0].view;
  }

  const leaf = workspace.getRightLeaf(false);
  if (!leaf) return null;

  await leaf.setViewState({ type: viewType, active: true });
  workspace.revealLeaf(leaf);
  return leaf.view;
}
```

### Open File at Line

```typescript
async openFileAtLine(file: TFile, line: number): Promise<void> {
  const leaf = this.app.workspace.getLeaf('tab');
  await leaf.openFile(file, {
    eState: { line }
  });
}
```

### Respond to Active File Changes

```typescript
this.registerEvent(
  this.app.workspace.on('active-leaf-change', (leaf) => {
    const file = this.app.workspace.getActiveFile();
    if (file && file.extension === 'md') {
      this.handleActiveFileChange(file);
    }
  })
);
```

### Check if View is Visible

```typescript
function isViewVisible(workspace: Workspace, viewType: string): boolean {
  const leaves = workspace.getLeavesOfType(viewType);
  return leaves.length > 0;
}
```

### Split Pane Direction

When creating a split, you can specify direction:

```typescript
// Horizontal split (side by side)
workspace.createLeafBySplit(existingLeaf, 'horizontal');

// Vertical split (top and bottom)
workspace.createLeafBySplit(existingLeaf, 'vertical');
```

```typescript
createLeafBySplit(leaf: WorkspaceLeaf, direction?: SplitDirection, before?: boolean): WorkspaceLeaf;
```
