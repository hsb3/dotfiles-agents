import { MarkdownRenderer, Component } from 'obsidian';

/**
 * Streaming Handler Example
 *
 * A reusable class for handling streamed responses in a chat UI.
 * Manages the lifecycle of a streaming message:
 * - Accumulates tokens into a buffer
 * - Updates the DOM with plain text during streaming
 * - Re-renders with Markdown once the stream completes
 * - Handles errors and cancellation via AbortController
 *
 * Usage:
 *   const handler = new StreamingHandler(contentEl, app, component);
 *   await handler.stream(asyncTokenGenerator);
 *   const fullText = handler.getText();
 */

interface StreamingHandlerOptions {
  /** Element to render streamed content into */
  contentEl: HTMLElement;
  /** Obsidian App instance (needed for MarkdownRenderer) */
  app: App;
  /** Component owner for MarkdownRenderer lifecycle */
  owner: Component;
  /** Called on each token for side effects like auto-scroll */
  onToken?: (fullText: string) => void;
  /** Called when the stream finishes successfully */
  onComplete?: (fullText: string) => void;
  /** Called if the stream errors */
  onError?: (error: Error) => void;
}

export class StreamingHandler {
  private contentEl: HTMLElement;
  private app: App;
  private owner: Component;
  private buffer = '';
  private abortController: AbortController | null = null;
  private onToken?: (fullText: string) => void;
  private onComplete?: (fullText: string) => void;
  private onError?: (error: Error) => void;

  constructor(options: StreamingHandlerOptions) {
    this.contentEl = options.contentEl;
    this.app = options.app;
    this.owner = options.owner;
    this.onToken = options.onToken;
    this.onComplete = options.onComplete;
    this.onError = options.onError;
  }

  /** Returns the full accumulated text */
  getText(): string {
    return this.buffer;
  }

  /** Abort the current stream */
  abort(): void {
    this.abortController?.abort();
  }

  /**
   * Consume an async generator of string tokens, updating the DOM
   * with plain text as tokens arrive. Once complete, re-render
   * the full text as Markdown.
   */
  async stream(tokens: AsyncIterable<string>): Promise<string> {
    this.buffer = '';
    this.abortController = new AbortController();
    const { signal } = this.abortController;

    try {
      for await (const token of tokens) {
        if (signal.aborted) break;

        this.buffer += token;
        // Plain text update during streaming for performance
        this.contentEl.setText(this.buffer);
        this.onToken?.(this.buffer);
      }

      if (!signal.aborted) {
        // Re-render as Markdown once streaming is done
        await this.renderMarkdown(this.buffer);
        this.onComplete?.(this.buffer);
      }
    } catch (error) {
      if (!signal.aborted) {
        const err = error instanceof Error ? error : new Error(String(error));
        this.renderError(err);
        this.onError?.(err);
        throw err;
      }
    } finally {
      this.abortController = null;
    }

    return this.buffer;
  }

  /**
   * Stream from a fetch Response with SSE (Server-Sent Events).
   * Parses the standard `data: {...}` format used by most LLM APIs.
   *
   * Expects each SSE data line to be JSON with a `content` field
   * containing the token text. Adjust the parser for your API format.
   */
  async streamSSE(
    response: Response,
    parseToken: (data: string) => string | null = defaultSSEParser
  ): Promise<string> {
    if (!response.body) {
      throw new Error('Response has no body');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    async function* tokenGenerator(): AsyncGenerator<string> {
      let partial = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        partial += decoder.decode(value, { stream: true });
        const lines = partial.split('\n');
        // Keep the last partial line for next iteration
        partial = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;

          const data = line.slice(6).trim();
          if (data === '[DONE]') return;

          const token = parseToken(data);
          if (token) yield token;
        }
      }
    }

    return this.stream(tokenGenerator());
  }

  private async renderMarkdown(text: string): Promise<void> {
    this.contentEl.empty();
    await MarkdownRenderer.render(this.app, text, this.contentEl, '', this.owner);
  }

  private renderError(error: Error): void {
    this.contentEl.empty();
    this.contentEl.createDiv({
      cls: 'chat-error',
      text: `Error: ${error.message}`,
    });
  }
}

/**
 * Default SSE data parser. Handles the common OpenAI-style format:
 *   data: {"choices":[{"delta":{"content":"token"}}]}
 *
 * Override this with your own parser if your API uses a different format.
 */
function defaultSSEParser(data: string): string | null {
  try {
    const parsed = JSON.parse(data);
    // OpenAI chat completion format
    return parsed?.choices?.[0]?.delta?.content ?? null;
  } catch {
    return null;
  }
}

/**
 * Integration example with ChatView:
 *
 *   // In handleSend():
 *   const contentEl = this.addMessage('assistant', '');
 *
 *   const handler = new StreamingHandler({
 *     contentEl,
 *     app: this.app,
 *     owner: this,
 *     onToken: () => this.scrollToBottom(),
 *   });
 *
 *   // Option A: Stream from an async generator
 *   await handler.stream(myAsyncTokenGenerator(userMessage));
 *
 *   // Option B: Stream from an SSE endpoint
 *   const response = await fetch('http://localhost:8000/stream', {
 *     method: 'POST',
 *     headers: { 'Content-Type': 'application/json' },
 *     body: JSON.stringify({ message: userMessage }),
 *   });
 *   await handler.streamSSE(response);
 *
 *   // Get the full text for storage
 *   const fullText = handler.getText();
 */
