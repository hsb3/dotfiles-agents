---
name: langgraph-sse-client
description: This skill should be used when the user asks about "LangGraph streaming", "SSE client", "server-sent events", "messages-tuple", "async generator", "LangGraph API", or mentions implementing streaming from LangGraph servers.
---

# LangGraph SSE Client

Provides patterns for implementing server-sent event (SSE) streaming clients for LangGraph APIs, enabling real-time token streaming in Obsidian plugins.

## Critical: Cannot Use EventSource

**LangGraph requires POST requests** - EventSource only supports GET.

```typescript
// ❌ WRONG - EventSource only does GET
const sse = new EventSource(url);

// ✅ CORRECT - Use fetch() with manual SSE parsing
const response = await fetch(url, { method: 'POST', ... });
```

## LangGraph Request Format

POST to the streaming endpoint:

```typescript
const url = `${serverUrl}/threads/${threadId}/runs/stream`;

const response = await fetch(url, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    assistant_id: 'agent',
    input: {
      messages: [
        { role: 'user', content: userMessage }
      ]
    },
    config: {
      configurable: {
        thread_id: threadId,
        // Custom config fields
        active_note_path: activeFile?.path,
      }
    },
    stream_mode: ['messages-tuple'],  // Required for token streaming
  }),
});
```

**Key fields:**
- `assistant_id` - Agent identifier on server
- `input.messages` - Conversation messages
- `config.configurable` - Thread ID and custom context
- `stream_mode: ['messages-tuple']` - Enable token streaming

## SSE Response Format

LangGraph sends events in SSE format:

```
event: metadata
data: {"run_id": "1efd8e68-...", "attempt": 1}

event: messages
data: [<message_chunk>, <metadata>]

event: messages
data: [<message_chunk>, <metadata>]

event: end
data: null
```

**Each `messages` event contains:**
- `[0]` - Message chunk (the content)
- `[1]` - Metadata (node info, etc.)

**Message chunk structure:**
```json
{
  "content": "partial token text",
  "type": "AIMessageChunk",
  "tool_calls": [],
  "usage_metadata": null
}
```

## Async Generator Pattern

Parse SSE stream with async generator:

```typescript
interface StreamEvent {
  type: 'token' | 'tool_call' | 'tool_result' | 'end' | 'error';
  content?: string;
  toolName?: string;
  toolArgs?: Record<string, unknown>;
}

async function* streamLangGraph(
  serverUrl: string,
  threadId: string,
  assistantId: string,
  messages: Array<{ role: string; content: string }>,
  config?: Record<string, unknown>,
): AsyncGenerator<StreamEvent> {
  const url = `${serverUrl}/threads/${threadId}/runs/stream`;

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      assistant_id: assistantId,
      input: { messages },
      config: {
        configurable: { thread_id: threadId, ...config }
      },
      stream_mode: ['messages-tuple'],
    }),
  });

  if (!response.ok) {
    throw new Error(`LangGraph error: ${response.status} ${response.statusText}`);
  }

  if (!response.body) {
    throw new Error('Response body is null');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE events separated by double newlines
      const parts = buffer.split('\n\n');
      buffer = parts.pop() ?? '';  // Keep incomplete part

      for (const part of parts) {
        if (!part.trim()) continue;

        let eventType = '';
        let eventData = '';

        for (const line of part.split('\n')) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            eventData = line.slice(6);
          }
        }

        if (!eventType || !eventData) continue;

        if (eventType === 'messages') {
          try {
            const [chunk, metadata] = JSON.parse(eventData);

            // Text content from LLM
            if (chunk.type === 'AIMessageChunk' && chunk.content) {
              yield {
                type: 'token',
                content: chunk.content,
              };
            }

            // Tool call initiation
            if (chunk.type === 'AIMessageChunk' && chunk.tool_calls?.length > 0) {
              for (const tc of chunk.tool_calls) {
                if (tc.name) {
                  yield {
                    type: 'tool_call',
                    toolName: tc.name,
                    toolArgs: tc.args,
                  };
                }
              }
            }

            // Tool result
            if (chunk.type === 'ToolMessage') {
              yield {
                type: 'tool_result',
                content: chunk.content,
                toolName: chunk.name,
              };
            }
          } catch (parseError) {
            console.debug('Failed to parse SSE message:', eventData);
          }
        } else if (eventType === 'end') {
          yield { type: 'end' };
        } else if (eventType === 'error') {
          yield { type: 'error', content: eventData };
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
```

## Using in Chat View

Integrate with Obsidian chat UI:

```typescript
private async handleSend(): Promise<void> {
  const text = this.inputEl.value.trim();
  if (!text) return;

  this.inputEl.value = '';
  this.inputEl.disabled = true;

  this.addMessage('user', text);

  const contentEl = this.addMessage('assistant', '');
  let fullText = '';

  try {
    const activeFile = this.app.workspace.getActiveFile();

    const stream = streamLangGraph(
      this.plugin.settings.serverUrl,
      this.threadId,
      'agent',
      [{ role: 'user', content: text }],
      { active_note_path: activeFile?.path ?? null },
    );

    for await (const event of stream) {
      switch (event.type) {
        case 'token':
          fullText += event.content ?? '';
          contentEl.setText(fullText);  // Plain text during streaming
          this.scrollToBottom();
          break;

        case 'tool_call':
          this.addToolCallIndicator(
            event.toolName ?? 'unknown'
          );
          break;

        case 'end':
          // Replace with markdown rendering
          contentEl.empty();
          await MarkdownRenderer.render(
            this.app,
            fullText,
            contentEl,
            '',
            this
          );
          break;

        case 'error':
          contentEl.empty();
          contentEl.createDiv({
            cls: 'error',
            text: `Error: ${event.content ?? 'Unknown error'}`,
          });
          break;
      }
    }
  } catch (error) {
    contentEl.empty();
    contentEl.createDiv({
      cls: 'error',
      text: `Connection error: ${error instanceof Error ? error.message : 'Unknown'}`,
    });
  } finally {
    this.inputEl.disabled = false;
    this.inputEl.focus();
  }
}
```

## Thread Management

Generate and manage thread IDs:

```typescript
import { v4 as uuidv4 } from 'uuid';

class ChatView extends ItemView {
  private threadId: string = uuidv4();

  newThread(): void {
    this.threadId = uuidv4();
    this.messagesContainer.empty();
  }

  async saveThread(): Promise<void> {
    // Persist thread ID in settings
    await this.plugin.saveData({
      ...this.plugin.settings,
      lastThreadId: this.threadId,
    });
  }
}
```

**Note:** LangGraph may auto-create threads on first message via `/threads/{id}/runs/stream` endpoint.

## Creating Threads Explicitly

If server requires explicit thread creation:

```typescript
async createThread(): Promise<string> {
  const response = await fetch(
    `${this.settings.serverUrl}/threads`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to create thread: ${response.statusText}`);
  }

  const data = await response.json();
  return data.thread_id;
}
```

## Error Handling

Handle connection and parsing errors:

```typescript
async function* streamLangGraph(...): AsyncGenerator<StreamEvent> {
  let response: Response;

  try {
    response = await fetch(url, { ... });
  } catch (error) {
    yield {
      type: 'error',
      content: `Connection failed: ${error instanceof Error ? error.message : 'Unknown'}`,
    };
    return;
  }

  if (!response.ok) {
    const text = await response.text();
    yield {
      type: 'error',
      content: `Server error ${response.status}: ${text}`,
    };
    return;
  }

  // ... streaming logic
}
```

## Timeout Handling

Add timeout for long-running streams:

```typescript
async function* streamLangGraph(...): AsyncGenerator<StreamEvent> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000);  // 60s timeout

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({...}),
      signal: controller.signal,
    });

    // ... streaming logic
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      yield { type: 'error', content: 'Request timed out' };
    } else {
      yield { type: 'error', content: error.message };
    }
  } finally {
    clearTimeout(timeout);
  }
}
```

## Authentication

Add authentication headers when needed:

```typescript
const response = await fetch(url, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${this.plugin.settings.apiKey}`,
  },
  body: JSON.stringify({...}),
});
```

## Streaming Performance

Optimize for smooth rendering:

```typescript
private async handleStream(
  stream: AsyncGenerator<StreamEvent>
): Promise<void> {
  let fullText = '';
  let pendingUpdate = '';
  let updateTimer: NodeJS.Timeout | null = null;

  const flushUpdate = () => {
    if (pendingUpdate) {
      fullText += pendingUpdate;
      this.contentEl.setText(fullText);
      pendingUpdate = '';
      this.scrollToBottom();
    }
  };

  for await (const event of stream) {
    if (event.type === 'token') {
      pendingUpdate += event.content ?? '';

      // Batch updates for performance
      if (!updateTimer) {
        updateTimer = setTimeout(() => {
          flushUpdate();
          updateTimer = null;
        }, 50);  // 50ms batching
      }
    }
  }

  // Flush any remaining
  if (updateTimer) clearTimeout(updateTimer);
  flushUpdate();
}
```

## Message History

Include conversation history in requests:

```typescript
interface Message {
  role: 'user' | 'assistant';
  content: string;
}

class ChatView extends ItemView {
  private messages: Message[] = [];

  private async sendMessage(text: string): Promise<void> {
    // Add to history
    this.messages.push({ role: 'user', content: text });

    // Stream with full history
    const stream = streamLangGraph(
      this.serverUrl,
      this.threadId,
      'agent',
      this.messages,  // Full history
      config
    );

    let assistantMessage = '';

    for await (const event of stream) {
      if (event.type === 'token') {
        assistantMessage += event.content ?? '';
      }
    }

    // Add assistant response to history
    this.messages.push({ role: 'assistant', content: assistantMessage });
  }
}
```

## Additional Resources

### Examples

Working examples in `examples/`:
- **`complete-sse-client.ts`** - Full SSE streaming implementation
- **`chat-integration.ts`** - Integration with chat UI

### Reference Files

For detailed information:
- **`references/langgraph-api.md`** - LangGraph API reference
- **`references/sse-format.md`** - SSE protocol details

### Official Resources

- [LangGraph API Documentation](https://docs.langchain.com/langgraph)
- [SSE Format Discussion](https://github.com/langchain-ai/langgraph/discussions)

## Next Steps

After implementing SSE client:
1. Integrate with chat UI using `obsidian-chat-ui` skill
2. Connect to MCP tools with `obsidian-mcp-server` skill
3. Test end-to-end streaming workflow
