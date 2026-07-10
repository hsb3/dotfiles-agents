---
name: dotfiles-expert
description: Expert knowledge of Henry's personal dotfiles at ~/dotfiles — the GNU Stow layout and per-package ownership, shell customizations (zsh aliases/functions/PATH, the dangerous rm/cp/mv -i aliases, and the agent tmux launcher), AI tooling (Claude Code global settings/instructions/rules/memory conventions, plugin-marketplace distribution, Antigravity agy, opencode/aider, the secret Keychain CLI, TTS speak scripts), bin utility scripts, package-manager supply-chain hardening (7-day cooldown, no install scripts, no git deps) and its per-command overrides, mise runtimes, and the install.sh bootstrap. Use this whenever working in or asking about ~/dotfiles, "my dotfiles", stow packages, the shell/aliases/zsh config, Claude Code global config (settings, instructions, rules, statusline, memory, plugins), agy/antigravity, API-key Keychain management, npm/pnpm/bun/uv/pip install failures or cooldowns, mise/Python/Node versions, the install/lint scripts, or any of Henry's machine customizations — even when the file isn't named, the goal is to navigate to the authoritative source rather than guess paths or commands.
---

# Dotfiles Expert

Henry's machine is configured almost entirely from one git repo: **`~/dotfiles`** (GitHub `<owner>/dotfiles`). This skill makes you fluent in its structure so you navigate to the right authoritative file instead of guessing paths, aliases, or commands.

**Core principle: pointers over memory.** The repo is heavily self-documented. `~/dotfiles/CLAUDE.md` (~25 KB, hot-loaded into every session in that repo) is the master overview. Do NOT restate it from memory — go read the source file for the detail you need. This skill captures the *map and the non-obvious gotchas*; the references hold the exhaustive enumerations.

## How the repo works (the one mental model)

Personal **macOS** dotfiles managed with **GNU Stow**. Each top-level directory is a *stow package*: `stow <pkg>` symlinks `~/dotfiles/<pkg>/...` into `$HOME`, preserving structure. So `zsh/.zshrc` → `~/.zshrc`, `bin/.local/bin/foo` → `~/.local/bin/foo`, `claude-code/.claude/hooks/` → `~/.claude/hooks/`.

```bash
./install.sh                                    # full bootstrap (brew, uv tools, mise, stow, launchd, .env)
./lint.sh                                       # static analysis + test suites — run before committing
stow --restow --ignore='.DS_Store' <package>    # re-symlink one package after moving files inside it
stow --adopt --restow <pkg>                     # pull existing real files into the package
```

The canonical stow-package list (in `install.sh`'s stow loop):
`zsh tmux starship git iterm2 reminders tmuxinator zed helix claude-code opencode mise bin aider btop micro pnpm bun uv pip secrets`

(Gotcha: `lint.sh`'s `STOW_PACKAGES` array lags — it omits `secrets`; `install.sh` is the current list. Verify both when adding a package.)

**Not stow packages** (live in the repo but wired by absolute path / copied manually): `antigravity/`, and the underscore-prefixed internal dirs `_scripts/` (bootstrap + Docker), `_docs/` (tracked reference docs + templates), `_meta/` (machine-local planning scratch). See gotchas.

For the full per-package ownership table and the runtime/machine-local file conventions, read **`references/repo-and-stow.md`**.

## Doc map — where the authoritative source lives

Navigate here rather than relying on memorized detail. All paths under `~/dotfiles` unless noted.

| Topic | Authoritative source |
|---|---|
| Master overview (everything, hot-loaded) | `CLAUDE.md` |
| Human-facing tour + command cheatsheet | `README.md` |
| Stow packages / loading order / supply-chain summary | `CLAUDE.md` → "Architecture" |
| Bootstrap (what gets installed, in what order) | `install.sh` |
| Lint + test suites (the pre-commit gate) | `lint.sh` |
| Shell aliases (incl. dangerous `-i` ones) | `zsh/.zsh/aliases.zsh` |
| Shell functions (`bg`, `proj`, `timer`, `theme`, `agent`, …) | `zsh/.zsh/functions.zsh` |
| PATH, `$DOTFILES`, `NODE_OPTIONS` heap cap | `zsh/.zsh/path.zsh` |
| zsh package overview + alias/function tables | `zsh/README.md` |
| bin utility scripts (per-script usage) | `bin/README.md` |
| Claude Code global config index | `claude-code/.claude/CLAUDE.md` (imports `instructions/*`) |
| Claude Code working conventions | `claude-code/.claude/instructions/*.md` |
| Claude Code path-scoped rules | `claude-code/.claude/rules/*.md` |
| Claude Code global settings (live) | `claude-code/.claude/settings.json` (seed: `settings.json.example`) |
| Plugin/marketplace distribution (enabledPlugins) | `claude-code/.claude/settings.json.example` |
| Every settings.json key explained | `_docs/reference/claude-code/claude-code-settings-reference.md` |
| Claude memory conventions | `_docs/reference/claude-code/claude-memory-reference.md` |
| Repo-local `stow` guard hook | `.claude/hooks/pre_stow_check/` (repo-root; not stowed) |
| Antigravity (`agy`) mirror/install/auth | `antigravity/README.md` + `antigravity/CHEATSHEET.md` |
| API keys — Keychain source of truth | `secrets/.config/secrets/README.md` + `bin/.local/bin/secret` |
| Homebrew packages/casks | `Brewfile` (+ `Brewfile.vscode`) |
| mise runtime versions | `mise/.config/mise/config.toml.example` (live file is machine-local) |

## The big gotchas (load-bearing — internalize these)

1. **Dangerous aliases: `rm`/`cp`/`mv` are aliased to interactive `-i`.** In a non-interactive Bash tool call they prompt then silently abort (stdin is closed). Use `rm -f`; for cp/mv **bypass the alias with `command cp` / `command mv`** (note: `cp -f` does NOT override `-i` on macOS). Prefer Edit/Write or `git restore` over `cp` when restoring. Also: `cat` → `bat`, `ls` → `eza`. Source: `zsh/.zsh/aliases.zsh`.

2. **Package-manager installs are hardened by default — a failure is usually intentional, not a bug to "fix" by disabling protection.** A 7-day install cooldown + blocked install scripts + blocked git/non-registry deps span npm/pnpm/bun/uv/pip. When an install fails for one of these reasons, use the documented *per-command* override, don't flip the global default. Full failure-signature → fix table in **`references/supply-chain.md`**.

3. **Dotfiles ships NO Claude Code hooks anymore (2026-07-07).** They were migrated out of `claude-code/.claude/hooks/` to the `dotfiles-agents-workbench` incubator; proven ones are redistributed as **plugins** via the `dotfiles-agents` marketplace (wired in `settings.json.example` `enabledPlugins`/`extraKnownMarketplaces`), NOT re-added to dotfiles. The **only** hook in the repo is the repo-local `pre_stow_check` at the repo-root `.claude/hooks/` (blocks `stow` calls missing `--ignore='.DS_Store'`; wired machine-locally, not stowed). `cc-hooks` (the bin CLI) still exists but manages whatever hooks a user places in `~/.claude/hooks/` — dotfiles puts none there. See `references/claude-code.md`.

4. **Skill/plugin distribution is the plugin marketplace, not a CLI.** The old `skills` bin CLI was retired (2026-07-09). Skills and plugins now come from the `dotfiles-agents` marketplace: `settings.json.example` lists `enabledPlugins` (e.g. `project-workflow@dotfiles-agents`, `media-gen@dotfiles-agents`) + `extraKnownMarketplaces`. Manage with native `claude plugin install|enable|disable` and `claude plugin marketplace update`. (This very skill is authored in the `dotfiles-agents` repo and compiled, not symlinked from a `skills/` shelf.)

5. **deepagents/dcode is gone; the terminal agents are `claude` and `opencode`.** The `deepagents`, `deepagents_customizations`, `langrepl`, and `codex` packages were removed (deepagents archived 2026-07-01, config neutralized 2026-07-09). Any old guidance about `dcode`, `da-hooks`, `native_models`, or `deepagents-cli` is dead — do not act on it. The `agent` shell function (in `zsh/.zsh/functions.zsh`) launches `claude` (or `opencode` fallback) in a tmux session. `antigravity/` remains in the repo but is NOT stowed (wired via `sync-from-claude.py`, run manually).

6. **API keys live in the macOS Keychain, not plaintext.** The `secret` bin CLI is the source of truth (`secret set|get|list|export`); `~/.env` is a backstop only. `mcp-secrets-sync` projects keys into GUI-app MCP configs. See the `secrets` package + `references/ai-tooling.md`.

7. **Memory files are not hot-loaded.** Only `MEMORY.md` indexes are; individual topic files load on demand. Operational/cold-path detail belongs in a memory file with a one-line pointer, not in `CLAUDE.md`.

## References — read the one matching the task

Each reference is standalone and includes its own detail tables. Pull in only what's relevant:

- **`references/repo-and-stow.md`** — full per-package ownership table, the stow workflow in depth, `.env`/machine-local/runtime-state conventions, zsh loading order, adding a new package, install.sh + lint.sh anatomy, mise runtimes, Brewfile structure.
- **`references/shell.md`** — every alias and function with the dangerous-alias and PATH/`NODE_OPTIONS` gotchas; the `agent`/`ccstatus`/`theme`/`proj` shell entry points.
- **`references/claude-code.md`** — the `claude-code` package: instructions vs rules, why dotfiles ships no hooks (migration + plugin-marketplace distribution), the repo-local `pre_stow_check` exception, statusline, settings.json conventions, and memory hygiene.
- **`references/ai-tooling.md`** — the AI-agent surface beyond Claude Code: Antigravity `agy` (mirror/install/auth/the "silent empty output" failure + fix), `opencode`, `aider`, the `secret`/`mcp-secrets-sync` Keychain tooling, TTS scripts (`speak_gemini` with `speak_kokoro` fallback), and the `cc-hooks`/`cc-project-memory`/`cc-migrate-memory` bin scripts.
- **`references/supply-chain.md`** — the npm/pnpm/bun/uv/pip hardening posture, every setting, the failure-signature → per-command-override table (incl. the pnpm `onlyBuiltDependencies`-ignored gotcha), and the commented opt-ins.

## Known-stale / inconsistent (flag, don't trust blindly)

The repo self-documents heavily; when a pointer looks off, `CLAUDE.md` is the most current in-repo source. Verify against live source:

- **`lint.sh` `STOW_PACKAGES` lags `install.sh`** — it omits `secrets`. Treat the `install.sh` stow loop as the authoritative package list.
- **Live config files are machine-local, tracked seeds are `*.example`.** `mise/.config/mise/config.toml`, `claude-code/.claude/settings.json` (has an `.example` seed), `reminders/reminders.yaml`, `micro`/`opencode` configs, `btop.conf` — the app rewrites them at runtime, so the repo tracks a `.example` and `install.sh` seeds the live file. Edit the `.example` for shipped defaults; the live file won't be tracked.
- **`README.md` can lag `CLAUDE.md`** on counts/details — prefer `CLAUDE.md`, then the live source file.
