# obsidian-mcp-server

Patterns for hosting an MCP (Model Context Protocol) server inside an Obsidian plugin over
Streamable HTTP, so external AI agents can call vault operations as tools. Covers SDK setup,
a stateless per-request server, tool registration (read/search/query vault notes), plugin
lifecycle integration, port fallback, and the localhost-only binding and input validation
needed to keep it safe. Use it to expose a plugin's vault as agent-callable tools instead of
building a bespoke integration.

## When it triggers

Use it when asked to add an MCP server, work with the Model Context Protocol, expose vault
tools over Streamable HTTP, register MCP tools, or otherwise integrate an MCP server into an
Obsidian plugin.

## Install

```
claude plugin install obsidian-toolkit@dotfiles-agents
```

Ships in the obsidian-toolkit bundle (not standalone). Pair with `obsidian-chat-ui` to
surface the agent's tool calls in the sidebar.
