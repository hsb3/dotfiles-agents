# Claude-code → opencode primitive mapping

_The translation table for a Claude Code → opencode distribution pipeline. ✅ = verified
against https://opencode.ai/docs and `@opencode-ai/plugin` 1.18.29 typings 2026-09-06. Aligned
with the distribution-capability-matrix decision (hooks → opencode currently **deferred**)._

## The table

| CC primitive | OC equivalent | Translation | Effort |
|---|---|---|---|
| **Skill** (`SKILL.md` + references/assets) | Skill — same format ✅ | **Near-zero.** OC discovers `.claude/skills/` and `~/.claude/skills/` natively ✅. Constraints: name must match `^[a-z0-9]+(-[a-z0-9]+)*$` (1–64, == dir) ✅; CC-only frontmatter (`allowed-tools`) is ignored, not an error ✅. Optionally emit a copy under `.opencode/skills/` for explicitness. | Mechanical |
| **Agent persona** (`.claude/agents/*.md`) | Agent (`.opencode/agents/*.md`) ✅ | **Frontmatter remap:** `name` → filename; `model: claude-*` → `anthropic/claude-*` (provider prefix required ✅); CC `tools:` allowlist → OC `permission:` allow/ask/deny map (invert: unlisted CC tools were denied; OC denies via patterns); add `mode: subagent` for CC subagents; `color` passes through. Body/system prompt unchanged. | Mechanical with a rules table |
| **MCP server** (`.mcp.json` entry) | Config `mcp` block ✅ | **JSON reshape:** stdio → `{type: "local", command: [...], environment: {...}}`; http/sse → `{type: "remote", url, headers}`. Env refs are rewritten to opencode's `{env:VAR}` form ✅ — not carried across verbatim (`references/extension-surfaces.md` §4). Hosted-MCP-only constraint applies to the claude-agents target, not OC. | Mechanical |
| **Hook** (script + config dir, event-named) | Plugin (TS module) ✅ — **currently deferred by decision** | **Not mechanical.** OC has no script+config hook surface; plugins are the only event mechanism and must be TS ✅. Viable design when un-deferred: generate a thin TS wrapper per hook that maps the event (table below) and `$`-execs the existing stdlib script. Blockers: imperfect event coverage, Bun runtime dependency, per-hook wrapper codegen. | Codegen (deferred) |
| **Slash command** (`.claude/commands/*.md`) | Command (`.opencode/commands/*.md`) ✅ | Frontmatter remap + body → `template`-style content; `$ARGUMENTS`/`$1` survive ✅. The remap is mechanical, but nothing is free: no `.claude/commands` auto-compat is documented ✅ (unlike skills), so a lane that ships commands must emit them, and a command whose body drives a skill needs that drive re-expressed in OC `skill`-tool terms — an authoring pass per command. | Mechanical + per-command authoring |
| **Rules / CLAUDE.md** | `AGENTS.md` ✅ (CLAUDE.md read as fallback ✅) | Zero (rely on fallback) or rename-copy to AGENTS.md. **Path-scoped CC rules (`.claude/rules/*.md` with `paths:` frontmatter ✅) have NO documented OC equivalent** ✅ — nearest approximation is `instructions` globs ✅, which are always-on, not trigger-scoped. Flag path-scoped rules at translation time. | Zero / lossy |
| **Auto-memory** (`MEMORY.md` + topic files) | No native equivalent | Ship memory files as-is (they're plain markdown the repo carries) + reference them from AGENTS.md / `instructions` so sessions load the index. Lazy topic-pull semantics are lost — OC loads what instructions name. | Convention, lossy |
| **Plugin / bundle** (claude plugin marketplace) | No marketplace | A bundle = a **laydown**: files into `.opencode/{agents,skills,commands,plugins,tools}/` + one config **fragment** merged into `opencode.jsonc` (config levels merge, later overrides conflicting keys ✅; array concat is unverified — emit idempotently) + optional npm plugin publication. See `references/distribution.md`. | Generator work |

## Hook-event mapping (for the deferred TS-wrapper design)

Two name sets ✅: a **`Hooks` member** is a key the plugin object returns; an **`Event` value** is
only reachable inside the `event` member as `event.type`. Registering an Event value as a
top-level key does nothing.

| CC hook event | OC surface ✅ | Fidelity |
|---|---|---|
| `PreToolUse` | `Hooks` member `tool.execute.before` (mutate `output.args`, or throw to block) | Good |
| `PostToolUse` | `Hooks` member `tool.execute.after` | Good |
| `PermissionRequest` | `Hooks` member `permission.ask` (set `output.status` allow/deny/ask) | Good |
| `UserPromptSubmit` | `Hooks` member `chat.message` (new user message; can edit `output.parts`) | Good |
| `PreCompact` | `Hooks` member `experimental.session.compacting` (fires *before* compaction; experimental) | Good but unstable API |
| `SessionStart` | `event` member, `event.type === "session.created"` | Good |
| `SessionEnd` | `event` member, `session.deleted` (or `session.idle`) | Approximate |
| `Stop` | `event` member, `session.idle` | Approximate — fires on idle, not turn-end |
| `Notification` | `tui.toast.show` is an Event the TUI consumes, not a hook; a plugin can only *publish* via the client | Emit-only |
| `SubagentStop` | — | No `Hooks` member and no Event found ✅ (session events are per-session; child-session semantics unverified) |

## Capability flags for the roster

Per the roster's capability-requirement field, an opencode-bound primitive needs at most:
`requires: [skills]` (nothing), `requires: [mcp-local]` (fine on OC), `requires: [hooks]`
(**excluded from the OC bundle** while hook translation is deferred — the bundle generator
must subset, never silently break).
