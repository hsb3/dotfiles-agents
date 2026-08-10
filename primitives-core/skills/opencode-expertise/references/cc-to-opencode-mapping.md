# Claude-code → opencode primitive mapping

_The translation table for a Claude Code → opencode distribution pipeline. ✅ = verified
against https://opencode.ai/docs 2026-07-02. Aligned with the distribution-capability-matrix
decision (hooks → opencode currently **deferred**)._

## The table

| CC primitive | OC equivalent | Translation | Effort |
|---|---|---|---|
| **Skill** (`SKILL.md` + references/assets) | Skill — same format ✅ | **Near-zero.** OC discovers `.claude/skills/` and `~/.claude/skills/` natively ✅. Constraints: name must match `^[a-z0-9]+(-[a-z0-9]+)*$` (1–64, == dir) ✅; CC-only frontmatter (`allowed-tools`) is ignored, not an error ✅. Optionally emit a copy under `.opencode/skills/` for explicitness. | Mechanical |
| **Agent persona** (`.claude/agents/*.md`) | Agent (`.opencode/agents/*.md`) ✅ | **Frontmatter remap:** `name` → filename; `model: claude-*` → `anthropic/claude-*` (provider prefix required ✅); CC `tools:` allowlist → OC `permission:` allow/ask/deny map (invert: unlisted CC tools were denied; OC denies via patterns); add `mode: subagent` for CC subagents; `color` passes through. Body/system prompt unchanged. | Mechanical with a rules table |
| **MCP server** (`.mcp.json` entry) | Config `mcp` block ✅ | **JSON reshape:** stdio → `{type: "local", command: [...], environment: {...}}`; http/sse → `{type: "remote", url, headers}`. `${VAR}` env refs survive. Hosted-MCP-only constraint applies to the claude-agents target, not OC. | Mechanical |
| **Hook** (script + config dir, event-named) | Plugin (TS module) ✅ — **currently deferred by decision** | **Not mechanical.** OC has no script+config hook surface; plugins are the only event mechanism and must be TS ✅. Viable design when un-deferred: generate a thin TS wrapper per hook that maps the event (table below) and `$`-execs the existing stdlib script. Blockers: imperfect event coverage, Bun runtime dependency, per-hook wrapper codegen. | Codegen (deferred) |
| **Slash command** (`.claude/commands/*.md`) | Command (`.opencode/commands/*.md`) ✅ | Frontmatter remap + body → `template`-style content; `$ARGUMENTS`/`$1` survive ✅. The remap is mechanical, but nothing is free: there is no `.claude/commands` auto-compat ✅ (unlike skills), so a lane that ships commands must emit them, and a command whose body drives a skill needs that drive re-expressed in OC `skill`-tool terms — an authoring pass per command. | Mechanical + per-command authoring |
| **Rules / CLAUDE.md** | `AGENTS.md` ✅ (CLAUDE.md read as fallback ✅) | Zero (rely on fallback) or rename-copy to AGENTS.md. **Path-scoped CC rules (`paths:` frontmatter) have NO OC equivalent** — nearest approximation is `instructions` globs ✅, which are always-on, not trigger-scoped. Flag path-scoped rules at translation time. | Zero / lossy |
| **Auto-memory** (`MEMORY.md` + topic files) | No native equivalent | Ship memory files as-is (they're plain markdown the repo carries) + reference them from AGENTS.md / `instructions` so sessions load the index. Lazy topic-pull semantics are lost — OC loads what instructions name. | Convention, lossy |
| **Plugin / bundle** (claude plugin marketplace) | No marketplace | A bundle = a **laydown**: files into `.opencode/{agents,skills,commands,plugins,tools}/` + one config **fragment** merged into `opencode.jsonc` (safe: arrays concat, objects deep-merge ✅) + optional npm plugin publication. See `references/distribution.md`. | Generator work |

## Hook-event mapping (for the deferred TS-wrapper design)

| CC hook event | OC plugin hook ✅ | Fidelity |
|---|---|---|
| `PreToolUse` | `tool.execute.before` | Good — can inspect/block |
| `PostToolUse` | `tool.execute.after` | Good |
| `SessionStart` | `session.created` | Good |
| `SessionEnd` | `session.deleted` (or `session.idle`) | Approximate |
| `Stop` | `session.idle` | Approximate — fires on idle, not turn-end |
| `UserPromptSubmit` | `tui.prompt.append` / `message.updated` | Weak — TUI-only / after-the-fact |
| `PreCompact` | `session.compacted` | **After**-the-fact only; no pre-compact intercept |
| `Notification` | `tui.toast.show` | Emit-only (plugin *sends* toasts; doesn't receive CC-style notifications) |
| `SubagentStop` | — | No equivalent found ✅ (session events are per-session; verify child-session semantics) |

## Capability flags for the roster

Per the roster's capability-requirement field, an opencode-bound primitive needs at most:
`requires: [skills]` (nothing), `requires: [mcp-local]` (fine on OC), `requires: [hooks]`
(**excluded from the OC bundle** while hook translation is deferred — the bundle generator
must subset, never silently break).
