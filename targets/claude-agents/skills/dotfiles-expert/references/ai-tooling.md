# AI agent tooling beyond Claude Code

Covers Antigravity (`agy`), the `opencode`/`aider` terminal agents, the `secret` Keychain tooling, the TTS scripts, and the AI-adjacent bin utilities. Authoritative sources cited per section.

> **What's gone (do NOT act on old guidance):** the `deepagents`/`dcode`, `deepagents_customizations`, `langrepl`/`lg`, and `codex` stow packages were **removed** (deepagents archived 2026-07-01, config neutralized 2026-07-09). Any reference to `dcode`, `da-hooks`, `native_models`, `deepagents-cli`, `da-prune-sessions`, or a `~/.deepagents/` tree is dead. The terminal agents on this machine are **`claude`** and **`opencode`** (launched together via the `agent` shell function — see `references/shell.md`).

## Antigravity (`agy`) — Google/Gemini-backed CLI

Full detail: `~/dotfiles/antigravity/README.md` + `antigravity/CHEATSHEET.md`. Note `antigravity/` is in the repo but **NOT a stow package** — it configures agy's `~/.gemini/` tree (runtime state mixed with config) and a VS Code-fork IDE, so it's wired by absolute path / copied in rather than symlinked.

`agy` = standalone Go binary at `~/.local/bin/agy` (formerly gemini-cli; NOT a uv tool, NOT from a stow package; PATH set in `.zshrc`). **No `agy login`/`auth` subcommand** — login is a browser OAuth flow triggered by running `agy` interactively. Config: CLI data in `~/.gemini/antigravity-cli/` (legacy, mostly ignored); the **live** shared config is `~/.gemini/config/` (`config.json`, `mcp_config.json`, `skills/`, `plugins/`, `AGENTS.md`). Per-run debug: `agy --log-file /tmp/x.log -p "..."`.

**Known failure signature ("silent empty output"):** `agy -p "..."` exits 0 with empty output while `--version`/`--help`/`models` still work (read-only calls don't need a project). Cause: native login token broke, fell back to a stale keyring `gcp` credential with no Cloud project. Setting `GOOGLE_CLOUD_PROJECT` does NOT fix it. **Fix:** reset `cache/onboarding.json` to all-false (forces the GCP-project picker), run `agy` interactively, authenticate, select the project. Gotcha: macOS case-insensitive FS means `~/Developer` vs `~/developer` key as separate workspaces, causing "re-auth in every folder" — auth at the parent or stick to one casing.

**Mirror of Claude config:** agy mirrors Claude Code's layout ~1:1 in `~/.gemini/config/` — MCP servers (`mcp_config.json`), skills (`skills/<name>/SKILL.md`, identical format so Claude skills port by symlink), plugins (needs a root `plugin.json`, rejects Claude's nested `.claude-plugin/plugin.json`), global rules (`AGENTS.md`, no `@import`). The reproducer is **`~/dotfiles/antigravity/sync-from-claude.py`** (idempotent; assembles mcp_config + skill symlinks + plugin wrappers + AGENTS.md from `claude-code/.claude/{instructions,rules}`). `antigravity/statusline/statusline.py` provides an agy CLI statusline; `antigravity/ide/` is a reference snapshot of the IDE config (copied in manually, not symlinked).

## Terminal agents & REPLs

- **claude** (Claude Code) — the primary agent; global config is the `claude-code` stow package (see `references/claude-code.md`).
- **opencode** — `opencode` stow package manages its config; `~/.opencode/bin` is added to PATH if present. Preferred fallback in the `agent` function when `claude` is absent.
- **aider** — `uv tool install aider-chat` (done by `install.sh`). `ask-aider` alias = `aider --chat-mode ask --message`. Config in the `aider` stow package.

## API keys — macOS Keychain (source of truth)

Full docs: `~/dotfiles/secrets/.config/secrets/README.md`. Core API keys live in the **macOS Keychain**; shell env and MCP config files are generated projections.

- **`secret`** bin CLI — the source of truth: `secret set KEY`, `secret get KEY`, `secret list`, `secret export` (emits shell `export` lines), `secret import`, `secret check`. `.zshrc` runs `eval "$(secret export)"` after sourcing `~/.env`, so the Keychain wins.
- **`mcp-secrets-sync`** bin script — projects Keychain keys into MCP config files that GUI apps read (e.g. Claude Desktop), which can't read the Keychain themselves. Add/rotate a key: `secret set KEY` then `mcp-secrets-sync`.
- `secrets/.config/secrets/manifest.txt` — tracked manifest of key *names* (no values). Keys flagged `noexport` (2nd column) are Keychain-only — never exported into shells; fetch per-use with `secret get KEY`. The LLM provider keys (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`) are flagged this way.
- `~/.env` (symlink to gitignored `~/dotfiles/.env`) is a **backstop only** — recreate it only as a temporary vehicle for importing new keys. Never commit `.env`.

## TTS scripts

Both are bin scripts (per-script usage in `bin/README.md`; deeper notes in `_docs/reference/speak_gemini.md`):

- **`speak_kokoro`** — local TTS via Kokoro (`uv tool install kokoro`, needs `espeak-ng`). Subcommands: `speak_kokoro "text"`, `demo`, `voices`, `preview` (TUI), `repl`. Flags `-v VOICE`, `-s SPEED`; env `SPEAK_VOICE`, `SPEAK_SPEED`. (Renamed from `speak` on 2026-07-07; the bare `speak` name is reserved for a future built-in wrapper.)
- **`speak_gemini`** — natural-sounding cloud TTS (Gemini). **Auto-falls back to `speak_kokoro`** when the cloud call fails and both `speak_kokoro` and `kokoro` are on PATH. Disable the fallback with `--no-fallback` or `SPEAK_GEMINI_NO_FALLBACK=1`.

## AI-adjacent bin scripts

Per-script usage in `~/dotfiles/bin/README.md`. The AI-relevant ones (current inventory):

| Script | Purpose |
|---|---|
| `cc-hooks` | enable/disable Claude Code hooks per project (see `references/claude-code.md`); dotfiles ships none for it to manage |
| `cc-project-memory` | give a repo its own tracked, transferable Claude auto-memory at `<repo>/.claude/memory/` (`init [--portable] [--migrate]`, `status`, `path`, `list`) |
| `cc-migrate-memory` | migrate a project's Claude memory after relocating the folder (slug-aware; dry-run default; `--list`) |
| `models-dev` | LLM model info from models.dev; `--update` refreshes `claude-code/.claude/instructions/models.md` (also driven monthly by the `com.henry.models-update` launchd job) |
| `mcp-secrets-sync` | project Keychain keys into GUI-app MCP config files |
| `secret` | macOS Keychain CLI for API keys (source of truth) |
| `speak_kokoro` / `speak_gemini` | local / cloud TTS (used by any speak_summary-style plugin hooks) |
| `fetch-docs` | download docs with a browser UA (Markdown-first); idempotent, manifest-logged |
