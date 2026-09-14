---
name: iterm2
description: >-
  Configure iTerm2 and exploit the features that distinguish it from other terminal emulators.
  Use for any iTerm2 request: "set iTerm2 as my default terminal", "change a profile or theme",
  "my iTerm setting keeps reverting", "add a dynamic profile", "version-control my iTerm config",
  "install shell integration", "set up triggers / status bar / hotkey window / badges / captured
  output", "why didn't my `defaults write` stick", or "what iTerm2 features am I not using".
  Covers the preferences model (why iTerm2 silently reverts scripted changes and how to write them
  safely), dynamic profiles, tracking the config in a dotfiles repo, shell integration and its
  utilities, the macOS default-terminal binding, and the power-feature catalog.
---

# iTerm2

Two things make iTerm2 unlike other terminals to automate: it keeps its **entire** configuration in
one plist that it rewrites from memory on quit, and its most valuable features are inert until
shell integration is installed. Most "my iTerm setting won't stick" problems are the first; most
"iTerm isn't better than Terminal.app" impressions are the second.

## The rule that governs every scripted change

**iTerm2 overwrites its preferences from memory when it quits.** Any `defaults write
com.googlecode.iterm2 …` made while iTerm2 is running is silently clobbered seconds later, when
the user quits. There is no error and no warning.

So: **quit iTerm2 before writing its preferences**, and guard every script that does so. Writing
prefs from a terminal running *inside* iTerm2 cannot work — run it from Terminal.app or another
emulator, or apply the change through the GUI.

Two traps sit inside that guard, both of which produce a check that silently reports the opposite
of the truth:

```bash
# WRONG on both counts.
if pgrep -xq iTerm2; then ...
```

- **`pgrep -x iTerm2` never matches.** pgrep compares against the full executable path
  (`/Applications/iTerm.app/Contents/MacOS/iTerm2`), so exact-match never fires. Plain
  `pgrep iTerm` is worse than useless: it matches the *helper* processes `iTermAI` and
  `iTermServer-<version>`, so it returns true when the app itself is closed.
- **`ps … | grep -q` under `set -o pipefail` returns 141.** `grep -q` exits at the first match,
  `ps` dies of SIGPIPE, and pipefail propagates it — so the guard reads "not running" exactly when
  it is running.

```bash
# RIGHT — capture, then substring-match. No pipeline, no SIGPIPE, no pgrep semantics.
iterm_running() {
  local procs; procs=$(ps -Ao comm=)
  [[ "$procs" == *"iTerm.app/Contents/MacOS/iTerm2"* ]]
}
```

## Route the request

| The request is to… | Read |
|---|---|
| Set profiles/themes, add a dynamic profile, fix a default profile that reverts | `references/configuration.md` |
| Track the whole iTerm2 config in a dotfiles repo | `references/configuration.md` (custom prefs folder) |
| Install shell integration, or use `imgcat`/`it2copy`/other utilities | `references/shell-integration.md` |
| Make iTerm2 the macOS default terminal | `references/default-terminal.md` |
| Set up triggers, status bar, hotkey window, badges, captured output, tmux integration | `references/features.md` |
| Find features the user isn't exploiting yet | `references/features.md` |

## Profiles, briefly

A **profile** is a named settings collection. **Dynamic profiles** are JSON files in
`~/Library/Application Support/iTerm2/DynamicProfiles/`, loaded automatically at launch — the right
way to keep profiles in a dotfiles repo, since they need no import step.

Two sharp edges: iTerm2 reads **every** file in that directory regardless of extension, so a
`.example` seed placed there loads as a second profiles file and triggers a duplicate-GUID warning;
keep seeds outside it. And a dynamic profile **cannot mark itself default** — the default lives in
the `Default Bookmark Guid` preference, which is subject to the clobber rule above.

## Close every change with verification

Reading a value back from `defaults` proves only what was written, not what iTerm2 will honor.

- Confirm the app is what the user thinks: `echo $ITERM_PROFILE` names the live profile.
- After a prefs change, relaunch iTerm2 and re-read — a value that survives a quit is a value that
  actually took.
- Shell integration is live when `ITERM_SHELL_INTEGRATION_INSTALLED=Yes` in a **new interactive**
  shell (the script no-ops in non-interactive shells, so `zsh -c` always looks like a failure).
