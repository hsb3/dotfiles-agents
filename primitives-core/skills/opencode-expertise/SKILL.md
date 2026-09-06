---
name: opencode-expertise
description:
  Expert knowledge of opencode — every extension surface (config, agents, skills,
  commands, custom tools, plugins, MCP, rules), the TypeScript constraint, and the
  claude-code → opencode translation mapping. Use when configuring opencode, authoring
  or migrating extenders for it, designing an opencode distribution target for a Claude
  Code skill collection, or answering how any opencode surface works.
metadata:
  version: 0.2.0
  verified: 2026-09-06
---

# opencode Expertise

opencode is a self-hostable AI coding agent (Bun/TypeScript backend). It is **highly
extensible but TypeScript-restrictive**: content surfaces are declarative (markdown/JSON),
but every *programmatic* surface — plugins, custom tools, and therefore anything
hook-shaped — must be written in TypeScript/JavaScript running on Bun.

Facts marked ✅ were verified against https://opencode.ai/docs and the published
`@opencode-ai/plugin` 1.18.29 type declarations on 2026-09-06. Unmarked details come from
gathered notes and may be stale or specific to a private fork — re-verify before relying on
them. opencode moves fast; when a path 404s or a field is
rejected, check the docs before assuming a bug.

## Extension-surface map

| Surface | Project location | Global location | Format | TS required? |
|---|---|---|---|---|
| Config ✅ | `opencode.json{,c}` (root; found by walking up to the nearest git dir). `.opencode/opencode.json{,c}` as a config *file* is unverified — the docs list `.opencode/` as a directory level for agents/commands/plugins | `~/.config/opencode/opencode.json{,c}` | JSON/JSONC | No |
| Rules ✅ | `AGENTS.md` (walks up; `CLAUDE.md` fallback) | `~/.config/opencode/AGENTS.md` (`~/.claude/CLAUDE.md` fallback) | Markdown | No |
| Agents ✅ | `.opencode/agents/*.md` | `~/.config/opencode/agents/*.md` | Markdown + frontmatter | No |
| Skills ✅ | `.opencode/skills/<name>/SKILL.md` (also reads `.claude/skills/`, `.agents/skills/`) | `~/.config/opencode/skills/` (also `~/.claude/skills/`, `~/.agents/skills/`) | SKILL.md | No |
| Commands ✅ | `.opencode/commands/*.md` | `~/.config/opencode/commands/*.md` | Markdown + frontmatter | No |
| MCP servers ✅ | `mcp` block in config | same | JSON | No |
| Custom tools ✅ | `.opencode/tools/*.ts` | `~/.config/opencode/tools/*.ts` | `@opencode-ai/plugin` `tool()` + Zod | **Yes** |
| Plugins (hooks) ✅ | `.opencode/plugins/*.{ts,js}` | `~/.config/opencode/plugins/` + npm via config `plugin: []` | JS/TS module returning hooks | **Yes** |
| Providers / themes / keybinds | config fields | config fields | JSON | No |

**Directory naming:** current docs use **plural** (`skills/`, `agents/`, `tools/`, `plugins/`,
`commands/`, `modes/`, `themes/`) and state that singular names (e.g. `agent/`) are still
supported for backwards compatibility ✅. Emit plural; read singular as legacy.

## The TypeScript constraint (plainly)

- **Declarative, no TS:** config, rules, agents, skills, commands, MCP registration.
- **TypeScript on Bun, no way around it:** custom tools and plugins — and since plugins
  are the ONLY hook mechanism, **anything hook-shaped requires TS**. A shell-script hook
  can survive as the *implementation* (a thin TS plugin wrapper `$`-execs it), but the
  registered artifact must be a TS module.

## Claude-code → opencode quick map

Full table + per-primitive notes: `references/cc-to-opencode-mapping.md`.

- **Skills → near-zero translation.** opencode reads `.claude/skills/` and `~/.claude/skills/`
  natively ✅. Stricter name rule applies: `^[a-z0-9]+(-[a-z0-9]+)*$`, 1–64 chars, must match dir ✅.
- **Agents → mechanical frontmatter remap** (model needs `provider/model` prefix; CC `tools:`
  list becomes OC `permission:` allow/ask/deny map).
- **MCP → mechanical config reshape** (`.mcp.json` → config `mcp` block; `type: local|remote`).
- **Hooks → NOT mechanical, currently deferred.** A CC→opencode capability matrix marks
  hook→opencode **✗ deferred**; the viable design when wanted is an OC **plugin**: generated
  TS wrapper mapping events (`PreToolUse`→`tool.execute.before`, `PostToolUse`→`tool.execute.after`
  — real `Hooks` members ✅; `SessionStart`→ the `event` member filtering
  `event.type === "session.created"` — an SDK *Event* value, not a hook key ✅) that shells out
  to the existing script. Some CC events have no exact equivalent.
- **CLAUDE.md → AGENTS.md** (or nothing: CLAUDE.md is read as a fallback ✅). Path-scoped CC
  rules have no direct equivalent — approximate with `instructions` globs ✅.
- **Plugins/bundles → no marketplace.** Distribution = laying files into the right dirs +
  merging a config fragment (config files are merged, later levels override only conflicting
  keys ✅; whether arrays concatenate or replace is unverified — the docs do not say).

## Read next (progressive disclosure)

- `references/configuration.md` — config schema, precedence chain, key fields, storage paths.
- `references/extension-surfaces.md` — each surface with a minimal working example.
- `references/cc-to-opencode-mapping.md` — the full translation table (feeds a
  CC → opencode translation/build step, if one exists in your project).
- `references/distribution.md` — how a generated opencode bundle should be laid out,
  install/merge behavior, gotchas.
