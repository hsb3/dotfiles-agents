---
name: dotfiles-expert
description: Expert knowledge of Henry's personal dotfiles at ~/dotfiles — the GNU Stow layout and per-package ownership, shell customizations (zsh aliases/functions/PATH and the dangerous rm/cp/mv -i aliases), AI tooling (Claude Code hooks + cc-hooks per-project enablement, settings/instructions/memory conventions, deepagents-code/dcode, Antigravity agy), bin utility scripts, package-manager supply-chain hardening (7-day cooldown, no install scripts, no git deps) and its per-command overrides, mise runtimes, and the install.sh bootstrap. Use this whenever working in or asking about ~/dotfiles, "my dotfiles", stow packages, the shell/aliases/zsh config, Claude Code global config (hooks, instructions, rules, statusline, memory), dcode/deepagents, agy/antigravity, npm/pnpm/bun/uv/pip install failures or cooldowns, mise/Python/Node versions, the install/lint scripts, or any of Henry's machine customizations — even when the file isn't named, the goal is to navigate to the authoritative source rather than guess paths or commands.
---

# Dotfiles Expert

Henry's machine is configured almost entirely from one git repo: **`~/dotfiles`** (GitHub `hsb3/dotfiles`). This skill makes you fluent in its structure so you navigate to the right authoritative file instead of guessing paths, aliases, or commands.

**Core principle: pointers over memory.** The repo is heavily self-documented. `~/dotfiles/CLAUDE.md` (~25 KB, hot-loaded into every session in that repo) is the master overview. Do NOT restate it from memory — go read the source file for the detail you need. This skill captures the *map and the non-obvious gotchas*; the references hold the exhaustive enumerations.

## How the repo works (the one mental model)

Personal **macOS** dotfiles managed with **GNU Stow**. Each top-level directory is a *stow package*: `stow <pkg>` symlinks `~/dotfiles/<pkg>/...` into `$HOME`, preserving structure. So `zsh/.zshrc` → `~/.zshrc`, `bin/.local/bin/foo` → `~/.local/bin/foo`, `claude-code/.claude/hooks/` → `~/.claude/hooks/`.

```bash
./install.sh                                    # full bootstrap (brew, uv tools, mise, stow, launchd, .env)
./lint.sh                                       # static analysis + test suites — run before committing
stow --restow --ignore='.DS_Store' <package>    # re-symlink one package after moving files inside it
stow --adopt --restow <pkg>                     # pull existing real files into the package
```

The canonical stow-package list (in BOTH `install.sh` and `lint.sh` as `STOW_PACKAGES`):
`zsh tmux starship git iterm2 reminders tmuxinator zed helix claude-code opencode mise bin aider btop micro deepagents langrepl codex pnpm bun uv pip`

**Not stow packages** (live in the repo but wired by absolute path / copied manually): `deepagents_customizations/`, `antigravity/`, `scripts/`, `.docs/`. See gotchas.

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
| Shell functions (`bg`, `proj`, `timer`, `theme`, …) | `zsh/.zsh/functions.zsh` |
| PATH, `$DOTFILES`, `NODE_OPTIONS` heap cap | `zsh/.zsh/path.zsh` |
| `agent()` tmux launcher | `zsh/.zsh/ai.zsh` |
| zsh package overview + alias/function tables | `zsh/README.md` |
| bin utility scripts (per-script usage) | `bin/README.md` |
| Claude Code global config index | `claude-code/.claude/CLAUDE.md` (imports `instructions/*`) |
| Claude Code working conventions | `claude-code/.claude/instructions/*.md` |
| Claude Code path-scoped rules | `claude-code/.claude/rules/*.md` |
| Claude Code hooks (inventory + enable) | `claude-code/.claude/hooks/README.md` + each hook's `config.json` |
| Live global hook wiring | `claude-code/.claude/settings.json` |
| Every settings.json key explained | `.docs/claude-code-settings-reference.md` |
| Skills ecosystem (2-tier model, `skills` CLI) | `.docs/reference/skills-inventory.md` |
| deepagents-code (`dcode`) full footprint | `.docs/deepagents-code.md` |
| deepagents hooks / native models / `da-hooks` | `deepagents_customizations/README.md` |
| Antigravity (`agy`) install/auth/customization | `~/.claude/projects/-Users-henry-Developer/memory/reference-antigravity-cli-agy.md` + `antigravity/README.md` |
| dcode rename history (cli → code) | `~/.claude/projects/-Users-henry-Developer/memory/reference-deepagents-dcode-rename.md` |
| Beginner terminal walkthrough | `.docs/terminal-guide.md` |
| Stack rationale (why each tool) | `.docs/spec-dotfiles.md` |
| Homebrew packages/casks | `Brewfile` (+ `Brewfile.vscode`) |
| mise runtime versions | `mise/.config/mise/config.toml` |

## The big gotchas (load-bearing — internalize these)

1. **Dangerous aliases: `rm`/`cp`/`mv` are aliased to interactive `-i`.** In a non-interactive Bash tool call they prompt then silently abort (stdin is closed). Use `rm -f`; for cp/mv **bypass the alias with `command cp` / `command mv`** (note: `cp -f` does NOT override `-i` on macOS). Prefer Edit/Write or `git restore` over `cp` when restoring. Also: `cat` → `bat`, `ls` → `eza`. Source: `zsh/.zsh/aliases.zsh`.

2. **Package-manager installs are hardened by default — a failure is usually intentional, not a bug to "fix" by disabling protection.** A 7-day install cooldown + blocked install scripts + blocked git/non-registry deps span npm/pnpm/bun/uv/pip. When an install fails for one of these reasons, use the documented *per-command* override, don't flip the global default. Full failure-signature → fix table in **`references/supply-chain.md`**.

3. **Claude Code hooks are mostly opt-in per project, NOT global.** Only a couple run everywhere (wired in `claude-code/.claude/settings.json`). Per-project hooks (`speak_summary`, `notify_on_stop`, `session_end`, …) are enabled with the **`cc-hooks`** CLI, which merges a hook's `config.json` into the project's `.claude/settings.local.json`. See `references/claude-code.md`.

4. **The interactive terminal agent is `dcode` (deepagents-code), not `deepagents-cli`.** Renamed mid-2026. Do NOT `uv tool upgrade deepagents-cli` expecting the agent — that package became LangGraph deploy tooling. Install/upgrade `deepagents-code`. See `references/ai-tooling.md`.

5. **`deepagents_customizations/` and `antigravity/` are in the repo but NOT stowed.** They're wired by absolute path (`hooks.json` hardcodes `${DOTFILES}/deepagents_customizations/hooks/*.sh`; `native_models` is injected into dcode's venv via `uv tool install --with`) or run manually. Their internal `bin/` dirs are therefore never deployed.

6. **Memory files are not hot-loaded.** Only `MEMORY.md` indexes are; individual `reference_*.md` memory files load on demand. Operational/cold-path detail belongs in a memory file with a one-line pointer, not in `CLAUDE.md`. The `agy` and `dcode-rename` notes above live in the auto-memory dir.

## References — read the one matching the task

Each reference is standalone and includes its own detail tables. Pull in only what's relevant:

- **`references/repo-and-stow.md`** — full per-package ownership table, the stow workflow in depth, `.env`/machine-local/runtime-state conventions, zsh loading order, adding a new package, install.sh + lint.sh anatomy, mise runtimes, Brewfile structure.
- **`references/shell.md`** — every alias and function with the dangerous-alias and PATH/`NODE_OPTIONS` gotchas; the `agent`/`dcode`/`lg`/`ccstatus`/`da-hooks` shell entry points.
- **`references/claude-code.md`** — the `claude-code` package: instructions vs rules, the hook inventory (global vs opt-in), `cc-hooks` per-project enablement, statusline, settings.json conventions, memory hygiene, and the skills ecosystem (2-tier core/plugin model + `skills` CLI).
- **`references/ai-tooling.md`** — the full AI-agent surface beyond Claude Code: deepagents-code/`dcode` footprint + hooks + native models, Antigravity `agy` (install/auth/the "silent empty output" failure + fix), langrepl, aider, codex, and the bin scripts that support them (`da-prune-sessions`, `cc-hooks`, `migrate-claude-memory`).
- **`references/supply-chain.md`** — the npm/pnpm/bun/uv/pip hardening posture, every setting, the failure-signature → per-command-override table, and the commented opt-ins.

## Known-stale / inconsistent (flag, don't trust blindly)

The repo is mid-migration in places. When you hit these, verify against current source:

- **`deepagents-dev`** (`bin/.local/bin/`) is **stale** — targets the old `libs/cli/.venv` path from before the `cli`→`code` (`dcode`) rename; would need repointing at `libs/code`.
- **`deepagents-env-dump`** (`deepagents_customizations/bin/.local/bin/`) is **orphaned + stale** — its dir isn't stowed so it's not in `~/.local/bin`, and it introspects the removed `deepagents_cli._server_config` schema.
- **`README.md`** lags `CLAUDE.md` in spots (older test counts ~97 vs current 156; describes the pre-`dcode` `deepagents-cli`). `CLAUDE.md` is the more current source.
- **Hook-global mismatch:** the live `settings.json` wires `post_write_format` + shell-lint + `curate_memories` + a memory-notification snippet globally, whereas the hooks `README.md` marks `post_write_format` as "not global." Treat `settings.json` as ground truth for what actually runs.
- Stale `.docs` describing the removed CLI (`deepagents-cli-internal-error.md`, `deepagents-db-cleanup.sh`, `.docs/reference/deepagents-cli/`) are superseded by `.docs/deepagents-code.md` + `da-prune-sessions`.
