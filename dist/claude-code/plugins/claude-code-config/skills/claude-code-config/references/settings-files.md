# The settings files, precedence, and the key catalog

The reference for **which file** a change belongs in and **which key** expresses it. Read this
before editing; the wrong file or a non-existent key is the most common way a config change
silently does nothing.

## The files, top to bottom by precedence

Higher entries override lower ones for the same key.

| # | File | Where | Scope | Committed to git? |
|---|---|---|---|---|
| 1 | Managed policy settings | An admin-installed system path (organization-controlled) | Everyone on the managed machine | n/a — you do not author it |
| 2 | Command-line flags | The invocation itself (e.g. a `--permission-mode` flag) | This one run | n/a — not a file |
| 3 | `.claude/settings.local.json` | Project root | This project, **this machine only** | **No** — auto-added to gitignore |
| 4 | `.claude/settings.json` | Project root | This project, **shared with the team** | **Yes** |
| 5 | `~/.claude/settings.json` | Your home directory | **You**, across all projects | n/a — user home |

### Which file for which change

- **Only this project needs it, and it's shareable** → `.claude/settings.json` (committed).
- **Only this project, and it's machine-specific or secret-adjacent** → `.claude/settings.local.json`
  (never committed). Personal experiments, a local tool path, a personal permission relaxation.
- **You want it in every project** → `~/.claude/settings.json`.
- **The organization must enforce it** → managed policy (an administrator's job, not yours).

Narrowest-scope rule: default to the project-local file. Promote to the shared project file only
when the team genuinely needs it, and to your user file only when *you* want it everywhere.
A secret or a machine-specific path in the **committed** `settings.json` is a leak — it belongs
in `settings.local.json`.

## JSON shape and validity

Each file is a single JSON object. Top-level keys are the categories below. There are no
comments in JSON — a `//` or `#` line makes the file invalid and the harness ignores the whole
file with no error. Always finish with:

```bash
python3 -m json.tool < .claude/settings.json   # prints the parsed file, or the parse error
```

A file that fails to parse is treated as absent. This is the single most common cause of "my
setting did nothing".

## The key catalog

These are the top-level keys you will most often set. Consult the current Claude Code settings
documentation for the complete list before relying on a key not shown here — do not invent keys.

| Key | Type | Purpose | Detail |
|---|---|---|---|
| `permissions` | object | allow / deny / ask rules, default mode, extra readable dirs | `references/permissions.md` |
| `hooks` | object | run a script on a harness event | `references/hooks.md` |
| `env` | object of strings | environment variables set for every session in scope | below |
| `model` | string | default model for sessions in scope | — |
| `enableAllProjectMcpServers` | boolean | auto-approve every server declared in `.mcp.json` | MCP section |
| `enabledMcpjsonServers` | array of strings | approve specific `.mcp.json` servers by name | MCP section |
| `disabledMcpjsonServers` | array of strings | block specific `.mcp.json` servers by name | MCP section |
| `statusLine` | object | custom status-line command | — |
| `cleanupPeriodDays` | number | how long transcripts are retained | — |
| `includeCoAuthoredBy` | boolean | whether commits add a co-author trailer | — |

### `env` — environment variables

`env` is a flat object of string-valued variables applied to every session within the file's
scope (and to the shells the agent spawns). Use it for build/runtime flags a project needs.

```json
{ "env": { "APP_ENVIRONMENT": "development", "TZ": "UTC" } }
```

**`env` requires a fresh session** — variables are read once at startup, so an edit does not
reach the running session. Never put a real secret value here in a committed file; reference an
externally-provided variable instead of pasting the literal.

See `references/examples/env.settings.json` for a validatable copy.

## MCP server registration (pointers)

MCP servers are **not** declared inside `settings.json`. They live in their own place, and
settings only govern which of them are enabled.

- **Where servers are declared:** a project's servers go in a **`.mcp.json` file at the project
  root** (project scope — shareable, committed). This is the file you edit to add a server. See
  `references/examples/mcp.mcp.json` for the shape (a `mcpServers` object; each server is either
  a `command`+`args` local process or a `type: http` URL, with an `env`/`headers` block that
  references secrets as `${VAR}`, never inline literals).
- **Scopes for a server** mirror the settings scopes: *local* (private to you in this project,
  the default when adding one interactively), *project* (`.mcp.json`, shared with the team), and
  *user* (available to you across all projects). Choose the same way you choose a settings file:
  narrowest scope that works; a shared server with a secret means the secret is an env reference,
  not a committed literal.
- **Enabling `.mcp.json` servers** is what `settings.json` controls: `enableAllProjectMcpServers`
  (approve all), or `enabledMcpjsonServers` / `disabledMcpjsonServers` (an allow/deny list by
  server name). A project `.mcp.json` server stays inactive until approved.
- **Verify** with the `/mcp` command (lists servers and connection status). A registration
  change generally needs a reconnect or a fresh session — see `references/verification.md`.
