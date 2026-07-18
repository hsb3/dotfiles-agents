# ItemView API Reference

Complete reference for Obsidian's `ItemView` class, the foundation for building custom sidebar panels including chat interfaces.

## Class Hierarchy

```
View
  └── ItemView
        └── Your ChatView
```

`ItemView` extends `View` and provides the standard Obsidian panel structure with a header (icon, title, menu) and a content area.

## Constructor

```typescript
constructor(leaf: WorkspaceLeaf)
```

Always call `super(leaf)` first. Pass additional dependencies (like your plugin instance) as extra constructor parameters:

```typescript
class ChatView extends ItemView {
  constructor(leaf: WorkspaceLeaf, private plugin: MyPlugin) {
    super(leaf);
  }
}
```

## Required Overrides

### `getViewType(): string`

Returns a unique string identifier for this view type. Must match the string used in `registerView()`.

```typescript
getViewType(): string {
  return 'my-plugin-chat';
}
```

### `getDisplayText(): string`

Returns the human-readable title shown in the tab header.

```typescript
getDisplayText(): string {
  return 'Chat';
}
```

## Optional Overrides

### `getIcon(): string`

Returns a Lucide icon name for the tab. Defaults to `'document'`. Common choices for chat:

- `'message-square'` - chat bubble
- `'messages-square'` - multiple chat bubbles
- `'bot'` - robot/AI
- `'sparkles'` - AI/magic

```typescript
getIcon(): string {
  return 'message-square';
}
```

### `async onOpen(): Promise<void>`

Called when the view is first displayed. Build your UI here.

The container element has two children:
- `this.containerEl.children[0]` - Reserved by Obsidian for the view header (icon, title, menu buttons). Do not modify.
- `this.containerEl.children[1]` - Your content area. Build your UI here.

```typescript
async onOpen(): Promise<void> {
  const container = this.containerEl.children[1] as HTMLElement;
  container.empty();
  container.addClass('chat-view');
  // Build your UI...
}
```

### `async onClose(): Promise<void>`

Called when the view is closed. Use for cleanup beyond DOM removal (which is automatic). Common uses: cancel pending requests, close WebSocket connections, save state.

```typescript
async onClose(): Promise<void> {
  this.abortController?.abort();
}
```

## Inherited Properties

| Property | Type | Description |
|----------|------|-------------|
| `this.app` | `App` | The Obsidian App instance |
| `this.containerEl` | `HTMLElement` | Root container element |
| `this.leaf` | `WorkspaceLeaf` | The workspace leaf hosting this view |
| `this.icon` | `string` | Current icon (can be set dynamically) |

## Inherited Methods from Component

`ItemView` extends `Component`, giving you lifecycle management:

### `this.registerEvent(eventRef)`

Register an event that is automatically unregistered when the view closes.

```typescript
this.registerEvent(
  this.app.workspace.on('active-leaf-change', () => {
    this.updateContextBar();
  })
);
```

### `this.registerInterval(id)`

Register a `window.setInterval` that is automatically cleared on close.

```typescript
this.registerInterval(
  window.setInterval(() => this.checkForUpdates(), 30000)
);
```

### `this.register(callback)`

Register a generic cleanup callback.

```typescript
const observer = new MutationObserver(callback);
observer.observe(element, { childList: true });
this.register(() => observer.disconnect());
```

### `this.addChild(component)`

Add a child Component whose lifecycle is tied to this view.

```typescript
const childComponent = new MyComponent();
this.addChild(childComponent);
```

## View Registration

Register the view type in your plugin's `onload()`:

```typescript
this.registerView(
  VIEW_TYPE_CHAT,
  (leaf: WorkspaceLeaf) => new ChatView(leaf, this)
);
```

The factory function receives a `WorkspaceLeaf` and must return a `View` instance.

## View State

Views can persist and restore state across sessions:

### `getState(): Record<string, unknown>`

Return serializable state to persist.

```typescript
getState(): Record<string, unknown> {
  return {
    threadId: this.currentThreadId,
  };
}
```

### `async setState(state, result): Promise<void>`

Restore persisted state when the view reopens.

```typescript
async setState(
  state: Record<string, unknown>,
  result: ViewStateResult
): Promise<void> {
  if (typeof state.threadId === 'string') {
    this.currentThreadId = state.threadId;
  }
  await super.setState(state, result);
}
```

## MarkdownRenderer

Use `MarkdownRenderer.render()` to display markdown content (assistant responses):

```typescript
await MarkdownRenderer.render(
  this.app,       // App instance
  markdownText,   // The markdown string
  containerEl,    // Target HTML element
  sourcePath,     // Source file path ('' if none)
  this            // Component owner (for lifecycle)
);
```

The `sourcePath` parameter affects link resolution. Pass `''` for chat content that has no source file, or pass a file path if the content references vault files.

## DOM Helpers

Obsidian extends `HTMLElement` with helper methods:

```typescript
// Create nested elements
container.createDiv({ cls: 'my-class' });
container.createEl('span', { text: 'Hello', cls: 'label' });
container.createEl('textarea', {
  cls: 'input',
  attr: { placeholder: 'Type here', rows: '3' },
});

// Clear contents
container.empty();

// Add/remove classes
container.addClass('active');
container.removeClass('active');
container.toggleClass('visible', isVisible);
```
