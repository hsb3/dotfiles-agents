# Repo structure, GNU Stow, bootstrap & runtimes

Authoritative sources: `~/dotfiles/CLAUDE.md` (master), `~/dotfiles/README.md`, `~/dotfiles/install.sh`, `~/dotfiles/lint.sh`. Read those for the live detail; this is the map.

## The stow model

Each top-level dir is a **stow package**. `stow <pkg>` symlinks `~/dotfiles/<pkg>/<path-relative-to-home>` → `$HOME/<path-relative-to-home>`, preserving structure.

```bash
stow --ignore='.DS_Store' <package>          # symlink a package into $HOME
stow --restow --ignore='.DS_Store' <pkg>     # re-symlink after moving files inside a package
stow --adopt --restow <pkg>                  # adopt existing real files into the package (replaces with symlinks)
stow --simulate <pkg>                        # dry-run — catches $HOME conflicts (lint.sh runs this)
```

Mapping examples: `zsh/.zshrc` → `~/.zshrc`; `zsh/.zsh/aliases.zsh` → `~/.zsh/aliases.zsh`; `tmux/.tmux.conf` → `~/.tmux.conf`; `bin/.local/bin/<script>` → `~/.local/bin/<script>`; `claude-code/.claude/hooks/` → `~/.claude/hooks/`; `git/.gitconfig` → `~/.gitconfig`; `pnpm/Library/Preferences/pnpm/config.yaml` → `~/Library/Preferences/pnpm/config.yaml`.

**Canonical package list** — identical in `install.sh` (stow loop) and `lint.sh` (`STOW_PACKAGES`). Keep them in sync when adding a package:

```
zsh tmux starship git iterm2 reminders tmuxinator zed helix claude-code
opencode mise bin aider btop micro deepagents langrepl codex pnpm bun uv pip
```

## Per-package ownership

| Package | Owns / manages |
|---|---|
| `zsh` | `.zshrc`, `.zshenv`, `.zsh/` (path, plugins, aliases, functions, tools, project-log, ai, prompt) |
| `tmux` | `.tmux.conf` — Ctrl+A prefix, TPM plugins (resurrect, continuum, yank, sessionx) |
| `starship` | `.config/starship.toml` — prompt |
| `git` | `.gitconfig` — rebase pull, histogram diff, diff3, `hx` editor |
| `iterm2` | DynamicProfiles `profiles.json` — Dark / Newspaper / Focus |
| `reminders` | `.local/bin/check-reminders`, `reminders.yaml`, 3 launchd plists (reminders 9am, tool-updates 1st/15th, tmux-cleanup 6pm) |
| `tmuxinator` | `.tmuxinator/` named layouts (`default`, `python-ai`, `fullstack`, `dotfiles`) |
| `zed` | `.config/zed/keymap.json` — vim mode, Space leader |
| `helix` | `.config/helix/config.toml` — `hx` editor |
| `claude-code` | `.claude/` — CLAUDE.md, instructions, rules, hooks, settings.json, statusline (see `references/claude-code.md`) |
| `opencode` | OpenCode terminal-AI config |
| `mise` | `.config/mise/config.toml` — runtime versions (Python 3.13, Node 24) |
| `bin` | `.local/bin/` personal utility scripts (see `bin/README.md`) |
| `aider` | aider config |
| `btop` / `micro` | system monitor / micro editor configs |
| `deepagents` | `.deepagents/` agent profiles, `load_env.sh`, README, `*.example` seeds (machine-local `config.toml`/`hooks.json`/`.env` stay unmanaged) |
| `langrepl` | `.langrepl/` — agents, LLMs, prompts, sandboxes (runtime DB unmanaged) |
| `codex` | `.codex/` — OpenAI Codex CLI skills + config template (runtime files unmanaged) |
| `pnpm` | `Library/Preferences/pnpm/config.yaml` — supply-chain hardening (sibling `rc` = auth, machine-local) |
| `bun` | `.bunfig.toml` — supply-chain hardening |
| `uv` | `.config/uv/uv.toml` — supply-chain hardening (uvx reads it too) |
| `pip` | `.config/pip/pip.conf` — supply-chain hardening (pipx honors it) |

## NOT stow packages (in repo, wired differently)

| Dir | How it's wired | Why not stowed |
|---|---|---|
| `deepagents_customizations/` | absolute path — `hooks.json` hardcodes `${DOTFILES}/deepagents_customizations/hooks/*.sh`; `native_models` injected into dcode's venv via `uv tool install --with` | the deepagents CLI treats every subdir of `~/.deepagents/` as an agent profile, so hook/CLI/model dirs can't live there |
| `antigravity/` | `sync-from-claude.py` run manually (mirrors Claude config into `~/.gemini/config/`) | not a `$HOME` config tree |
| `scripts/` | invoked directly (`install.sh`, `setup-devcontainer.sh`, Docker, pyexpat fix) | bootstrap/CI scripts |
| `.docs/` | reference docs (read manually) | documentation, not config |

Consequence: a non-stowed package's internal `bin/` (e.g. `deepagents_customizations/bin/.local/bin/deepagents-env-dump`) is **never deployed** to `~/.local/bin`.

## Machine-local & runtime files (gitignored, NOT in stow)

- `~/dotfiles/.env` → symlinked to `~/.env` by `install.sh`. `.env.example` is the tracked template. `.zshrc` sources it with `set -a; source ~/.env; set +a`.
- `~/.zshrc.local` — machine-specific overrides, sourced at end of `.zshrc` if present.
- `~/.deepagents/config.toml`, `hooks.json`, `.env` — seeded by `install.sh` from `*.example`; `.state/sessions.db` + logs are runtime.
- `~/.codex/config.toml` — seeded from example (has project-specific trust paths).
- `~/.npmrc` — machine-local, secret-free; NOT stowed (template is `.npmrc.example`). pnpm's auth `rc` is also machine-local.

## zsh loading order (`.zshrc` sources in this order)

1. `path.zsh` — PATH, `$DOTFILES` (`$HOME/dotfiles`), `NODE_OPTIONS="--max-old-space-size=4096"` (4 GB V8 heap cap, added after a 100 GB OOM crash), `MAILCHECK=0`
2. `~/.env` — API keys (allexport)
3. `plugins.zsh` — zinit bootstrap, compinit, fzf-tab, autosuggestions, syntax-highlighting
4. `aliases.zsh`
5. `functions.zsh`
6. `tools.zsh` — zoxide, fzf, **mise activate** (directory-based version switching), `EDITOR`/`VISUAL`=`hx`
7. `project-log.zsh` — chpwd hook logging git-repo entries (for `project-activity`)
8. `ai.zsh` — `agent` launcher
9. `prompt.zsh` — Starship (last)
10. `~/.zshrc.local` if present

`.zshenv` (runs for ALL shells incl. non-interactive) adds **mise shims** to PATH so `node`/`python` work in scripts and Claude Code subshells.

## Runtimes — mise

`mise/.config/mise/config.toml`: `node = "24"`, `python = "3.13"`, `[settings] experimental = true`. mise replaces pyenv + NVM. Reads `.mise.toml`/`.nvmrc`/`.python-version` per-project. uv handles project venvs; mise handles the interpreter versions. Legacy versions installed manually: `mise install python@3.12 python@3.11`.

## Brewfile

`~/dotfiles/Brewfile` (~94 lines) groups: Taps, Terminal & shell, Languages & runtimes (Node/Python NOT here — mise owns them), Package managers, Git TUIs, GitHub & dev tools, Azure, Google Cloud (gcloud installed via Google's installer, NOT brew cask — postinstall fragility), Media & documents, tmux session management, AI & deployment, Fonts, Apps. `brew bundle` re-syncs; `brewup` (a bin script) does the full update cycle. VS Code extensions split into `Brewfile.vscode`.

## install.sh bootstrap order

macOS-only (guards on `uname`). In order: Homebrew → `brew bundle` → pyexpat fix (macOS 26+ workaround) → uv → uv tools (`deepagents-code` with `native_models`, `aider-chat`, `ty`, `langrepl`, `kokoro`) → pipx (`jupyter`) → mise (`python@3.13`, `node@24`) → gh-copilot extension → npm globals (`firebase-tools pnpm yarn nx`) → Google Cloud SDK → TPM → `~/Developer` → **stow all packages** → iTerm2 default profile (Newspaper) → seed `~/.deepagents/{config.toml,hooks.json}` + `~/.codex/config.toml` from examples → launchd jobs (reminders 9am, tmux-cleanup 6pm, tool-updates 1st/15th 10am) → `.env` symlink → verify. Manual post-steps printed at the end (API keys, Zed settings, tmux `Ctrl+a I`, npmrc token, deepagents keys).

## lint.sh — the pre-commit gate

`./lint.sh` (`--fix` to auto-fix ruff). Static analysis + test suites (README cites 156 tests across 4 suites; exact counts drift — read the file). Covers: zsh `-n`, shellcheck, ruff, yamllint, plutil, JSON validation, `stow --simulate` for all packages, plus the deepagents test suites (hooks shell tests, hooks_cli_pkg pytest, native_models pytest, speak_summary_helper). New Python bin scripts → add to `PY_FILES`; new zsh scripts → add to the `zsh -n` loop.

## Adding a new config package

```bash
mkdir -p ~/dotfiles/<package>/<path-relative-to-home>
command cp -r ~/.<config> ~/dotfiles/<package>/
cd ~/dotfiles && stow --ignore='.DS_Store' <package>
# add <package> to the stow loop in install.sh AND STOW_PACKAGES in lint.sh
./lint.sh
```

## Linux/devcontainer path (not stow)

`scripts/setup-devcontainer.sh` (curl-into-bash, or clone first) bootstraps Linux VMs (apt/dnf/apk). Flags: `--minimal`, `--ai-tools claude,opencode,aider,codex`, `--with-env`. Self-contained image in `scripts/Dockerfile` + `docker-compose.yml`. Verified by `scripts/verify-docker-build.sh` (23+ check suite).
