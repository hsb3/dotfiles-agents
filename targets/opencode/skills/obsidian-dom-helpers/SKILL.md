---
name: obsidian-dom-helpers
description: This skill should be used when the user asks about "DOM manipulation", "create elements", "innerHTML", "safe rendering", "MarkdownRenderer", or mentions creating UI elements in Obsidian plugins. Critical for passing community plugin review.
---

# Obsidian DOM Helpers

Provides guidance on safe DOM manipulation in Obsidian plugins using the platform's built-in helpers. Following these patterns is **critical for passing community plugin review**.

## Critical Rule: Never Use innerHTML

**The #1 community review violation**: Never use `innerHTML`, `outerHTML`, or similar methods.

```typescript
// ❌ WRONG - Will fail review
el.innerHTML = '<div class="message">Hello</div>';

// ✅ CORRECT - Use Obsidian helpers
const msgEl = el.createDiv({ cls: 'message', text: 'Hello' });
```

**Why this matters:**
- Obsidian's automated review bot **auto-rejects** plugins using innerHTML
- Security risk: enables XSS attacks
- No exceptions: innerHTML is banned in all contexts

## Obsidian's createEl API

Obsidian extends HTMLElement with helper methods for safe element creation:

### Basic Element Creation

```typescript
// Create any element type
const header = container.createEl('h3', { text: 'Title' });
const paragraph = container.createEl('p', { text: 'Content' });
const button = container.createEl('button', { text: 'Click me' });

// Specialized helpers for common elements
const div = container.createDiv({ cls: 'wrapper' });
const span = container.createSpan({ text: 'Label' });
```

### Element Options

The second parameter accepts configuration:

```typescript
container.createEl('div', {
  cls: 'my-class',              // Single class
  text: 'Content',              // Text content (safe)
  attr: {                       // HTML attributes
    'data-id': '123',
    'aria-label': 'Description'
  }
});

// Multiple classes
container.createEl('div', {
  cls: ['class1', 'class2', 'class3']
});
```

### Callback Pattern

Create nested elements with callbacks:

```typescript
container.createDiv({ cls: 'wrapper' }, (wrapper) => {
  wrapper.createEl('h3', { text: 'Title' });
  wrapper.createEl('p', { text: 'Description' });

  wrapper.createDiv({ cls: 'buttons' }, (btnContainer) => {
    btnContainer.createEl('button', { text: 'OK' });
    btnContainer.createEl('button', { text: 'Cancel' });
  });
});
```

**Callback benefits:**
- Clean nesting without temporary variables
- Readable structure matching HTML hierarchy
- Scoped element references

## Setting Text Content

Multiple safe ways to set text:

```typescript
// 1. Via createEl options
const el = container.createDiv({ text: 'Hello' });

// 2. setText method
el.setText('Updated text');

// 3. textContent property
el.textContent = 'Direct text';

// 4. appendText method (for appending)
el.appendText(' more text');
```

**All are safe** - they escape HTML automatically.

## Clearing Elements

Remove all children safely:

```typescript
// Clear all children
container.empty();

// Then rebuild
container.createDiv({ text: 'New content' });
```

**Pattern:** Always use `empty()` before rebuilding dynamic content.

## Adding/Removing Classes

Manage CSS classes safely:

```typescript
// Add classes
element.addClass('active');
element.addClass('selected', 'highlighted');

// Remove classes
element.removeClass('active');
element.removeClass('selected', 'highlighted');

// Toggle class
element.toggleClass('hidden', shouldHide);
```

## Markdown Rendering

For rendering markdown content (assistant responses, notes, etc.), use MarkdownRenderer:

```typescript
import { MarkdownRenderer } from 'obsidian';

// Render markdown safely
await MarkdownRenderer.render(
  this.app,                    // App instance
  markdownContent,             // Markdown string
  container,                   // Target element
  '',                          // Source path (for wikilink resolution)
  this                         // Component for lifecycle management
);
```

**Use cases:**
- Rendering agent responses with markdown formatting
- Displaying note content in custom views
- Preview panels and tooltips

**Critical:** MarkdownRenderer is the **only** safe way to render markdown. Never parse markdown manually with innerHTML.

## Common UI Patterns

### Message List (Chat)

Build a message list without innerHTML:

```typescript
function addMessage(
  container: HTMLElement,
  role: 'user' | 'assistant',
  content: string
): HTMLElement {
  const msgEl = container.createDiv({
    cls: `message message-${role}`
  });

  msgEl.createDiv({
    cls: 'message-label',
    text: role === 'user' ? 'You' : 'Assistant'
  });

  const contentEl = msgEl.createDiv({ cls: 'message-content' });

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
    // Plain text for user messages
    contentEl.setText(content);
  }

  return contentEl;
}
```

### Form Inputs

Create form elements safely:

```typescript
const form = container.createDiv({ cls: 'form' });

// Text input
const input = form.createEl('input', {
  attr: {
    type: 'text',
    placeholder: 'Enter value...'
  }
});

// Textarea
const textarea = form.createEl('textarea', {
  attr: {
    rows: '5',
    placeholder: 'Enter text...'
  }
});

// Checkbox
const checkbox = form.createEl('input', {
  attr: { type: 'checkbox', id: 'my-checkbox' }
});
const label = form.createEl('label', {
  text: 'Enable feature',
  attr: { for: 'my-checkbox' }
});
```

### Collapsible Sections

Create expandable sections:

```typescript
function createCollapsible(
  container: HTMLElement,
  title: string,
  content: string
): void {
  const wrapper = container.createDiv({ cls: 'collapsible' });

  const header = wrapper.createDiv({ cls: 'collapsible-header' });
  header.createEl('span', { text: title });

  const toggle = header.createEl('span', {
    text: '▶',
    cls: 'toggle-icon'
  });

  const details = wrapper.createDiv({ cls: 'collapsible-details' });
  details.style.display = 'none';
  details.setText(content);

  header.addEventListener('click', () => {
    const isHidden = details.style.display === 'none';
    details.style.display = isHidden ? 'block' : 'none';
    toggle.setText(isHidden ? '▼' : '▶');
  });
}
```

## Streaming Text Updates

For streaming responses (chat, SSE), append text safely:

```typescript
class StreamingMessage {
  private container: HTMLElement;
  private fullText: string = '';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  appendToken(token: string): void {
    this.fullText += token;
    // Update with plain text during streaming
    this.container.setText(this.fullText);
  }

  async finalize(app: App, component: Component): Promise<void> {
    // Replace with rendered markdown when complete
    this.container.empty();
    await MarkdownRenderer.render(
      app,
      this.fullText,
      this.container,
      '',
      component
    );
  }
}
```

**Pattern:**
1. During streaming: Use `setText()` for plain text
2. After complete: Use `MarkdownRenderer` for formatted output
3. Never build HTML strings manually

## Event Listeners

Add events to created elements:

```typescript
const button = container.createEl('button', { text: 'Submit' });

button.addEventListener('click', () => {
  void this.handleSubmit();
});

// With type safety
button.addEventListener('click', (e: MouseEvent) => {
  e.preventDefault();
  void this.handleClick(e);
});
```

**Event cleanup:** Obsidian handles cleanup automatically for elements created with createEl.

## Setting Styles

Apply inline styles when needed:

```typescript
const element = container.createDiv({ cls: 'box' });

// Individual styles
element.style.display = 'flex';
element.style.backgroundColor = '#f0f0f0';

// Multiple styles
Object.assign(element.style, {
  display: 'flex',
  flexDirection: 'column',
  padding: '10px',
});
```

**Prefer CSS classes** over inline styles when possible.

## Review Checklist

Before submitting plugin for review:

- [ ] No `innerHTML`, `outerHTML`, or `insertAdjacentHTML`
- [ ] All elements created with `createEl()`, `createDiv()`, or `createSpan()`
- [ ] Text set with `setText()`, `textContent`, or element options
- [ ] Markdown rendered with `MarkdownRenderer.render()`
- [ ] No HTML string concatenation
- [ ] Event listeners use `addEventListener()`

## Common Mistakes

### Mistake 1: Building HTML Strings

```typescript
// ❌ WRONG
let html = '<div class="message">';
html += '<span>' + text + '</span>';
html += '</div>';
el.innerHTML = html;

// ✅ CORRECT
const msgDiv = el.createDiv({ cls: 'message' });
msgDiv.createEl('span', { text: text });
```

### Mistake 2: Unsafe Text Insertion

```typescript
// ❌ WRONG
el.innerHTML = userInput;  // XSS risk!

// ✅ CORRECT
el.setText(userInput);  // Escaped automatically
```

### Mistake 3: Manual Markdown Parsing

```typescript
// ❌ WRONG
const html = marked.parse(markdown);
el.innerHTML = html;

// ✅ CORRECT
await MarkdownRenderer.render(this.app, markdown, el, '', this);
```

## Additional Resources

### Examples

Working examples in `examples/`:
- **`safe-dom-patterns.ts`** - Complete safe DOM patterns
- **`streaming-message.ts`** - Safe streaming text implementation

### Official Resources

- [Obsidian Sample Plugin](https://github.com/obsidianmd/obsidian-sample-plugin)
- [Community Plugin Review Guidelines](https://docs.obsidian.md/Plugins/Releasing/Submit+your+plugin)

## Next Steps

After mastering safe DOM manipulation:
1. Review community requirements with `obsidian-best-practices` skill
2. Build chat interfaces with `obsidian-chat-ui` skill
3. Understand plugin lifecycle with `obsidian-api-basics` skill
