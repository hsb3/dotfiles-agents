# opencode extension surfaces — minimal working examples

_✅ = verified against https://opencode.ai/docs and `@opencode-ai/plugin` 1.18.29 typings on
2026-09-06. **Current docs use PLURAL directory names** (`agents/`, `skills/`, `tools/`,
`plugins/`, `commands/`); singular forms remain supported for backwards compatibility ✅._

## 1. Agents ✅ — declarative (markdown)

`.opencode/agents/{name}.md` (project) · `~/.config/opencode/agents/{name}.md` (global)

```markdown
---
description: "Code reviewer — reads code, suggests improvements, never edits"  # required
mode: subagent          # primary | subagent | all (default: all)
model: anthropic/claude-opus-4-6   # {provider}/{model} prefix required; subagents default to the caller's model
temperature: 0.3
top_p: 0.9
hidden: false           # hide from @ picker (subagents)
steps: 50               # max agentic iterations
color: "#FF5733"         # hex or theme color (primary, accent, ...)
disable: false          # true removes the agent
permission:             # `tools:` map is deprecated in favour of this
  bash: deny
  write: deny
  read: { "*": "allow", "*.env": "ask" }
---
System prompt body. (@file-refs and !`shell` injection in agent bodies: from notes, unverified —
the docs only show `prompt: "{file:...}"` substitution.)
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

Frontmatter ✅: `description`, `agent`, `model`, `subtask` (force a subagent run).
Template vars ✅: `$ARGUMENTS`, `$1..$n`, `` !`cmd` `` (shell inject), `@file` (content include).
No `.claude/commands` compatibility is documented ✅ (absence in docs, not a tested negative) —
irrelevant for a skills-only marketplace (skills-over-commands).

## 4. MCP servers ✅ — declarative (config)

```jsonc
"mcp": {
  "fs":  { "type": "local",  "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
           "environment": { "API_KEY": "{env:MY_KEY}" }, "cwd": ".", "timeout": 30000 },
  "api": { "type": "remote", "url": "https://mcp.example.com",
           "headers": { "Authorization": "Bearer {env:TOKEN}" },
           "oauth": { "clientId": "{env:ID}", "clientSecret": "{env:SECRET}", "scope": "read write" } }
}
```

Env substitution is `{env:VAR}` ✅ (not `${VAR}`); `timeout` defaults to 5000 ms ✅. MCP tools
appear namespaced `{server}_{tool}` ✅. OAuth tokens → `~/.local/share/opencode/mcp-auth.json` ✅.

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

export const MyPlugin: Plugin = async ({ project, client, $, directory, worktree }) => ({
  "tool.execute.before": async (input, output) => {
    if (input.tool === "bash") { /* inspect/mutate output.args, or throw to block */ }
  },
  "tool.execute.after": async (input, output) => { /* post-processing */ },
  event: async ({ event }) => {                       // ONE hook for every SDK event
    if (event.type === "session.created") { await $`./scripts/session-start.sh` }
  },
})
```

**Two different name sets — do not mix them.** A plugin returns an object whose keys are
`Hooks` interface members; SDK *event type strings* are only ever seen inside the `event`
member. A key like `"session.created": async () => {}` at the top level is silently ignored.

`Hooks` members ✅ (from `@opencode-ai/plugin` 1.18.29 `index.d.ts`): `event` · `config` ·
`tool` (map of `tool()` definitions) · `auth` · `provider` · `chat.message` (a new user message
arrived) · `chat.params` · `chat.headers` · `permission.ask` · `command.execute.before` ·
`tool.execute.before` · `tool.execute.after` · `tool.definition` · `shell.env` · `dispose` ·
experimental: `experimental.chat.messages.transform`, `experimental.chat.system.transform`,
`experimental.provider.small_model`, `experimental.session.compacting` (fires *before*
compaction), `experimental.compaction.autocontinue`, `experimental.text.complete`.

SDK `Event` union values ✅ (from `@opencode-ai/sdk` 1.18.29 typings; what `event.type` can be):
`session.created/updated/deleted/idle/status/error/diff/compacted` · `message.updated/removed`,
`message.part.updated/removed` · `permission.updated/replied` (the docs page also lists
`permission.asked`, which is absent from the typings) · `file.edited`, `file.watcher.updated` ·
`command.executed` · `lsp.client.diagnostics`, `lsp.updated` · `server.connected`,
`server.instance.disposed` · `installation.updated`, `installation.update-available` ·
`todo.updated` · `vcs.branch.updated` · `pty.created/updated/exited/deleted` ·
`tui.prompt.append`, `tui.command.execute`, `tui.toast.show`.

Plugin context ✅: `{ project, client, $, directory, worktree, serverUrl, experimental_workspace }`.
Plugins can also add tools (`tool` member), hook auth/providers, and mutate config ✅. Load
order ✅: global config `plugin` → project config `plugin` → `~/.config/opencode/plugins/` →
`.opencode/plugins/`; npm plugins are installed by Bun into `~/.cache/opencode/node_modules/`.

## 7. Providers / themes / keybinds — declarative (config)

Providers: `{provider}/{model}` ids; bundled majors + any OpenAI-compatible `baseURL`.
Themes/keybinds: config fields (TUI). Low relevance for distribution.
