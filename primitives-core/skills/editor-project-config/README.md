# editor-project-config

Design a repo's tracked `.vscode/` and `.zed/` folders in one pass — file-type
associations for everything the editors cannot identify on their own, tasks wired to the
repo's real lint and build commands, extension recommendations that match its toolchain,
and debug configs only where they actually work — with the two folders kept in parity
instead of one drifting behind the other.

## When it triggers

Ask to "set up editor config for this project", "add a .vscode or .zed folder",
"recommend extensions for this repo", or "wire lint into editor tasks" — or point at a
file that opens without syntax highlighting (extensionless scripts, odd filenames).

## Install

```
claude plugin install editor-project-config@dotfiles-agents
```
