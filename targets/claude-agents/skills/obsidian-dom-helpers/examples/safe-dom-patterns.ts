/**
 * Safe DOM Patterns for Obsidian Plugins
 *
 * Demonstrates all recommended DOM manipulation patterns that pass
 * community plugin review. Never use innerHTML — use these instead.
 */

import { App, Component, ItemView, MarkdownRenderer, WorkspaceLeaf } from 'obsidian';

const VIEW_TYPE = 'safe-dom-demo';

/**
 * Example view demonstrating every safe DOM pattern from the skill guide.
 */
export class SafeDomDemoView extends ItemView {
	constructor(leaf: WorkspaceLeaf) {
		super(leaf);
	}

	getViewType(): string {
		return VIEW_TYPE;
	}

	getDisplayText(): string {
		return 'Safe DOM Patterns Demo';
	}

	async onOpen(): Promise<void> {
		const { contentEl } = this;
		contentEl.empty();
		contentEl.addClass('safe-dom-demo');

		this.renderElementCreation(contentEl);
		this.renderTextMethods(contentEl);
		this.renderCallbackNesting(contentEl);
		this.renderClassManagement(contentEl);
		await this.renderMarkdown(contentEl);
		this.renderFormInputs(contentEl);
		this.renderCollapsibleSection(contentEl);
		this.renderMessageList(contentEl);
		this.renderStreamingMessage(contentEl);
		this.renderEventListeners(contentEl);
		this.renderStylePatterns(contentEl);
	}

	// --- 1. Basic Element Creation ---

	private renderElementCreation(container: HTMLElement): void {
		const section = container.createDiv({ cls: 'demo-section' });
		section.createEl('h3', { text: 'Element Creation' });

		// createEl with tag name and options
		section.createEl('p', { text: 'A paragraph created with createEl.' });
		section.createEl('button', { text: 'A button' });

		// Shorthand helpers
		const wrapper = section.createDiv({ cls: 'wrapper' });
		wrapper.createSpan({ text: 'Span inside a div' });

		// Attributes and multiple classes
		section.createEl('div', {
			cls: ['card', 'card-primary', 'rounded'],
			text: 'Element with multiple classes and attributes',
			attr: {
				'data-id': 'demo-card',
				'aria-label': 'Demo card element',
			},
		});
	}

	// --- 2. Setting Text Content ---

	private renderTextMethods(container: HTMLElement): void {
		const section = container.createDiv({ cls: 'demo-section' });
		section.createEl('h3', { text: 'Text Methods' });

		// text option in createEl
		const el1 = section.createDiv({ text: 'Set via createEl options' });

		// setText replaces text content
		const el2 = section.createDiv();
		el2.setText('Set via setText()');

		// textContent property
		const el3 = section.createDiv();
		el3.textContent = 'Set via textContent';

		// appendText adds without replacing
		const el4 = section.createDiv({ text: 'First part' });
		el4.appendText(' — appended with appendText()');
	}

	// --- 3. Callback Nesting Pattern ---

	private renderCallbackNesting(container: HTMLElement): void {
		const section = container.createDiv({ cls: 'demo-section' });
		section.createEl('h3', { text: 'Callback Nesting' });

		// Nested creation without temporary variables
		section.createDiv({ cls: 'card' }, (card) => {
			card.createEl('h4', { text: 'Card Title' });
			card.createEl('p', { text: 'Card body text goes here.' });

			card.createDiv({ cls: 'card-actions' }, (actions) => {
				actions.createEl('button', { text: 'Confirm' });
				actions.createEl('button', { text: 'Cancel' });
			});
		});
	}

	// --- 4. Class Management ---

	private renderClassManagement(container: HTMLElement): void {
		const section = container.createDiv({ cls: 'demo-section' });
		section.createEl('h3', { text: 'Class Management' });

		const box = section.createDiv({ cls: 'box', text: 'Toggle my classes' });

		// addClass / removeClass / toggleClass
		box.addClass('highlighted');
		box.addClass('bordered', 'shadow');
		box.removeClass('shadow');
		box.toggleClass('active', true);
	}

	// --- 5. Markdown Rendering ---

	private async renderMarkdown(container: HTMLElement): Promise<void> {
		const section = container.createDiv({ cls: 'demo-section' });
		section.createEl('h3', { text: 'Markdown Rendering' });

		const markdown = [
			'**Bold text** and *italic text*.',
			'',
			'- Item one',
			'- Item two',
			'',
			'`inline code` and a [link](https://obsidian.md)',
		].join('\n');

		const target = section.createDiv({ cls: 'markdown-content' });

		await MarkdownRenderer.render(
			this.app,
			markdown,
			target,
			'',   // source path for wikilink resolution
			this  // component for lifecycle management
		);
	}

	// --- 6. Form Inputs ---

	private renderFormInputs(container: HTMLElement): void {
		const section = container.createDiv({ cls: 'demo-section' });
		section.createEl('h3', { text: 'Form Inputs' });

		const form = section.createDiv({ cls: 'form' });

		// Text input with label
		const textGroup = form.createDiv({ cls: 'form-group' });
		textGroup.createEl('label', {
			text: 'Name',
			attr: { for: 'demo-name' },
		});
		textGroup.createEl('input', {
			attr: {
				type: 'text',
				id: 'demo-name',
				placeholder: 'Enter your name...',
			},
		});

		// Textarea
		const textareaGroup = form.createDiv({ cls: 'form-group' });
		textareaGroup.createEl('label', {
			text: 'Notes',
			attr: { for: 'demo-notes' },
		});
		textareaGroup.createEl('textarea', {
			attr: {
				id: 'demo-notes',
				rows: '4',
				placeholder: 'Enter notes...',
			},
		});

		// Checkbox
		const checkGroup = form.createDiv({ cls: 'form-group' });
		checkGroup.createEl('input', {
			attr: { type: 'checkbox', id: 'demo-toggle' },
		});
		checkGroup.createEl('label', {
			text: 'Enable feature',
			attr: { for: 'demo-toggle' },
		});

		// Submit button
		form.createEl('button', {
			cls: 'mod-cta',
			text: 'Submit',
		});
	}

	// --- 7. Collapsible Section ---

	private renderCollapsibleSection(container: HTMLElement): void {
		const section = container.createDiv({ cls: 'demo-section' });
		section.createEl('h3', { text: 'Collapsible Section' });

		createCollapsible(
			section,
			'Click to expand',
			'This content is hidden by default and revealed on click.'
		);
	}

	// --- 8. Message List (Chat UI) ---

	private renderMessageList(container: HTMLElement): void {
		const section = container.createDiv({ cls: 'demo-section' });
		section.createEl('h3', { text: 'Message List' });

		const messageContainer = section.createDiv({ cls: 'message-list' });

		addMessage(messageContainer, 'user', 'What is Obsidian?', this.app, this);
		addMessage(
			messageContainer,
			'assistant',
			'**Obsidian** is a knowledge base that works on local Markdown files.',
			this.app,
			this
		);
	}

	// --- 9. Streaming Message ---

	private renderStreamingMessage(container: HTMLElement): void {
		const section = container.createDiv({ cls: 'demo-section' });
		section.createEl('h3', { text: 'Streaming Message' });

		const target = section.createDiv({ cls: 'streaming-target' });
		const stream = new StreamingMessage(target);

		// Simulate tokens arriving over time
		const tokens = ['Hello, ', 'this ', 'is a ', '**streamed** ', 'response.'];
		let i = 0;
		const interval = window.setInterval(() => {
			if (i < tokens.length) {
				stream.appendToken(tokens[i]);
				i++;
			} else {
				window.clearInterval(interval);
				void stream.finalize(this.app, this);
			}
		}, 200);
	}

	// --- 10. Event Listeners ---

	private renderEventListeners(container: HTMLElement): void {
		const section = container.createDiv({ cls: 'demo-section' });
		section.createEl('h3', { text: 'Event Listeners' });

		const status = section.createDiv({ text: 'No clicks yet.' });

		const btn = section.createEl('button', { text: 'Click me' });
		let count = 0;

		btn.addEventListener('click', (e: MouseEvent) => {
			e.preventDefault();
			count++;
			status.setText(`Clicked ${count} time(s).`);
		});

		// Keyboard event on an input
		const input = section.createEl('input', {
			attr: { type: 'text', placeholder: 'Type here...' },
		});
		const echo = section.createDiv({ cls: 'echo', text: '' });

		input.addEventListener('input', () => {
			echo.setText(`You typed: ${input.value}`);
		});
	}

	// --- 11. Inline Styles ---

	private renderStylePatterns(container: HTMLElement): void {
		const section = container.createDiv({ cls: 'demo-section' });
		section.createEl('h3', { text: 'Style Patterns' });

		// Individual style properties
		const box1 = section.createDiv({ text: 'Individual styles' });
		box1.style.padding = '8px';
		box1.style.border = '1px solid var(--background-modifier-border)';

		// Object.assign for multiple styles
		const box2 = section.createDiv({ text: 'Batch styles via Object.assign' });
		Object.assign(box2.style, {
			display: 'flex',
			alignItems: 'center',
			gap: '8px',
			padding: '8px',
			borderRadius: '4px',
			backgroundColor: 'var(--background-secondary)',
		});
	}

	async onClose(): Promise<void> {
		this.contentEl.empty();
	}
}

// --- Standalone helper functions ---

/**
 * Create a collapsible section with click-to-toggle visibility.
 */
function createCollapsible(
	container: HTMLElement,
	title: string,
	content: string
): void {
	const wrapper = container.createDiv({ cls: 'collapsible' });

	const header = wrapper.createDiv({ cls: 'collapsible-header' });
	header.createEl('span', { text: title });
	const toggle = header.createEl('span', {
		text: '\u25B6',
		cls: 'toggle-icon',
	});

	const details = wrapper.createDiv({ cls: 'collapsible-details' });
	details.style.display = 'none';
	details.setText(content);

	header.addEventListener('click', () => {
		const isHidden = details.style.display === 'none';
		details.style.display = isHidden ? 'block' : 'none';
		toggle.setText(isHidden ? '\u25BC' : '\u25B6');
	});
}

/**
 * Add a chat message to a container. Uses MarkdownRenderer for assistant
 * messages and plain setText for user messages.
 */
function addMessage(
	container: HTMLElement,
	role: 'user' | 'assistant',
	content: string,
	app: App,
	component: Component
): HTMLElement {
	const msgEl = container.createDiv({ cls: `message message-${role}` });

	msgEl.createDiv({
		cls: 'message-label',
		text: role === 'user' ? 'You' : 'Assistant',
	});

	const contentEl = msgEl.createDiv({ cls: 'message-content' });

	if (role === 'assistant') {
		void MarkdownRenderer.render(app, content, contentEl, '', component);
	} else {
		contentEl.setText(content);
	}

	return contentEl;
}

/**
 * Handles streaming text that arrives token-by-token. Uses setText during
 * streaming for safety, then replaces with rendered markdown on finalize.
 */
class StreamingMessage {
	private container: HTMLElement;
	private fullText = '';

	constructor(container: HTMLElement) {
		this.container = container;
	}

	appendToken(token: string): void {
		this.fullText += token;
		this.container.setText(this.fullText);
	}

	async finalize(app: App, component: Component): Promise<void> {
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
