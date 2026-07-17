# Tooling — the as-built CLI

The commands that implement the taxonomy's structural side on a machine. Reference them by
command name (they are on `PATH`), never by filesystem path. This file points at the
tools; it does not re-document their flags — `--help` on each is authoritative.

## `cc-project-memory` — opt a repo into tracked project memory

| Command | Does |
|---|---|
| `cc-project-memory init [--portable] [--migrate]` | Creates `.claude/memory/MEMORY.md` (index stub) if absent; points the repo's `autoMemoryDirectory` at the tracked dir (default: machine-local `settings.local.json`; `--portable`: a `~/`-relative path in tracked `settings.json`); fixes `.gitignore` so `memory/` stays tracked. `--migrate` copies an existing hidden native memory dir into the repo. |
| `cc-project-memory status` | Shows how the current repo's memory is configured |
| `cc-project-memory path` | Prints the resolved memory dir for this repo |
| `cc-project-memory list` | Lists hidden native memory dirs that exist (migration candidates) |

After `init`, accept the workspace-trust dialog for the folder (a project-scope
`autoMemoryDirectory` is only honored after trust — the same gate that governs hooks),
then commit `.claude/memory/`.

## `migrate-claude-memory` — relocated projects

For a project whose folder moved or was renamed: migrates its Claude Code `memory/` to the
new slug. Supports `--list` and a dry-run-first flow.

## Not yet built

- **`cc-project-memory audit`** — the curation report named by the memory-standard
  technical design (oversized / stale / off-taxonomy / duplicate-of-global findings) is
  **not yet built**. Deferred to a follow-on engineering spec against the dotfiles repo.
  Until it exists, curation passes are manual, run at the boundaries the v1 cadence
  default names (wrap-up / handoff).
