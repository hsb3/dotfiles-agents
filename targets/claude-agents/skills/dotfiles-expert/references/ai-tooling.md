# AI agent tooling beyond Claude Code

Covers deepagents-code (`dcode`), Antigravity (`agy`), langrepl, aider, codex, and the bin scripts that support them. Authoritative sources cited per section.

## deepagents-code (`dcode`) — the interactive terminal agent

Full footprint map: `~/dotfiles/.docs/deepagents-code.md`. Customizations: `deepagents_customizations/README.md`. History: the `reference-deepagents-dcode-rename` memory note.

**The rename you must know.** langchain-ai split the `deepagents` repo mid-2026. The interactive terminal agent moved `deepagents-cli` → **`deepagents-code`** (command **`dcode`**, `libs/code`). The old `deepagents-cli` 0.2.x (`libs/cli`) was *repurposed* into LangGraph Platform deploy tooling. So **do NOT `uv tool upgrade deepagents-cli` expecting the agent** — install/upgrade `deepagents-code`. The harness library is `deepagents` (0.6.x). Henry migrated his customizations to dcode on 2026-06-06 (`deepagents_customizations/MIGRATION-dcode.md`).

**Install / reproduce:**
```bash
uv tool install deepagents-code --with ~/dotfiles/deepagents_customizations/native_models
```
`dcode` lands at `~/.local/bin/dcode` (symlink into the uv-tool venv). `install.sh` does this, then stows `deepagents` (config examples) and seeds machine-local `config.toml` + `hooks.json` from examples.

**Component map** (where each piece lives — none of `deepagents_customizations/` is stowed):

| Component | Source | Lands at |
|---|---|---|
| `dcode` tool | uv tool (install.sh) | `~/.local/bin/dcode` |
| config dir (profiles, `load_env.sh`) | `deepagents/.deepagents/` (stow pkg `deepagents`) | `~/.deepagents/` |
| `native_models` (custom BaseChatModel wrappers) | `deepagents_customizations/native_models/` | injected into dcode's venv via `--with` |
| hooks ×5 | `deepagents_customizations/hooks/` | referenced by absolute path from `~/.deepagents/hooks.json` |
| `da-hooks` CLI | `deepagents_customizations/hooks_cli` | `da-hooks` alias |
| `dcode` alias + `agent()` | `zsh/.zsh/aliases.zsh`, `ai.zsh` | shell |
| `da-prune-sessions` | `bin/.local/bin/` | `~/.local/bin/` ✓ |

**Runtime `~/.deepagents/`:** stowed symlinks (profiles, `load_env.sh`, `*.example`) + machine-local real files (`config.toml`, `hooks.json`, `.env`, seeded by install.sh) + runtime state (`.state/sessions.db` — LangGraph checkpoints, can grow to GBs; prune with `da-prune-sessions`).

**native_models wrappers** (`config.toml` `[models.providers.*]` `class_path`): `ChatAnthropicNative` (web_search, code_execution, web_fetch), `ChatOpenAINative` (web_search), `ChatGoogleGenAINative` (google_search, url_context — not usable with dcode due to a function-calling restriction).

**Active hooks** (`~/.deepagents/hooks.json`, all via `${DOTFILES}/deepagents_customizations/hooks/`): `notify_on_complete.sh` (task.complete), `notify_on_error.sh` (tool.error), `notify_on_compact.sh` (context.compact), `session_log.sh` (session.start/end → `~/.deepagents/sessions.log`), `speak_summary.sh` (task.complete → spoken summary). Auto-discovered via `# hook:` metadata headers; event reference in `hooks/EVENTS.md` (8 events). dcode's `hooks.py` also emits a `user.name.set` event (per `MIGRATION-dcode.md`) — not listed in EVENTS.md.

**`da-hooks` CLI:** `da-hooks list-hooks | install | status | test`.

## Antigravity (`agy`) — Google/Gemini-backed CLI

Full detail: the `reference-antigravity-cli-agy` memory note + `~/dotfiles/antigravity/README.md` / `CHEATSHEET.md`.

`agy` = standalone ~138 MB Go binary at `~/.local/bin/agy` (NOT a uv tool, NOT from a stow package; PATH set in `.zshrc`). **No `agy login`/`auth` subcommand** — login is a browser OAuth flow triggered by running `agy` interactively. Config: CLI data in `~/.gemini/antigravity-cli/` (legacy, mostly ignored); the **live** shared config is `~/.gemini/config/` (`config.json`, `mcp_config.json`, `skills/`, `plugins/`, `AGENTS.md`). Per-run debug: `agy --log-file /tmp/x.log -p "..."`.

**Known failure signature ("silent empty output"):** `agy -p "..."` exits 0 with empty output while `--version`/`--help`/`models` still work (read-only calls don't need a project). Cause: native login token broke → fell back to a stale keyring `gcp` credential with no Cloud project → `invalid project ID: ""`. Setting `GOOGLE_CLOUD_PROJECT` does NOT fix it. **Fix:** reset `cache/onboarding.json` to all-false (forces the GCP-project picker), run `agy` interactively, authenticate, select the project (Henry's: `your-gcp-project`). Resolved 2026-06-05. Gotcha: macOS case-insensitive FS means `~/Developer` vs `~/developer` are keyed as separate workspaces → "re-auth in every folder"; auth at the parent or stick to one casing.

**Mirror of Claude config:** agy mirrors Claude Code's layout ~1:1 in `~/.gemini/config/` — MCP servers (`mcp_config.json`), skills (`skills/<name>/SKILL.md`, identical format so Claude skills port by symlink), plugins (needs a root `plugin.json`, rejects Claude's nested `.claude-plugin/plugin.json`), global rules (`AGENTS.md`, no `@import`). The reproducer is **`~/dotfiles/antigravity/sync-from-claude.py`** (idempotent; assembles mcp_config + skill symlinks + plugin wrappers + AGENTS.md from `claude-code/.claude/{instructions,rules}`).

## Other agents / REPLs

- **langrepl** (`lg` alias) — LLM agent REPL. `lg` sources `~/.langrepl/.env` then `langrepl -w ~`; `lg -a <agent>` for a specific agent. Config in the `langrepl` stow package (`~/.langrepl/`). Installed via `uv tool install --python 3.13 langrepl`.
- **aider** — `uv tool install aider-chat`. `ask-aider` alias = `aider --chat-mode ask --message`. Config in the `aider` stow package.
- **codex** (OpenAI Codex CLI) — `codex` stow package manages `~/.codex/` skills + config template; `config.toml` is machine-local (seeded from example).
- **opencode** — `opencode` stow package; `~/.opencode/bin` added to PATH if present.

## Supporting bin scripts

Per-script usage in `bin/README.md`. AI-relevant ones:

| Script | Purpose |
|---|---|
| `da-prune-sessions` | prune `~/.deepagents/.state/sessions.db` (dry-run by default; `--days`, `--keep`, `--all`, `--apply`) |
| `cc-hooks` | enable/disable Claude Code hooks per project (see `references/claude-code.md`) |
| `migrate-claude-memory` | move a project's Claude memory after relocating its folder (slug-aware; dry-run default) |
| `models-dev` | LLM model info from models.dev; `--update` refreshes `~/.claude/instructions/models.md` |
| `speak` / `speak_gemini` | local TTS (Kokoro) / cloud TTS (Gemini, voice profiles) — used by the speak_summary hooks |

## Stale / orphaned (verify before trusting)

- **`deepagents-dev`** (`bin/.local/bin/`) — stale: targets the old `libs/cli/.venv/bin/deepagents`; predates the `cli`→`code` rename. Needs repointing at `libs/code`.
- **`deepagents-env-dump`** (`deepagents_customizations/bin/.local/bin/`) — orphaned (dir not stowed → not in `~/.local/bin`) AND stale (introspects removed `deepagents_cli._server_config` / `DA_SERVER_*`).
