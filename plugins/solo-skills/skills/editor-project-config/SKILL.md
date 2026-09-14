---
name: editor-project-config
description: >-
  Design the tracked per-repo editor configuration for VS Code (`.vscode/`) and Zed
  (`.zed/`) — settings overrides, extension recommendations, tasks, and debug configs
  that travel with the repo. Use when asked to "set up editor config for this project",
  "add a .vscode or .zed folder", "recommend extensions for this repo", "wire lint or
  tests into editor tasks", or when a repo's files open without syntax highlighting
  (extensionless scripts, odd filenames, JSONC named .json). Covers the surface map for
  both editors, the two association mechanisms (files.associations vs file_types),
  mirroring the repo's existing lint toolchain instead of inventing one, and keeping the
  two folders in parity.
---

# Editor project config — .vscode and .zed

Project-level editor config overrides user config and travels with the repo. Track both
folders in git; never put credentials in them (API-token settings, e.g. Zed
`context_servers`, belong in user-level config only).

## Surface map

| Concern | VS Code `.vscode/` | Zed `.zed/` |
|---|---|---|
| Settings overrides | `settings.json` | `settings.json` — global-only keys (theme, vim_mode, telemetry) are silently ignored at project level |
| Extension recommendations | `extensions.json` `{"recommendations": [...]}`, prompted on first open | none — Zed auto-installs language support |
| Tasks | `tasks.json` (`"version": "2.0.0"` + `tasks` array; parameterize with `inputs`/`pickString`) | `tasks.json` (flat array of `{label, command}`; `$ZED_FILE`, `$ZED_RELATIVE_FILE`, … are env vars in the task shell, so POSIX expansion like `${ZED_RELATIVE_FILE%%/*}` works) |
| Debug | `launch.json` (`"type": "debugpy"`, …) | `debug.json` (flat array; `"adapter": "Debugpy"`, `"CodeLLDB"`, …) |

Both editors parse all of these as JSONC. If the repo lints JSON strictly, write plain
JSON (both editors accept it) so the repo's existing linter covers the new files.

## Procedure

1. **Inventory the repo.** Languages present, plus everything an editor cannot identify
   by extension: extensionless executables (shebang scan:
   `for f in <bindir>/*; do head -1 "$f"; done`), tool-specific filenames (Brewfile,
   rc files), dialect mismatches (JSONC content in `.json` files, XML plists).
2. **Write associations in both editors.** VS Code `files.associations` maps glob →
   language id (`python`, `shellscript`, `javascript`, `ruby`, `xml`, `jsonc`); keys
   without `/` match basenames, keys with `/` match paths. Zed `file_types` inverts the
   map: language display name → glob list, and the names differ (`"Shell Script"`, not
   `shellscript`).
3. **Mirror the repo's toolchain, never invent one.** Point linter/formatter settings at
   the tools the repo's CI or lint script already runs, with the same flags (e.g.
   shellcheck severity). Where the repo does not format a language, disable
   format-on-save for that language only (VS Code `"[markdown]": {"editor.formatOnSave":
   false}`; Zed `languages.Markdown.format_on_save: "off"`) so saves cannot churn diffs.
4. **Tasks are the repo's canonical commands.** Lint, verify, build — verbatim from the
   repo's docs, not new inventions. Make the pre-commit check the default build task.
   Parameterize with VS Code `inputs`/`pickString`; in Zed, with shell expansion over
   `$ZED_*` variables.
5. **Recommend only toolchain extensions.** `extensions.json` carries what maps to the
   repo's linters/formatters; personal or global extensions stay in user config.
6. **Debug configs only where they work.** Scripts with inline dependency metadata
   (`uv run --script` shebangs) do not resolve their deps under a plain debugpy launch —
   note such limits rather than shipping configs that fail.
7. **Parity pass.** Every decision lands in both folders, or the gap is stated (e.g. Zed
   has no extension-recommendation surface).
8. **Verify live.** Open a formerly unidentified file in each editor and confirm
   highlighting; run at least one task from each.

## Gotchas

- Zed drops global-only settings in project files without any warning or error.
- Whitespace-trim / final-newline settings dirty vendored and generated files — scope
  them per-language or leave them off.
- VS Code `search.exclude` hides results from search only; Zed's nearest lever,
  `file_scan_exclusions`, also hides files from the project panel. Asymmetric — decide
  deliberately on each side.
