# Shell integration and utilities

Shell integration teaches iTerm2 where each prompt begins and ends, which is the precondition for
a whole tier of features. Without it, iTerm2 behaves like an ordinary terminal.

## What it unlocks

- **Marks** — jump between prompts with `Cmd+Shift+Up`/`Down`; save and return with
  `Cmd+Shift+M` / `Cmd+Shift+J`.
- **Command metadata** — exit status, working directory, and runtime per command.
- **Select output of last command**, and click-a-command to restrict Find/Filter to it.
- **Command history and directory "frecency"**, per user+host, in the toolbelt.
- **Alerts** when a long-running command finishes.
- **Download/upload over ssh** — right-click a filename to scp it down; option-drag to upload.
- **Automatic profile switching** by hostname/username.
- **Captured Output** (needs command history, so it needs this).
- **Auto Composer**, the native text view for the prompt.

## Installing it

The advertised installer is:

```bash
curl -L https://iterm2.com/shell_integration/install_shell_integration.sh | bash
```

It appends a source line to the user's shell rc file. **That is the wrong move on a
symlink-managed dotfiles setup** — `~/.zshrc` is typically a symlink into the tracked repo, so the
installer dirties the repo and duplicates a line the repo may already have.

Prefer fetching the script directly and letting the repo's own rc own the sourcing:

```bash
curl -fsSL https://iterm2.com/shell_integration/zsh -o ~/.iterm2_shell_integration.zsh
```

with this already in the tracked rc:

```zsh
[[ "$TERM_PROGRAM" == "iTerm.app" && -f "$HOME/.iterm2_shell_integration.zsh" ]] \
  && source "$HOME/.iterm2_shell_integration.zsh"
```

Note the failure mode this guard creates: if the file was never downloaded, the guard makes the
whole thing a silent no-op. Nothing errors, and every dependent feature is simply missing. When a
user reports that marks or command history "don't work", check that the file exists before
anything else.

## Verifying

The script is wrapped in `if [[ -o interactive ]]`, so it defines nothing in a non-interactive
shell — `zsh -c '...'` will always look like a failure. Test with an interactive shell:

```bash
zsh -i -c 'echo $ITERM_SHELL_INTEGRATION_INSTALLED'   # -> Yes
```

A working session also emits `RemoteHost`, `CurrentDir`, and `ShellIntegrationVersion` escape
sequences at startup.

## Utilities

The utilities package normally installs to `~/.iterm2/` with aliases appended to the integration
script. They also ship inside the app bundle at
`/Applications/iTerm.app/Contents/Resources/utilities/`, which iTerm2 puts on `PATH` for its own
sessions — so they often work without installing anything.

| Tool | Purpose |
|---|---|
| `imgcat file` | Render an image inline in the terminal (any format, including animated GIF) |
| `imgls` | `ls` with inline image thumbnails |
| `it2copy` | Copy to the local pasteboard, **works over ssh** (needs "Applications in terminal may access clipboard") |
| `it2dl` / `it2ul` | Download to `~/Downloads` / upload, over ssh |
| `it2attention` | Bounce the dock icon or fire a cursor animation when a long job ends |
| `it2check` | Exit 0 iff the terminal is iTerm2 — the right guard for rc files |
| `it2getvar` | Read a session variable, e.g. `it2getvar session.name` |
| `it2setcolor` | Set colors live: `it2setcolor fg fff`, or `it2setcolor preset 'Light Background'` |
| `it2universion` | Switch Unicode width tables (8 vs 9) for emoji alignment |

Escape codes cover the rest; e.g. clear captured output before a build with
`printf "\e]1337;ClearCapturedOutput\e\\"`.
