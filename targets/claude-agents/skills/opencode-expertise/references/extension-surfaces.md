# opencode extension surfaces — minimal working examples

_✅ = verified against https://opencode.ai/docs 2026-07-02. **Current docs use PLURAL
directory names** (`agents/`, `skills/`, `tools/`, `plugins/`, `commands/`); singular forms
in older guides are stale._

## 1. Agents ✅ — declarative (markdown)

`.opencode/agents/{name}.md` (project) · `~/.config/opencode/agents/{name}.md` (global)

```markdown
---
description: "Code reviewer — reads code, suggests improvements, never edits"  # required
mode: subagent          # primary | subagent | all (default: all)
model: anthropic/claude-opus-4-6   # {provider}/{model} prefix required
temperature: 0.3
top_p: 0.9
hidden: false           # hide from @ picker (subagents)
steps: 50               # max agentic iterations
color: "#FF5733"
permission:
  bash: deny
  write: deny
  read: { "*": "allow", "*.env": "ask" }
---
System prompt body. Supports @file-refs and !`shell` injection (from notes).
```

Built-ins ✅: `build`, `plan` (primary); `general`, `explore`, `scout` (subagents);
`compaction`, `title`, `summary` (hidden system).

## 2. Skills ✅ — declarative (SKILL.md)

Discovery (project): `.opencode/skills/<name>/`, `.claude/skills/<name>/`, `.agents/skills/<name>/`
Discovery (global): `~/.config/opencode/skills/`, `~/.claude/skills/`, `~/.agents/skills/`
Walks up from cwd to the git worktree root.

```markdown
---
name: my-skill          # required; ^[a-z0-9]+(-[a-z0-9]+)*$, 1–64 chars, == dir name
description: "What it does and when to use it"   # required, 1–1024 chars
license: MIT            # optional
compatibility: opencode # optional
metadata: { category: "dev" }   # optional string map; unknown fields ignored
---
Content injected when the agent calls the `skill` tool.
```

Permission: `"permission": { "skill": { "my-skill": "allow", "internal-*": "deny", "*": "ask" } }`.
CC `allowed-tools` frontmatter is not in the OC schema (ignored — unknown fields are ignored ✅).

## 3. Commands ✅ — declarative (markdown)

`.opencode/commands/{name}.md` · `~/.config/opencode/commands/` (or `command` config block)

```markdown
---
description: Run the test suite and summarize failures
agent: build
model: anthropic/claude-sonnet-4-5
---
Run tests for $ARGUMENTS. Context: !`git status`. Spec: @docs/testing.md
```

Template vars ✅: `$ARGUMENTS`, `$1..$n`, `` !`cmd` `` (shell inject), `@file` (content include).
No `.claude/commands` compatibility ✅ — irrelevant for dotfiles-agents (skills-over-commands).

## 4. MCP servers ✅ — declarative (config)

```jsonc
"mcp": {
  "fs":  { "type": "local",  "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
           "environment": { "API_KEY": "${MY_KEY}" }, "timeout": 30000 },
  "api": { "type": "remote", "url": "https://mcp.example.com",
           "headers": { "Authorization": "Bearer ${TOKEN}" },
           "oauth": { "clientId": "abc", "scope": "read write" } }
}
```

MCP tools appear namespaced `{server}_{tool}`. OAuth tokens → `~/.local/share/opencode/mcp-auth.json`.

## 5. Custom tools ✅ — **TypeScript required**

`.opencode/tools/{name}.ts` · `~/.config/opencode/tools/{name}.ts`
Filename → tool name; multiple exports → `{file}_{export}`; custom tools override built-ins ✅.

```typescript
import { tool } from "@opencode-ai/plugin"
import { $ } from "bun"

export default tool({
  description: "Initialize a new pipeline",
  args: { source: tool.schema.string().describe("Source name") },   // Zod
  async execute(args) {
    return await $`my-cli init ${args.source}`.text()
  },
})
```

The TS layer can shell out to any language — the *interface* must be TS, the work needn't be.

## 6. Plugins ✅ — **TypeScript required; the only hook mechanism**

`.opencode/plugins/*.{ts,js}` · `~/.config/opencode/plugins/` · npm via config `plugin: []`.
Auto-loaded at startup.

```typescript
import type { Plugin } from "@opencode-ai/plugin"

export const MyPlugin: Plugin = async ({ project, client, $ }) => ({
  "tool.execute.before": async (input, output) => {
    if (input.tool === "bash") { /* validate / block / log */ }
  },
  "tool.execute.after": async (input, output) => { /* post-processing */ },
  "session.created": async () => { await $`./scripts/session-start.sh` },  // wrap a shell hook
})
```

Hook events ✅ (by family): `tool.execute.before/after` · `session.created/compacted/deleted/
diff/error/idle/status/updated` · `message.updated/removed`, `message.part.updated/removed` ·
`permission.asked/replied` · `file.edited`, `file.watcher.updated` · `command.executed` ·
`lsp.client.diagnostics`, `lsp.updated` · `server.connected` · `installation.updated` ·
`shell.env` · `tui.prompt.append`, `tui.command.execute`, `tui.toast.show`.

Plugins can also add tools (`tool` helper), hook auth, and mutate config.

## 7. Providers / themes / keybinds — declarative (config)

Providers: `{provider}/{model}` ids; bundled majors + any OpenAI-compatible `baseURL`.
Themes/keybinds: config fields (TUI). Low relevance for distribution.
