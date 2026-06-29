/**
 * Complete SSE Client for LangGraph
 *
 * A standalone async generator that streams tokens from a LangGraph API
 * using fetch + manual SSE parsing (EventSource cannot do POST).
 *
 * Usage:
 *   for await (const event of streamLangGraph(url, threadId, 'agent', messages)) {
 *     if (event.type === 'token') process(event.content);
 *   }
 */

// ── Types ──────────────────────────────────────────────────────────────

export interface StreamEvent {
  type: 'token' | 'tool_call' | 'tool_result' | 'end' | 'error';
  content?: string;
  toolName?: string;
  toolArgs?: Record<string, unknown>;
}

export interface StreamOptions {
  /** AbortSignal for cancellation */
  signal?: AbortSignal;
  /** Timeout in milliseconds (default: 60000) */
  timeout?: number;
  /** Authorization bearer token */
  apiKey?: string;
}

// ── Core Streaming Function ────────────────────────────────────────────

export async function* streamLangGraph(
  serverUrl: string,
  threadId: string,
  assistantId: string,
  messages: Array<{ role: string; content: string }>,
  config?: Record<string, unknown>,
  options?: StreamOptions,
): AsyncGenerator<StreamEvent> {
  const url = `${serverUrl}/threads/${threadId}/runs/stream`;
  const controller = new AbortController();
  const timeoutMs = options?.timeout ?? 60000;
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  // Link external signal to our controller
  if (options?.signal) {
    options.signal.addEventListener('abort', () => controller.abort());
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (options?.apiKey) {
    headers['Authorization'] = `Bearer ${options.apiKey}`;
  }

  let response: Response;

  try {
    response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        assistant_id: assistantId,
        input: { messages },
        config: {
          configurable: { thread_id: threadId, ...config },
        },
        stream_mode: ['messages-tuple'],
      }),
      signal: controller.signal,
    });
  } catch (error) {
    clearTimeout(timer);
    if (error instanceof Error && error.name === 'AbortError') {
      yield { type: 'error', content: 'Request timed out or was cancelled' };
    } else {
      yield {
        type: 'error',
        content: `Connection failed: ${error instanceof Error ? error.message : 'Unknown'}`,
      };
    }
    return;
  }

  if (!response.ok) {
    clearTimeout(timer);
    const text = await response.text().catch(() => '');
    yield { type: 'error', content: `Server error ${response.status}: ${text}` };
    return;
  }

  if (!response.body) {
    clearTimeout(timer);
    yield { type: 'error', content: 'Response body is null' };
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE events are separated by double newlines
      const parts = buffer.split('\n\n');
      buffer = parts.pop() ?? '';

      for (const part of parts) {
        const event = parseSSEPart(part);
        if (event) yield event;
      }
    }

    // Process any remaining buffer
    if (buffer.trim()) {
      const event = parseSSEPart(buffer);
      if (event) yield event;
    }
  } finally {
    clearTimeout(timer);
    reader.releaseLock();
  }
}

// ── SSE Parsing ────────────────────────────────────────────────────────

function parseSSEPart(part: string): StreamEvent | null {
  if (!part.trim()) return null;

  let eventType = '';
  let eventData = '';

  for (const line of part.split('\n')) {
    if (line.startsWith('event: ')) {
      eventType = line.slice(7).trim();
    } else if (line.startsWith('data: ')) {
      eventData = line.slice(6);
    }
  }

  if (!eventType || !eventData) return null;

  if (eventType === 'messages') {
    return parseMessageEvent(eventData);
  } else if (eventType === 'end') {
    return { type: 'end' };
  } else if (eventType === 'error') {
    return { type: 'error', content: eventData };
  }

  return null;
}

function parseMessageEvent(data: string): StreamEvent | null {
  try {
    const [chunk, _metadata] = JSON.parse(data);

    // AI text token
    if (chunk.type === 'AIMessageChunk' && chunk.content) {
      return { type: 'token', content: chunk.content };
    }

    // Tool call initiation
    if (chunk.type === 'AIMessageChunk' && chunk.tool_calls?.length > 0) {
      const tc = chunk.tool_calls[0];
      if (tc.name) {
        return { type: 'tool_call', toolName: tc.name, toolArgs: tc.args };
      }
    }

    // Tool result
    if (chunk.type === 'ToolMessage') {
      return { type: 'tool_result', content: chunk.content, toolName: chunk.name };
    }
  } catch {
    console.debug('Failed to parse SSE message:', data);
  }

  return null;
}

// ── Thread Management Helpers ──────────────────────────────────────────

export async function createThread(
  serverUrl: string,
  apiKey?: string,
): Promise<string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (apiKey) {
    headers['Authorization'] = `Bearer ${apiKey}`;
  }

  const response = await fetch(`${serverUrl}/threads`, {
    method: 'POST',
    headers,
    body: JSON.stringify({}),
  });

  if (!response.ok) {
    throw new Error(`Failed to create thread: ${response.status} ${response.statusText}`);
  }

  const data = await response.json();
  return data.thread_id;
}

export function generateThreadId(): string {
  // Simple UUID v4 without external dependency
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}
