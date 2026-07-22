# opencode configuration reference

_Verification: ✅ = checked against https://opencode.ai/docs 2026-07-02. Unmarked = from
gathered notes (2026-05/06 era, partly from a private fork) — re-verify before relying._

## Config file precedence (low → high)

1. `https://org/.well-known/opencode` — remote org defaults
2. `~/.config/opencode/opencode.json{,c}` — global user config ✅
3. `$OPENCODE_CONFIG` env var file
4. `./opencode.json{,c}` — project root ✅
5. `./.opencode/opencode.json{,c}` — project .opencode dir ✅
6. `$OPENCODE_CONFIG_CONTENT` env var (inline JSON)
7. `/etc/opencode/opencode.json{,c}` — managed/enterprise (macOS: `/Library/Application Support/opencode`)

**Merge semantics ✅:** arrays (`plugin`, `instructions`) are **concatenated** across levels;
objects are **deep-merged**; project overrides global. This is what makes distributed config
fragments composable.

Prefer `.jsonc` — comments allowed. Validate against `"$schema": "https://opencode.ai/config.json"`.

## Key config fields

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "model": "anthropic/claude-sonnet-4-5",   // {provider}/{model} — prefix REQUIRED
  "default_agent": "build",
  "theme": "opencode",
  "autoupdate": true,

  "provider": {                              // API keys / custom endpoints
    "anthropic": { "apiKey": "{env:ANTHROPIC_API_KEY}" },
    "custom-openai": { "baseURL": "https://proxy.example.com/v1" }
  },

  "agent": {                                 // agents inline (alt to agents/*.md)
    "researcher": {
      "description": "Deep research agent",
      "mode": "subagent",
      "model": "anthropic/claude-opus-4-6",
      "prompt": "You are...",
      "permission": { "bash": "deny", "write": "deny" }
    }
  },

  "permission": {                            // allow | ask | deny, glob patterns
    "bash": "ask",
    "write": "allow",
    "read": { "*": "allow", "*.env": "ask", "secrets/*": "deny" },
    "skill": { "my-skill": "allow", "*": "ask" }
  },

  "mcp": {
    "local-server":  { "type": "local",  "command": ["npx", "-y", "some-server"], "environment": { "KEY": "${VAR}" } },
    "remote-server": { "type": "remote", "url": "https://mcp.example.com", "headers": { "Authorization": "Bearer ${TOKEN}" } }
  },

  "plugin": ["some-npm-plugin@1.0.0"],       // npm plugins; local files auto-load from plugins/ dirs ✅
  "instructions": ["docs/guidelines.md", ".cursor/rules/*.md"],  // paths, globs, URLs ✅
  "command": { },                            // commands inline (alt to commands/*.md) ✅

  "compaction": { "auto": true, "prune": true },
  "experimental": { "batch_tool": false, "mcp_timeout": 60000 }
}
```

## Rules / instructions ✅

Read order: project `AGENTS.md` (walking up from cwd; `CLAUDE.md` as claude-code fallback) →
global `~/.config/opencode/AGENTS.md` → `~/.claude/CLAUDE.md` fallback. All `instructions`
entries are combined with AGENTS.md content. Disable claude-code fallbacks:
`OPENCODE_DISABLE_CLAUDE_CODE=1`.

## Model selection priority (low → high)

`config.model` → `agent.model` → session variant → mid-session `@model` switch.

## Storage paths (XDG)

| Path | Contents |
|---|---|
| `~/.local/share/opencode/` | SQLite DB, auth.json, mcp-auth.json (0600), snapshots, worktrees, LSP binaries |
| `~/.config/opencode/` | config, agents/, skills/, tools/, plugins/, commands/, AGENTS.md ✅ |
| `~/.cache/opencode/` | models cache, Bun packages — safe to delete |
| `~/.local/state/opencode/` | runtime state |

## Feature flags (env vars; from notes — verify before use)

| Flag | Effect |
|---|---|
| `OPENCODE_EXPERIMENTAL=1` | master switch: plan mode, Exa, LSP tool |
| `OPENCODE_ENABLE_EXA=1` | websearch + codesearch tools (no API key) |
| `OPENCODE_ENABLE_QUESTION_TOOL=1` | question tool in API/ACP clients |
| `OPENCODE_DISABLE_AUTOCOMPACT=1` / `OPENCODE_DISABLE_PRUNE=1` | context management off-switches |
| `OPENCODE_DISABLE_PROJECT_CONFIG=1` | skip project-level config |
| `OPENCODE_DISABLE_EXTERNAL_SKILLS=1` | skip `.claude/` + `.agents/` skill dirs |
| `OPENCODE_DISABLE_CLAUDE_CODE=1` | skip claude-code skills AND rules fallbacks |
| `OPENCODE_PERMISSION='{"bash":"allow"}'` | JSON permission override (highest priority) |
| `OPENCODE_CONFIG` / `OPENCODE_CONFIG_CONTENT` | config path / inline config |

## Sessions, compaction, worktrees (from notes)

- Auto-compaction when `tokens.total >= model_context - reserved`; reserved = `min(20k, maxOutputTokens)`.
- Pruning drops old tool outputs, keeps the calls; **skill outputs are never pruned**.
- Git worktrees per feature via the UI "Enable Workspaces"; data in `~/.local/share/opencode/worktrees/`.
- Snapshots = git trees (not commits) powering revert/undo.
- ACP: `opencode acp` exposes session events over stdio JSON-RPC.

## Fork-specific notes (a private opencode fork — NOT upstream)

- Docker: nginx on port 4097 fronting SolidJS SPA + Hono API; state in named volumes
  (`opencode-data`, `opencode-config`, `opencode-cache`, `opencode-state`).
- Set `OPENCODE_DISABLE_AUTOUPDATE=1` in containers.
