import {
  ItemView,
  MarkdownRenderer,
  Plugin,
  WorkspaceLeaf,
} from 'obsidian';

/**
 * Complete Chat View Example
 *
 * A full ChatView implementation with:
 * - Sidebar panel via ItemView
 * - Message history with user/assistant roles
 * - Markdown rendering for assistant responses
 * - Streaming text display
 * - Active note context bar
 * - Tool call indicators with expandable details
 * - Thread management (multiple conversations)
 * - Loading states and error handling
 * - Keyboard shortcuts (Enter to send, Shift+Enter for newline)
 */

export const VIEW_TYPE_CHAT = 'my-plugin-chat';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export class ChatView extends ItemView {
  private plugin: Plugin;
  private messagesContainer: HTMLElement;
  private inputEl: HTMLTextAreaElement;
  private contextBar: HTMLElement;
  private threads: Map<string, Message[]> = new Map();
  private currentThreadId = 'default';
  private isStreaming = false;

  constructor(leaf: WorkspaceLeaf, plugin: Plugin) {
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
    return 'message-square';
  }

  async onOpen(): Promise<void> {
    const container = this.containerEl.children[1] as HTMLElement;
    container.empty();
    container.addClass('chat-view');

    // Header with thread controls
    const header = container.createDiv({ cls: 'chat-header' });
    header.createEl('span', { text: 'Chat', cls: 'chat-title' });

    const headerActions = header.createDiv({ cls: 'chat-header-actions' });
    const newThreadBtn = headerActions.createEl('button', {
      text: 'New thread',
      cls: 'chat-new-thread-btn',
    });
    newThreadBtn.addEventListener('click', () => this.createNewThread());

    // Context bar showing active note
    this.contextBar = container.createDiv({ cls: 'chat-context-bar' });
    this.updateContextBar();

    // Listen for active file changes
    this.registerEvent(
      this.app.workspace.on('active-leaf-change', () => {
        this.updateContextBar();
      })
    );

    // Scrollable messages area
    this.messagesContainer = container.createDiv({ cls: 'chat-messages' });

    // Input area
    const inputArea = container.createDiv({ cls: 'chat-input-area' });
    this.inputEl = inputArea.createEl('textarea', {
      cls: 'chat-input',
      attr: { placeholder: 'Ask a question...', rows: '3' },
    });

    const sendBtn = inputArea.createEl('button', {
      text: 'Send',
      cls: 'chat-send-btn',
    });

    sendBtn.addEventListener('click', () => void this.handleSend());

    this.inputEl.addEventListener('keydown', (e: KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        void this.handleSend();
      }
    });

    // Initialize default thread
    this.threads.set('default', []);
  }

  async onClose(): Promise<void> {
    // ItemView handles DOM cleanup automatically
  }

  // --- Context Bar ---

  private updateContextBar(): void {
    this.contextBar.empty();
    const activeFile = this.app.workspace.getActiveFile();

    if (activeFile) {
      this.contextBar.createEl('span', {
        text: `Context: ${activeFile.basename}`,
        cls: 'context-file',
      });
    } else {
      this.contextBar.createEl('span', {
        text: 'No active file',
        cls: 'context-empty',
      });
    }
  }

  // --- Message Rendering ---

  private addMessage(role: 'user' | 'assistant', content: string): HTMLElement {
    const msgEl = this.messagesContainer.createDiv({
      cls: `chat-message chat-message-${role}`,
    });

    const labelEl = msgEl.createDiv({ cls: 'chat-message-label' });
    labelEl.setText(role === 'user' ? 'You' : 'Assistant');

    const contentEl = msgEl.createDiv({ cls: 'chat-message-content' });

    if (role === 'assistant' && content) {
      void MarkdownRenderer.render(this.app, content, contentEl, '', this);
    } else {
      contentEl.setText(content);
    }

    this.scrollToBottom();
    return contentEl;
  }

  private scrollToBottom(): void {
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  }

  // --- Tool Call Indicators ---

  private addToolCallIndicator(toolName: string): HTMLElement {
    const indicator = this.messagesContainer.createDiv({
      cls: 'chat-tool-call',
    });

    const header = indicator.createDiv({ cls: 'chat-tool-call-header' });
    header.createEl('span', {
      text: `Used: ${toolName}`,
      cls: 'chat-tool-call-name',
    });

    const toggle = header.createEl('span', {
      text: '\u25b6',
      cls: 'chat-tool-call-toggle',
    });

    const details = indicator.createDiv({ cls: 'chat-tool-call-details' });
    details.style.display = 'none';

    header.addEventListener('click', () => {
      const isHidden = details.style.display === 'none';
      details.style.display = isHidden ? 'block' : 'none';
      toggle.setText(isHidden ? '\u25bc' : '\u25b6');
    });

    this.scrollToBottom();
    return details;
  }

  // --- Loading State ---

  private showLoading(): HTMLElement {
    const loadingEl = this.messagesContainer.createDiv({
      cls: 'chat-loading',
    });
    loadingEl.createEl('span', { text: 'Thinking...' });
    this.scrollToBottom();
    return loadingEl;
  }

  // --- Send and Stream ---

  private async handleSend(): Promise<void> {
    const text = this.inputEl.value.trim();
    if (!text || this.isStreaming) return;

    this.inputEl.value = '';
    this.inputEl.disabled = true;
    this.isStreaming = true;

    // Store user message
    this.addMessage('user', text);
    this.storeMessage({ role: 'user', content: text });

    // Create assistant message container for streaming
    const assistantEl = this.addMessage('assistant', '');
    let fullText = '';

    try {
      // Replace this with your actual streaming API call.
      // See streaming-handler.ts for a reusable streaming class.
      for await (const token of this.streamResponse(text)) {
        fullText += token;
        assistantEl.setText(fullText);
        this.scrollToBottom();
      }

      // Re-render with markdown once streaming is complete
      assistantEl.empty();
      await MarkdownRenderer.render(this.app, fullText, assistantEl, '', this);

      this.storeMessage({ role: 'assistant', content: fullText });
    } catch (error) {
      assistantEl.empty();
      assistantEl.createDiv({
        cls: 'chat-error',
        text: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    } finally {
      this.inputEl.disabled = false;
      this.inputEl.focus();
      this.isStreaming = false;
    }
  }

  /**
   * Placeholder streaming generator. Replace with actual API integration.
   * See the langgraph-sse-client skill for SSE-based streaming.
   */
  private async *streamResponse(userMessage: string): AsyncGenerator<string> {
    const words = `This is a placeholder response to: "${userMessage}". Replace this generator with your actual streaming API call.`.split(' ');
    for (const word of words) {
      await new Promise((resolve) => setTimeout(resolve, 50));
      yield word + ' ';
    }
  }

  // --- Thread Management ---

  private storeMessage(msg: Message): void {
    const messages = this.threads.get(this.currentThreadId) || [];
    messages.push(msg);
    this.threads.set(this.currentThreadId, messages);
  }

  private createNewThread(): void {
    const threadId = `thread-${Date.now()}`;
    this.threads.set(threadId, []);
    this.currentThreadId = threadId;
    this.messagesContainer.empty();
  }

  private selectThread(threadId: string): void {
    if (!this.threads.has(threadId)) return;
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
}

/**
 * Plugin registration helper.
 * Add this to your main plugin class onload():
 *
 *   this.registerView(VIEW_TYPE_CHAT, (leaf) => new ChatView(leaf, this));
 *
 *   this.addCommand({
 *     id: 'open-chat',
 *     name: 'Open chat',
 *     callback: () => void this.activateChat(),
 *   });
 *
 *   this.addRibbonIcon('message-square', 'Open chat', () => {
 *     void this.activateChat();
 *   });
 */
export async function activateChat(plugin: Plugin): Promise<void> {
  const { workspace } = plugin.app;
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
