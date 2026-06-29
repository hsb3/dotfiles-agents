# mcp primitives — neutral connection specs

Each `<name>.json` here is a **neutral MCP connection spec** — *how to reach a server*, never the
server's code. The translation service (`scripts/translate.py`) renders each spec into every
target's own MCP config schema; the source code lives in its own repo / installed binary and is
referenced by `command`, not vendored.

## Schema

```jsonc
{
  "name": "agent-bus",                 // server key (matches the roster id)
  "description": "one-line summary",   // surfaced in generated fragments
  "transport": "stdio",                // "stdio" (local process) | "http" (remote URL)

  // transport: stdio
  "command": "agent-bus",              // bare command — resolved on PATH (portable; no machine paths)
  "args": ["serve"],
  "env": {},                           // secrets as "${VAR}" placeholders ONLY — never literal tokens

  // transport: http
  "url": "https://…/mcp",
  "headers": {}                        // "${VAR}" placeholders for auth
}
```

**Secrets** are never committed: use `${VAR}` placeholders resolved at deploy time from the
Keychain (`secret` / `mcp-secrets-sync`).

## How each target renders (capability matrix → `primitives-core-translation-config.yaml`)

| Target | Output | Shape |
| ------ | ------ | ----- |
| claude-code | `targets/claude-code/mcp/<name>.json` | `{ "mcpServers": { name: { type, command, args, env } } }` (merge into `.mcp.json` / `~/.claude.json`) |
| opencode | `targets/opencode/mcp/<name>.json` | `{ "mcp": { name: { type: local\|remote, command:[…], environment } } }` |
| claude-agents (CMA) | `targets/claude-agents/mcp/<name>.json` | `{ "mcp_servers": [ { type: url, url, name } ] }` — **remote-only**; a local `stdio` spec is recorded as a skip |

MCP fragments are **config, merged at deploy** — they are rendered shelf-agnostically (a `core`
vs `toggle` mcp both emit a raw fragment), unlike skills/agents which split into raw vs plugin
folders. The actual placement/merge is dotfiles-bootstrap's job.
