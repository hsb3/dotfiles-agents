# opencode configuration reference

_Verification: ✅ = checked against https://opencode.ai/docs 2026-09-06. Unmarked = from
gathered notes (2026-05/06 era, partly from a private fork) — re-verify before relying._

## Config file precedence (low → high)

1. `.well-known/opencode` on the provider host — remote org defaults ✅
2. `~/.config/opencode/opencode.json{,c}` — global user config ✅
3. `$OPENCODE_CONFIG` env var file ✅
4. `./opencode.json{,c}` — project root, found by walking up to the nearest git dir ✅
5. `.opencode/` directories — agents, commands, plugins ✅ (`$OPENCODE_CONFIG_DIR` adds another
   such directory ✅; a `.opencode/opencode.json` config *file* at this level is unverified)
6. `$OPENCODE_CONFIG_CONTENT` env var (inline JSON) ✅
7. `/etc/opencode/opencode.json{,c}` — managed (macOS: `/Library/Application Support/opencode/`,
   Windows: `%ProgramData%\opencode`) ✅, then macOS MDM `.mobileconfig` ✅

TUI-only keys (`theme`, `keybinds`, `tui`) now live in a sibling `tui.json{,c}`; the legacy keys
in `opencode.json` are deprecated and auto-migrated ✅.

**Merge semantics:** config files are merged, not replaced — later levels override only
conflicting keys and non-conflicting keys survive ✅. Whether arrays (`plugin`, `instructions`)
concatenate or replace is **unverified** (the docs do not say); a generator should assume
replace and emit complete arrays, or check-before-add.

Prefer `.jsonc` — comments allowed. Validate against `"$schema": "https://opencode.ai/config.json"`.

## Key config fields

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "model": "anthropic/claude-sonnet-4-5",   // {provider}/{model} — prefix REQUIRED ✅
  "small_model": "anthropic/claude-haiku-4-5", // lightweight tasks ✅
  "default_agent": "build",                  // must be a primary agent ✅
  "autoupdate": true,                        // or "notify" ✅ (theme moved to tui.json)

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
    "local-server":  { "type": "local",  "command": ["npx", "-y", "some-server"], "environment": { "KEY": "{env:VAR}" } },
    "remote-server": { "type": "remote", "url": "https://mcp.example.com", "headers": { "Authorization": "Bearer {env:TOKEN}" } }
  },

  "plugin": ["some-npm-plugin@1.0.0"],       // npm plugins; local files auto-load from plugins/ dirs ✅
  "instructions": ["docs/guidelines.md", ".cursor/rules/*.md"],  // paths, globs, https URLs (5 s timeout) ✅
  "command": { },                            // commands inline (alt to commands/*.md) ✅

  "compaction": { "auto": true, "prune": true, "reserved": 10000 },  // ✅
  "subagent_depth": 1,                       // ✅ 0 = no subagents
  "experimental": { }                        // exists ✅; specific sub-keys from notes are unverified
}
```

## Rules / instructions ✅

Read order: project `AGENTS.md` (walking up from cwd; `CLAUDE.md` as claude-code fallback) →
global `~/.config/opencode/AGENTS.md` → `~/.claude/CLAUDE.md` fallback. First match wins per
category. All `instructions` entries are combined with AGENTS.md content. Disable claude-code
fallbacks: `OPENCODE_DISABLE_CLAUDE_CODE=1` (all), `OPENCODE_DISABLE_CLAUDE_CODE_PROMPT=1`
(only `~/.claude/CLAUDE.md`), `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1` (only `.claude/skills`).

## Model selection priority (low → high)

`config.model` → `agent.model` → session variant → mid-session `@model` switch.

## Storage paths (XDG)

| Path | Contents |
|---|---|
| `~/.local/share/opencode/` | SQLite DB, auth.json, mcp-auth.json (0600), snapshots, worktrees, LSP binaries |
| `~/.config/opencode/` | config, agents/, skills/, tools/, plugins/, commands/, AGENTS.md ✅ |
| `~/.cache/opencode/` | models cache, Bun packages — safe to delete |
| `~/.local/state/opencode/` | runtime state |

## Feature flags (env vars; ✅ = listed on the CLI reference page)

| Flag | Effect |
|---|---|
| `OPENCODE_EXPERIMENTAL=1` ✅ | experimental umbrella flag (individual `OPENCODE_EXPERIMENTAL_PLAN_MODE`, `_EXA`, `_LSP_TOOL`, `_WORKSPACES`, … also exist ✅) |
| `OPENCODE_ENABLE_EXA=1` ✅ | Exa web search tools |
| `OPENCODE_ENABLE_QUESTION_TOOL=1` | not on the current CLI page — unverified |
| `OPENCODE_DISABLE_AUTOCOMPACT=1` / `OPENCODE_DISABLE_PRUNE=1` ✅ | context management off-switches |
| `OPENCODE_DISABLE_PROJECT_CONFIG=1` | not on the current CLI page — unverified |
| `OPENCODE_DISABLE_EXTERNAL_SKILLS=1` | not on the current CLI page — unverified; use `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1` ✅ for `.claude/skills` |
| `OPENCODE_DISABLE_CLAUDE_CODE=1` ✅ | skip all `.claude` reading (skills AND rules fallbacks) |
| `OPENCODE_DISABLE_AUTOUPDATE=1` ✅ | no update checks (containers) |
| `OPENCODE_PERMISSION='{"bash":"allow"}'` ✅ | inline JSON permission config |
| `OPENCODE_CONFIG` / `OPENCODE_CONFIG_CONTENT` / `OPENCODE_CONFIG_DIR` ✅ | config path / inline config / extra config directory |

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
