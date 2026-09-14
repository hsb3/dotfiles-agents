# tui-craft

Design, build, test, debug, and retrofit terminal UI apps — the layering, state ownership,
streaming and repaint discipline, terminal-capability handling, and key routing that a
full-screen or text-mode app needs before the first widget is drawn.

## When it triggers

Reach for it when deciding whether something should be a TUI at all, starting a new one,
inheriting one you didn't write, building a terminal chat or agent client, or debugging a
specific symptom: flicker, tearing, resize corruption, broken copy-paste, terminal state left
wrong after exit or crash, or slow output with long content. It also triggers on any TUI
framework or terminal primitive by name (Textual, Rich, Ratatui, crossterm, Bubble Tea,
Lipgloss, OpenTUI, Ink, prompt_toolkit, curses, ncurses, notcurses, tview, tcell, blessed,
alternate screen, raw mode, ANSI escapes). Not for ordinary CLI work or browser-based
terminal emulators.

`SKILL.md` is the router; the depth lives in `references/` — build-order, laws, interaction,
streaming, terminal, retrofit, and hard-facts.

## Install

```
claude plugin install solo-skills@dotfiles-agents
```

Ships in the `solo-skills` bundle.
