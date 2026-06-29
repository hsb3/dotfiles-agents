# Shell customizations — aliases, functions, PATH, entry points

Authoritative sources: `~/dotfiles/zsh/.zsh/{aliases,functions,path,ai,tools}.zsh` and `zsh/README.md`. Shell is **zsh + zinit** (NOT oh-my-zsh); plugins lazy-load. Read the source files for exact definitions — this enumerates them with the gotchas attached.

## Dangerous aliases (the #1 gotcha for agents)

From `aliases.zsh`:

```sh
alias rm='rm -i'      alias cp='cp -i'      alias mv='mv -i'
```

In a **non-interactive Bash tool call** these prompt on overwrite/delete, then silently abort because stdin is closed. So a tool-call `rm`/`cp`/`mv` does nothing and you won't see why.

- `rm` → use **`rm -f`**.
- `cp`/`mv` → **bypass the alias with `command cp` / `command mv`**. Note: `cp -f` does NOT override `-i` on macOS.
- Restoring a file? Prefer the Edit/Write tools or `git restore` over `cp`.

Other behavior-changing aliases: `cat` → `bat --paging=never` (syntax-highlighted; `catp` for paged), `ls` → `eza --icons`, `ll` → `eza -la --icons --git`.

## Alias inventory (`aliases.zsh`)

| Group | Aliases |
|---|---|
| Git | `gs` `ga` `gc` `gp` `gl` `gd` `gb` `gco` `glog` (pretty graph log) |
| Docker | `d` `dc` `dcu` `dcd` `dps` `dlog` |
| uv | `uvs`=sync `uvi`=add `uvr`=run `uvl`=lock `ac`=`source .venv/bin/activate` |
| Navigation | `..` `...` `-`(cd -) `ls`/`ll` (eza) |
| File safety | `cp`/`mv`/`rm` → `-i` (see gotcha above) |
| bat | `cat`/`catp` |
| tmux | `mux`=`tmuxinator` |
| Reminders | `reminders`=`check-reminders list`, `reminders-run`=`check-reminders` |
| AI | `ask-aider`, `lg` (langrepl: sources `~/.langrepl/.env`), `dcode`, `da-hooks` |

## Shell-function entry points (defined as functions, not aliases)

`ccstatus` (in `aliases.zsh`) — Claude Code statusline control: `ccstatus` (status), `ccstatus signal|balanced|dashboard` (profile), `ccstatus theme auto|dark|light`.

`agent` (in `ai.zsh`) — opens **dcode** in a tmux split (chat pane left, exec pane right); creates a session if not already in tmux. Runs `source ~/.deepagents/load_env.sh && dcode`.

From `functions.zsh`:

| Function | What it does |
|---|---|
| `bg <cmd>` | run command in a new tmux window; macOS notification on finish |
| `proj <name>` | fuzzy-jump to `~/Developer/*<name>*` |
| `port <n>` / `killport <n>` | what's on a port / kill it |
| `mkcd <dir>` | mkdir -p + cd |
| `activate` | source nearest `.venv/bin/activate` |
| `timer <mins>` | countdown + notification + Glass sound |
| `todo [name]` / `daily` | dated note from a template, opens in VS Code (`code`) |
| `extract <file>` | unpack any archive format |
| `theme dark\|newspaper\|focus` | switch iTerm2 profile + retint tmux status bar |
| `rmproject <path>` | `rm -rf` + reminder to clear IDE caches |
| `dsh <container>` | shell into a running Docker container |

## Two aliases that load AI-agent env

```sh
alias dcode='source ~/.deepagents/load_env.sh && DEEPAGENTS_CODE_DEBUG=1 DEEPAGENTS_CODE_DEBUG_FILE=~/.deepagents/dcode-debug.log command dcode'
alias da-hooks='${DOTFILES:-$HOME/dotfiles}/deepagents_customizations/hooks_cli'
```

`dcode` loads API keys + debug env then runs the real `dcode` (`command` bypasses the alias). The comment notes deepagents-cli was removed 2026-06-06; the interactive agent is now dcode. `da-hooks` points straight at the (non-stowed) hooks CLI in `deepagents_customizations/`.

## PATH & environment (`path.zsh`)

- `export DOTFILES="$HOME/dotfiles"` (first — used by `check-reminders` and other scripts).
- PATH prepends: `/opt/homebrew/{bin,sbin}`, `~/.local/bin`, `~/bin`; conditionally openjdk, VS Code CLI, gcloud, `~/.opencode/bin`.
- **`NODE_OPTIONS="--max-old-space-size=4096"`** — caps V8 heap at 4 GB per process to stop runaway Claude Code / OpenCode / MCP sessions from exhausting RAM and crashing macOS (added after a 100 GB OOM crash from concurrent `claude --resume` sessions).
- `MAILCHECK=0`.
- Python/Node version strategy: **mise** for runtime versions (shims added in `.zshenv` so they work in non-interactive shells), **uv** for project venvs. pyenv/NVM removed.

## tmux (manual start)

Not auto-started. Start with `tmux` or `mux start default` (tmuxinator). Prefix **Ctrl+A**. Session picker `Ctrl+A o` (sessionx). `Ctrl+A r` reloads config. TPM plugins: resurrect, continuum, yank, sessionx. Layouts in `tmuxinator/.tmuxinator/` (`default`, `python-ai`, `fullstack`, `dotfiles`).
