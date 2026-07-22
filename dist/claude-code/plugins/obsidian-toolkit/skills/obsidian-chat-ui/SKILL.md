---
name: obsidian-chat-ui
description: This skill should be used when the user asks to "create chat interface", "build sidebar", "ItemView", "streaming messages", "chat sidebar", "copilot UI", or mentions building chat or conversational interfaces in Obsidian plugins.
---

# Obsidian Chat UI

Provides patterns for building chat and copilot-style interfaces in Obsidian plugins using ItemView for sidebar panels with streaming message support.

## ItemView Pattern

Chat interfaces in Obsidian use `ItemView` for sidebar panels:

```typescript
import { ItemView, WorkspaceLeaf } from 'obsidian';

export const VIEW_TYPE_CHAT = 'my-plugin-chat';

export class ChatView extends ItemView {
  private plugin: MyPlugin;

  constructor(leaf: WorkspaceLeaf, plugin: MyPlugin) {
    super(leaf);
    this.plugin = plugin;
  }

  getViewType(): string {
    return VIEW_TYPE_CHAT;
  }

  getDisplayText(): string {
    return 'Chat';
  }

  getIcon(): string {
    return 'message-square';  // Lucide icon name
  }

  async onOpen(): Promise<void> {
    // Build UI here
  }

  async onClose(): Promise<void> {
    // Cleanup (mostly automatic)
  }
}
```

### Registering the View

In `main.ts`:

```typescript
async onload() {
  this.registerView(
    VIEW_TYPE_CHAT,
    (leaf) => new ChatView(leaf, this)
  );

  this.addCommand({
    id: 'open-chat',
    name: 'Open chat',
    callback: () => {
      void this.activateView();
    }
  });

  this.addRibbonIcon('message-square', 'Open chat', () => {
    void this.activateView();
  });
}

async activateView(): Promise<void> {
  const { workspace } = this.app;
  let leaf = workspace.getLeavesOfType(VIEW_TYPE_CHAT)[0];

  if (!leaf) {
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

## Chat UI Layout

Build the chat interface structure:

```typescript
async onOpen(): Promise<void> {
  const container = this.containerEl.children[1];  // Obsidian reserves [0]
  container.empty();
  container.addClass('chat-view');

  // Header
  const header = container.createDiv({ cls: 'chat-header' });
  header.createEl('span', { text: 'Chat', cls: 'chat-title' });

  // Context bar (shows active note)
  const contextBar = container.createDiv({ cls: 'chat-context-bar' });
  this.updateContextBar(contextBar);

  // Messages area (scrollable)
  this.messagesContainer = container.createDiv({ cls: 'chat-messages' });

  // Input area
  const inputArea = container.createDiv({ cls: 'chat-input-area' });
  this.inputEl = inputArea.createEl('textarea', {
    cls: 'chat-input',
    attr: { placeholder: 'Ask a question...', rows: '3' }
  });

  const sendBtn = inputArea.createEl('button', {
    text: 'Send',
    cls: 'chat-send-btn'
  });

  sendBtn.addEventListener('click', () => {
    void this.handleSend();
  });

  this.inputEl.addEventListener('keydown', (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void this.handleSend();
    }
  });
}
```

## Context Bar Pattern

Show the active note context:

```typescript
private updateContextBar(contextBar: HTMLElement): void {
  contextBar.empty();
  const activeFile = this.app.workspace.getActiveFile();

  if (activeFile) {
    contextBar.createEl('span', {
      text: `Context: ${activeFile.basename}`,
      cls: 'context-file'
    });
  } else {
    contextBar.createEl('span', {
      text: 'No active file',
      cls: 'context-empty'
    });
  }
}

// Update when active file changes
this.registerEvent(
  this.app.workspace.on('active-leaf-change', () => {
    this.updateContextBar(contextBar);
  })
);
```

## Message Rendering

Add messages to the chat:

```typescript
private addMessage(
  role: 'user' | 'assistant',
  content: string
): HTMLElement {
  const msgEl = this.messagesContainer.createDiv({
    cls: `chat-message chat-message-${role}`
  });

  const labelEl = msgEl.createDiv({ cls: 'chat-message-label' });
  labelEl.setText(role === 'user' ? 'You' : 'Assistant');

  const contentEl = msgEl.createDiv({ cls: 'chat-message-content' });

  if (role === 'assistant') {
    // Use MarkdownRenderer for assistant messages
    void MarkdownRenderer.render(
      this.app,
      content,
      contentEl,
      '',
      this
    );
  } else {
    contentEl.setText(content);
  }

  // Auto-scroll to bottom
  this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;

  return contentEl;
}
```

## Streaming Text Support

Handle streaming token-by-token:

```typescript
private async handleSend(): Promise<void> {
  const text = this.inputEl.value.trim();
  if (!text) return;

  this.inputEl.value = '';
  this.inputEl.disabled = true;

  // Add user message
  this.addMessage('user', text);

  // Create assistant message container
  const assistantEl = this.addMessage('assistant', '');
  let fullText = '';

  try {
    // Streaming simulation - replace with actual API call
    for await (const token of this.streamResponse(text)) {
      fullText += token;
      assistantEl.setText(fullText);  // Plain text during streaming
      this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    // Replace with markdown rendering when complete
    assistantEl.empty();
    await MarkdownRenderer.render(
      this.app,
      fullText,
      assistantEl,
      '',
      this
    );
  } catch (error) {
    assistantEl.empty();
    assistantEl.createDiv({
      cls: 'chat-error',
      text: `Error: ${error instanceof Error ? error.message : 'Unknown'}`
    });
  } finally {
    this.inputEl.disabled = false;
    this.inputEl.focus();
  }
}
```

## Tool Call Indicators

Show when assistant uses tools:

```typescript
private addToolCallIndicator(
  toolName: string
): HTMLElement {
  const indicator = this.messagesContainer.createDiv({
    cls: 'chat-tool-call'
  });

  const header = indicator.createDiv({ cls: 'chat-tool-call-header' });
  header.createEl('span', {
    text: `Used: ${toolName}`,
    cls: 'chat-tool-call-name'
  });

  const toggle = header.createEl('span', {
    text: '▶',
    cls: 'chat-tool-call-toggle'
  });

  const details = indicator.createDiv({
    cls: 'chat-tool-call-details'
  });
  details.style.display = 'none';

  header.addEventListener('click', () => {
    const isHidden = details.style.display === 'none';
    details.style.display = isHidden ? 'block' : 'none';
    toggle.setText(isHidden ? '▼' : '▶');
  });

  this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;

  return details;
}
```

## Loading State

Show thinking indicator:

```typescript
private showLoading(): HTMLElement {
  const loadingEl = this.messagesContainer.createDiv({
    cls: 'chat-loading'
  });
  loadingEl.createEl('span', { text: 'Thinking...' });

  this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;

  return loadingEl;
}

private hideLoading(loadingEl: HTMLElement): void {
  loadingEl.remove();
}
```

## Styling

Add basic styles in `styles.css`:

```css
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 10px;
}

.chat-header {
  padding: 10px;
  border-bottom: 1px solid var(--background-modifier-border);
  margin-bottom: 10px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  margin-bottom: 10px;
}

.chat-message {
  margin-bottom: 15px;
  padding: 10px;
  border-radius: 5px;
}

.chat-message-user {
  background-color: var(--background-secondary);
}

.chat-message-assistant {
  background-color: var(--background-primary-alt);
}

.chat-message-label {
  font-weight: bold;
  margin-bottom: 5px;
  font-size: 0.9em;
  opacity: 0.7;
}

.chat-input-area {
  display: flex;
  gap: 5px;
}

.chat-input {
  flex: 1;
  resize: vertical;
  padding: 8px;
}

.chat-send-btn {
  padding: 8px 15px;
}

.chat-context-bar {
  padding: 5px 10px;
  background-color: var(--background-secondary);
  border-radius: 3px;
  margin-bottom: 10px;
  font-size: 0.9em;
}

.chat-tool-call {
  margin: 5px 0;
  padding: 5px;
  background-color: var(--background-modifier-border);
  border-radius: 3px;
  font-size: 0.9em;
}

.chat-tool-call-header {
  cursor: pointer;
  display: flex;
  justify-content: space-between;
}

.chat-loading {
  padding: 10px;
  font-style: italic;
  opacity: 0.7;
}

.chat-error {
  color: var(--text-error);
  padding: 10px;
  background-color: var(--background-modifier-error);
  border-radius: 3px;
}
```

## Thread Management

Support multiple conversation threads:

```typescript
private threads: Map<string, Message[]> = new Map();
private currentThreadId: string = 'default';

private selectThread(threadId: string): void {
  // Save current thread
  this.threads.set(this.currentThreadId, this.getCurrentMessages());

  // Load selected thread
  this.currentThreadId = threadId;
  this.renderThread(threadId);
}

private renderThread(threadId: string): void {
  this.messagesContainer.empty();

  const messages = this.threads.get(threadId) || [];
  for (const msg of messages) {
    this.addMessage(msg.role, msg.content);
  }
}
```

## Additional Resources

### Examples

Working examples in `examples/`:
- **`complete-chat-view.ts`** - Full chat view implementation
- **`streaming-handler.ts`** - Streaming message handler

### Reference Files

For detailed patterns:
- **`references/itemview-api.md`** - ItemView API details
- **`references/workspace-integration.md`** - Workspace management

### Official Resources

- [Obsidian Sample Plugin](https://github.com/obsidianmd/obsidian-sample-plugin)
- [WhiskeyJack96/obsidian-agent](https://github.com/WhiskeyJack96/obsidian-agent) - Clean chat UI reference

## Next Steps

After building chat UI:
1. Integrate streaming with `langgraph-sse-client` skill
2. Add MCP server support with `obsidian-mcp-server` skill
3. Review best practices with `obsidian-best-practices` skill
