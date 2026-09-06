# obsidian-chat-ui

Patterns for building chat and copilot-style panels in Obsidian plugins on top of
`ItemView`: sidebar registration, message rendering with markdown, token-by-token
streaming, tool-call indicators, loading states, and multi-thread management. Use it to get
a working chat sidebar — not a bare textarea — without hand-rolling the streaming and
scroll-management plumbing yourself.

## When it triggers

Use it when asked to create a chat interface, build a sidebar panel, work with `ItemView`,
stream messages token by token, build a chat or copilot UI, or otherwise build a
conversational interface inside an Obsidian plugin.

## Install

```
claude plugin install obsidian-toolkit@dotfiles-agents
claude plugin install solo-skills@dotfiles-agents
```

Ships in the `obsidian-toolkit` and `solo-skills` bundles. Pair with `obsidian-mcp-server` to
give the chat panel vault-backed tools.
