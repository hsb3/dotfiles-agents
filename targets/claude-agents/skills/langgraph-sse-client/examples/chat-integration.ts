/**
 * Chat Integration Example
 *
 * Shows how to wire the SSE streaming client into an Obsidian
 * ItemView-based chat sidebar with:
 * - Token-by-token rendering
 * - Batched DOM updates for performance
 * - Tool call indicators
 * - Final markdown rendering
 * - Conversation history management
 * - Cancellation support
 */

import { ItemView, MarkdownRenderer, WorkspaceLeaf } from 'obsidian';
import { streamLangGraph, generateThreadId } from './complete-sse-client';
import type { StreamEvent } from './complete-sse-client';
import type { Plugin } from 'obsidian';

// ── Types ──────────────────────────────────────────────────────────────

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface ChatPluginSettings {
  serverUrl: string;
  apiKey?: string;
  assistantId: string;
}

// ── Chat View ──────────────────────────────────────────────────────────

export const CHAT_VIEW_TYPE = 'langgraph-chat';

export class ChatView extends ItemView {
  private plugin: Plugin & { settings: ChatPluginSettings };
  private threadId: string;
  private messages: ChatMessage[] = [];
  private messagesEl: HTMLElement;
  private inputEl: HTMLTextAreaElement;
  private abortController: AbortController | null = null;

  constructor(leaf: WorkspaceLeaf, plugin: Plugin & { settings: ChatPluginSettings }) {
    super(leaf);
    this.plugin = plugin;
    this.threadId = generateThreadId();
  }

  getViewType(): string {
    return CHAT_VIEW_TYPE;
  }

  getDisplayText(): string {
    return 'LangGraph Chat';
  }

  getIcon(): string {
    return 'message-square';
  }

  async onOpen(): Promise<void> {
    const container = this.containerEl.children[1] as HTMLElement;
    container.empty();
    container.addClass('langgraph-chat-container');

    // Messages area
    this.messagesEl = container.createDiv({ cls: 'chat-messages' });

    // Input area
    const inputArea = container.createDiv({ cls: 'chat-input-area' });

    this.inputEl = inputArea.createEl('textarea', {
      cls: 'chat-input',
      attr: { placeholder: 'Type a message...', rows: '2' },
    });

    // Send on Enter (Shift+Enter for newline)
    this.inputEl.addEventListener('keydown', (e: KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.handleSend();
      }
    });

    // Action buttons
    const actions = inputArea.createDiv({ cls: 'chat-actions' });

    const sendBtn = actions.createEl('button', { text: 'Send', cls: 'chat-send-btn' });
    sendBtn.addEventListener('click', () => this.handleSend());

    const newBtn = actions.createEl('button', { text: 'New Chat', cls: 'chat-new-btn' });
    newBtn.addEventListener('click', () => this.newThread());

    const cancelBtn = actions.createEl('button', { text: 'Cancel', cls: 'chat-cancel-btn' });
    cancelBtn.addEventListener('click', () => this.cancelStream());
    cancelBtn.style.display = 'none';
    this.cancelBtn = cancelBtn;
  }

  private cancelBtn: HTMLButtonElement;

  async onClose(): Promise<void> {
    this.cancelStream();
  }

  // ── Send Message ───────────────────────────────────────────────────

  private async handleSend(): Promise<void> {
    const text = this.inputEl.value.trim();
    if (!text) return;

    this.inputEl.value = '';
    this.setInputEnabled(false);

    // Add user message to UI and history
    this.addMessageEl('user', text);
    this.messages.push({ role: 'user', content: text });

    // Create assistant message container
    const contentEl = this.addMessageEl('assistant', '');
    let fullText = '';

    this.abortController = new AbortController();

    try {
      const activeFile = this.app.workspace.getActiveFile();

      const stream = streamLangGraph(
        this.plugin.settings.serverUrl,
        this.threadId,
        this.plugin.settings.assistantId,
        this.messages,
        { active_note_path: activeFile?.path ?? null },
        {
          signal: this.abortController.signal,
          apiKey: this.plugin.settings.apiKey,
        },
      );

      fullText = await this.consumeStream(stream, contentEl);

      // Render final markdown
      contentEl.empty();
      await MarkdownRenderer.render(this.app, fullText, contentEl, '', this);

      // Add to history
      this.messages.push({ role: 'assistant', content: fullText });
    } catch (error) {
      contentEl.empty();
      contentEl.createDiv({
        cls: 'chat-error',
        text: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    } finally {
      this.abortController = null;
      this.setInputEnabled(true);
    }
  }

  // ── Stream Consumer with Batched Updates ───────────────────────────

  private async consumeStream(
    stream: AsyncGenerator<StreamEvent>,
    contentEl: HTMLElement,
  ): Promise<string> {
    let fullText = '';
    let pending = '';
    let batchTimer: ReturnType<typeof setTimeout> | null = null;

    const flush = () => {
      if (pending) {
        fullText += pending;
        contentEl.setText(fullText);
        pending = '';
        this.scrollToBottom();
      }
    };

    for await (const event of stream) {
      switch (event.type) {
        case 'token':
          pending += event.content ?? '';
          // Batch DOM updates every 50ms
          if (!batchTimer) {
            batchTimer = setTimeout(() => {
              flush();
              batchTimer = null;
            }, 50);
          }
          break;

        case 'tool_call':
          flush();
          this.addToolIndicator(contentEl, event.toolName ?? 'tool');
          break;

        case 'tool_result':
          // Tool results are handled server-side, optionally show them
          break;

        case 'error':
          flush();
          contentEl.createDiv({
            cls: 'chat-error',
            text: event.content ?? 'Stream error',
          });
          break;

        case 'end':
          break;
      }
    }

    // Flush remaining tokens
    if (batchTimer) clearTimeout(batchTimer);
    flush();

    return fullText;
  }

  // ── UI Helpers ─────────────────────────────────────────────────────

  private addMessageEl(role: 'user' | 'assistant', text: string): HTMLElement {
    const wrapper = this.messagesEl.createDiv({ cls: `chat-message chat-${role}` });
    const label = role === 'user' ? 'You' : 'Assistant';
    wrapper.createDiv({ cls: 'chat-role', text: label });
    const contentEl = wrapper.createDiv({ cls: 'chat-content' });
    if (text) contentEl.setText(text);
    this.scrollToBottom();
    return contentEl;
  }

  private addToolIndicator(parentEl: HTMLElement, toolName: string): void {
    parentEl.createDiv({
      cls: 'chat-tool-indicator',
      text: `Using tool: ${toolName}`,
    });
  }

  private scrollToBottom(): void {
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  }

  private setInputEnabled(enabled: boolean): void {
    this.inputEl.disabled = !enabled;
    this.cancelBtn.style.display = enabled ? 'none' : 'inline-block';
    if (enabled) this.inputEl.focus();
  }

  private cancelStream(): void {
    this.abortController?.abort();
  }

  private newThread(): void {
    this.threadId = generateThreadId();
    this.messages = [];
    this.messagesEl.empty();
    this.inputEl.focus();
  }
}
