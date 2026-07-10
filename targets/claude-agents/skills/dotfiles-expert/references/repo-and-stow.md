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

Mapping examples: `zsh/.zshrc` → `~/.zshrc`; `zsh/.zsh/aliases.zsh` → `~/.zsh/aliases.zsh`; `tmux/.tmux.conf` → `~/.tmux.conf`; `bin/.local/bin/<script>` → `~/.local/bin/<script>`; `claude-code/.claude/instructions/` → `~/.claude/instructions/`; `git/.gitconfig` → `~/.gitconfig`; `pnpm/Library/Preferences/pnpm/config.yaml` → `~/Library/Preferences/pnpm/config.yaml`.

**Canonical package list** — the `install.sh` stow loop is authoritative:

```
zsh tmux starship git iterm2 reminders tmuxinator zed helix claude-code
opencode mise bin aider btop micro pnpm bun uv pip secrets
```

`lint.sh`'s `STOW_PACKAGES` array should mirror it, but currently **lags** (omits `secrets`) — keep both in sync when adding a package, and treat `install.sh` as the source of truth.

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
| `mise` | `.config/mise/config.toml` — runtime versions (Python 3.14, Node 26); live file seeded from `config.toml.example` |
| `bin` | `.local/bin/` personal utility scripts (see `bin/README.md`) |
| `aider` | aider config |
| `btop` / `micro` | system monitor / micro editor configs (each seeded from a tracked `*.example`; live file rewritten at runtime) |
| `secrets` | `.config/secrets/` — API-key manifest + README (values live in the macOS Keychain, not here) |
| `pnpm` | `Library/Preferences/pnpm/config.yaml` — supply-chain hardening (sibling `rc` = auth, machine-local) |
| `bun` | `.bunfig.toml` — supply-chain hardening |
| `uv` | `.config/uv/uv.toml` — supply-chain hardening (uvx reads it too) |
| `pip` | `.config/pip/pip.conf` — supply-chain hardening (pipx honors it) |

## NOT stow packages (in repo, wired differently)

| Dir | How it's wired | Why not stowed |
|---|---|---|
| `antigravity/` | `sync-from-claude.py` run manually (mirrors Claude config into `~/.gemini/config/`); IDE config copied in | agy's `~/.gemini/` mixes runtime state with config; the IDE atomic-saves `settings.json` (breaks symlinks) |
| `_scripts/` | invoked directly (`install.sh`, `verify-setup.sh`, `setup-devcontainer.sh`, Docker, pyexpat fix) | bootstrap/CI scripts |
| `_docs/` | reference docs + templates (read/copied manually) | documentation, not `$HOME` config |
| `_meta/` | machine-local planning scratch — gitignored (`_meta/*`) except the tracked planning desk `_meta/plans/` | local working desk, not config |

Underscore-prefixed dirs are internal, not stow packages. Consequence: a non-stowed dir's internal `bin/` would **never** be deployed to `~/.local/bin`.

## Machine-local & runtime files (gitignored / seeded, NOT symlinked into place)

Many live configs are machine-local because the app rewrites them at runtime (a stowed symlink would churn the repo). The pattern: the repo tracks a `*.example`, and `install.sh`'s `seed_local` copies it to a real file **before** the stow loop.

| Live file (machine-local) | Tracked seed |
|---|---|
| `~/.config/mise/config.toml` | `mise/.config/mise/config.toml.example` |
| `~/.claude/settings.json` | `claude-code/.claude/settings.json.example` |
| `~/.config/micro/settings.json`, `bindings.json` | `micro/.config/micro/*.example` |
| `~/.config/opencode/opencode.jsonc` | `opencode/.config/opencode/opencode.jsonc.example` |
| `~/.config/btop/btop.conf` | `btop/.config/btop/btop.conf.example` |
| `~/dotfiles/reminders/reminders.yaml` (repo-internal, gitignored) | `reminders/reminders.yaml.example` |

Also machine-local:
- `~/dotfiles/.env` → symlinked to `~/.env` by `install.sh` as a **backstop** (`.zshrc` sources it, then `secret export` from the Keychain wins). `.env.example` is the tracked template. API keys' real source of truth is the macOS Keychain via the `secret` CLI — see `references/ai-tooling.md`.
- `~/.zshrc.local` — machine-specific overrides, sourced at the end of `.zshrc` if present.
- `~/.npmrc` — machine-local, secret-free; NOT stowed (template is `.npmrc.example`). pnpm's auth `rc` is also machine-local.

## zsh loading order (`.zshrc` sources in this order)

1. `path.zsh` — PATH, `$DOTFILES` (`$HOME/dotfiles`), `NODE_OPTIONS="--max-old-space-size=4096"` (4 GB V8 heap cap, added after a 100 GB OOM crash), `MAILCHECK=0`
2. API keys — `~/.env` backstop (allexport), then `eval "$(secret export)"` from the macOS Keychain (Keychain wins)
3. `plugins.zsh` — zinit bootstrap, extra completions, **compinit** (exactly one daily-cached call: rebuild once/day, else `compinit -C`), fzf-tab, autosuggestions, syntax-highlighting
4. `aliases.zsh`
5. `functions.zsh` — includes the `agent` tmux launcher
6. `tools.zsh` — zoxide, fzf, **mise activate** (directory-based version switching)
7. `project-log.zsh` — chpwd hook logging git-repo entries (for `project-activity`)
8. `prompt.zsh` — Starship (last)
9. `~/.zshrc.local` if present

`.zshenv` (runs for ALL shells incl. non-interactive) adds **mise shims** to PATH so `node`/`python` work in scripts and Claude Code subshells.

## Runtimes — mise

`mise/.config/mise/config.toml` (live file; tracked seed is `config.toml.example`): `node = "26"`, `python = "3.14"`, `[settings] experimental = true`. mise replaces pyenv + NVM. Reads `.mise.toml`/`.nvmrc`/`.python-version` per-project. uv handles project venvs; mise handles the interpreter versions.

## Brewfile

`~/dotfiles/Brewfile` groups: Taps, Terminal & shell, Languages & runtimes (Node/Python NOT here — mise owns them), Package managers, Git TUIs, GitHub & dev tools, Azure, Google Cloud (gcloud installed via Google's installer, NOT brew cask — postinstall fragility), Media & documents, tmux session management, AI & deployment, Fonts, Apps. `brew bundle` re-syncs; `brewup` (a bin script) does the full update cycle. VS Code extensions split into `Brewfile.vscode`.

## install.sh bootstrap order

macOS-only (guards on `uname`). Broadly: `seed_local` (copy `*.example` → live machine-local files, before stow) → Homebrew → `brew bundle` → pyexpat fix (macOS 26+ workaround) → uv → uv tools (`aider-chat`, `ty`, `kokoro` with soundfile + a spaCy model) → pipx (`jupyter`) → mise (`python@3.14`, `node@26`) → gh-copilot extension → npm globals (`firebase-tools pnpm yarn nx`) → Google Cloud SDK → TPM → `~/Developer` → **stow all packages** (incl. `secrets`) → iTerm2 default profile → **launchd jobs are OPT-IN** (skipped unless `--with-launchd` or `DOTFILES_LAUNCHD=1`) → `.env` symlink → `verify-setup.sh`. Manual post-steps printed at the end (API keys via `secret`, Zed settings, tmux `Ctrl+a I`, npmrc token).

**launchd jobs (opt-in, `reminders/Library/LaunchAgents/`):** reminders 9am · tmux-cleanup 6pm · tool-updates 1st/15th 10am · **models-update** (`com.henry.models-update`, runs `models-dev --update` monthly). All four plists set PATH from the runtime `$HOME` (a fix so the reminders job stops silently failing when it shells out to a uv-based script).

## lint.sh — the pre-commit gate

`./lint.sh` (`--fix` to auto-fix ruff). Static analysis: zsh `-n`, shellcheck (incl. the repo-root `.claude/hooks/pre_stow_check`), ruff, yamllint, actionlint, plutil (the four plists), JSON validation, `stow --simulate` for all packages. New Python bin scripts → add to `PY_FILES`; new zsh scripts → add to the `zsh -n` loop. (The old deepagents/hooks test suites are gone with those packages.)

## Adding a new config package

```bash
mkdir -p ~/dotfiles/<package>/<path-relative-to-home>
command cp -r ~/.<config> ~/dotfiles/<package>/
cd ~/dotfiles && stow --ignore='.DS_Store' <package>
# add <package> to the stow loop in install.sh (and STOW_PACKAGES in lint.sh)
./lint.sh
```

## Linux/devcontainer path (not stow)

`_scripts/setup-devcontainer.sh` (curl-into-bash, or clone first) bootstraps Linux VMs (apt/dnf/apk). Flags: `--minimal`, `--ai-tools claude,opencode,aider,codex`, `--with-env`. Self-contained image in `_scripts/docker/Dockerfile` + `docker-compose.yml`. Verified by `_scripts/docker/verify-docker-build.sh`.
