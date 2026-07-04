# mcp primitives — neutral connection specs

Each `<name>.json` here is a **neutral MCP connection spec** — *how to reach a server*, never the
server's code. The translation service (`scripts/translate.py`) renders each spec into every
target's own MCP config schema; the source code lives in its own repo / installed binary and is
referenced by `command`, not vendored.

## Schema

```jsonc
{
  "name": "example-server",            // server key (matches the roster id)
  "description": "one-line summary",   // surfaced in generated fragments
  "transport": "stdio",                // "stdio" (local process) | "http" (remote URL)

  // transport: stdio
  "command": "example-server",         // bare command — resolved on PATH (portable; no machine paths)
  "args": ["serve"],
  "env": {},                           // secrets as "${VAR}" placeholders ONLY — never literal tokens
  "install": {                         // REQUIRED for stdio (issue #79): where the binary comes from
    "upstream": "https://github.com/<owner>/<repo>",
    "command": "uv tool install example-server"   // or brew/npm/cargo — one runnable install step
  },

  // transport: http
  "url": "https://…/mcp",
  "headers": {}                        // "${VAR}" placeholders for auth
}
```

A stdio spec with no `install:` block fails `validate_primitives.py` (`make ci`) — a bare
PATH command otherwise silently assumes the binary is already on the machine. The roster
entry additionally declares the binary via `requires: [cli:<command>]` so deploy tooling
(dotfiles-bootstrap) can check or provision it. Externals specs are exempt: their
provenance lives in `externals.yaml`.

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
