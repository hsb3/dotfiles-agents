# Workspace Integration Reference

Patterns for managing custom views within Obsidian's workspace system. Covers opening, positioning, revealing, and managing the lifecycle of sidebar panels like chat views.

## Opening a View in the Sidebar

The standard pattern for activating a sidebar view:

```typescript
async activateView(): Promise<void> {
  const { workspace } = this.app;

  // Check if the view already exists
  let leaf = workspace.getLeavesOfType(VIEW_TYPE_CHAT)[0];

  if (!leaf) {
    // Create in right sidebar
    const rightLeaf = workspace.getRightLeaf(false);
    if (rightLeaf) {
      await rightLeaf.setViewState({
        type: VIEW_TYPE_CHAT,
        active: true,
      });
      leaf = rightLeaf;
    }
  }

  if (leaf) {
    workspace.revealLeaf(leaf);
  }
}
```

### `getRightLeaf(shouldSplit)`

- `getRightLeaf(false)` - Reuse existing right sidebar leaf, or create one
- `getRightLeaf(true)` - Always create a new split in the right sidebar

There is also `getLeftLeaf(shouldSplit)` for the left sidebar.

### `setViewState(state)`

Sets the view type and options on a leaf:

```typescript
await leaf.setViewState({
  type: VIEW_TYPE_CHAT,  // Must match registerView() type
  active: true,          // Make this the active tab
  state: {               // Optional: passed to view's setState()
    threadId: 'some-id',
  },
});
```

### `revealLeaf(leaf)`

Makes the leaf visible. If the sidebar is collapsed, this expands it and switches to the correct tab.

## Querying Existing Views

### `getLeavesOfType(type)`

Returns all leaves with a specific view type:

```typescript
const chatLeaves = workspace.getLeavesOfType(VIEW_TYPE_CHAT);

if (chatLeaves.length > 0) {
  const chatView = chatLeaves[0].view as ChatView;
  // Interact with the view
}
```

### Checking if View is Open

```typescript
function isChatOpen(): boolean {
  return this.app.workspace.getLeavesOfType(VIEW_TYPE_CHAT).length > 0;
}
```

## View Positioning Options

### Right Sidebar (most common for chat)

```typescript
const leaf = workspace.getRightLeaf(false);
```

### Left Sidebar

```typescript
const leaf = workspace.getLeftLeaf(false);
```

### Main Editor Area

```typescript
// New tab in main area
const leaf = workspace.getLeaf('tab');

// Split current editor
const leaf = workspace.getLeaf('split');

// Split in specific direction
const leaf = workspace.getLeaf('split', 'horizontal');
```

### Floating Window (Obsidian 1.x+)

```typescript
const leaf = workspace.getLeaf('window');
```

## Workspace Events

Subscribe to workspace events using `registerEvent()` inside your view or plugin for automatic cleanup.

### `active-leaf-change`

Fires when the user switches to a different pane. Useful for updating a context bar that shows the active note.

```typescript
this.registerEvent(
  this.app.workspace.on('active-leaf-change', (leaf) => {
    // leaf is the newly active WorkspaceLeaf, or null
    this.updateContextBar();
  })
);
```

### `file-open`

Fires when a file is opened in any pane.

```typescript
this.registerEvent(
  this.app.workspace.on('file-open', (file) => {
    // file is TFile or null
    if (file) {
      console.log('Opened:', file.path);
    }
  })
);
```

### `layout-change`

Fires when the workspace layout changes (panes resized, tabs moved).

```typescript
this.registerEvent(
  this.app.workspace.on('layout-change', () => {
    // React to layout changes if needed
  })
);
```

### `resize`

Fires when the workspace container is resized.

```typescript
this.registerEvent(
  this.app.workspace.on('resize', () => {
    // Adjust layout if needed
  })
);
```

## Ribbon Icon Integration

Add a sidebar icon that opens your chat view:

```typescript
this.addRibbonIcon('message-square', 'Open chat', () => {
  void this.activateView();
});
```

Parameters: icon name (Lucide), tooltip text, click callback.

## Command Integration

Register a command to open the view:

```typescript
this.addCommand({
  id: 'open-chat',
  name: 'Open chat',
  callback: () => void this.activateView(),
});
```

Users can then bind this to a hotkey via Settings > Hotkeys.

## Detaching Views on Unload

When your plugin unloads, detach all instances of your view:

```typescript
async onunload() {
  this.app.workspace.detachLeavesOfType(VIEW_TYPE_CHAT);
}
```

This ensures no orphaned views remain after the plugin is disabled.

## Singleton View Pattern

Ensure only one instance of your view exists:

```typescript
async activateView(): Promise<void> {
  const { workspace } = this.app;
  const existing = workspace.getLeavesOfType(VIEW_TYPE_CHAT);

  if (existing.length > 0) {
    // Already open, just reveal it
    workspace.revealLeaf(existing[0]);
    return;
  }

  // Not open, create it
  const leaf = workspace.getRightLeaf(false);
  if (leaf) {
    await leaf.setViewState({ type: VIEW_TYPE_CHAT, active: true });
    workspace.revealLeaf(leaf);
  }
}
```

## Reading the Active File

Access the currently active file from anywhere:

```typescript
// Get active file (TFile or null)
const file = this.app.workspace.getActiveFile();

// Read file content
if (file) {
  const content = await this.app.vault.read(file);
}
```

## Communicating Between Views and Plugin

Pass the plugin reference to the view constructor for access to shared state:

```typescript
// In plugin
this.registerView(
  VIEW_TYPE_CHAT,
  (leaf) => new ChatView(leaf, this)
);

// In ChatView
class ChatView extends ItemView {
  constructor(leaf: WorkspaceLeaf, private plugin: MyPlugin) {
    super(leaf);
  }

  someMethod() {
    // Access plugin settings, methods, etc.
    const apiKey = this.plugin.settings.apiKey;
  }
}
```
