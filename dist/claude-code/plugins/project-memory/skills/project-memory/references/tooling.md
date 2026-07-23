# Tooling — the as-built scripts

The tools that implement the taxonomy's structural side: opting a repo into tracked
project memory and relocating memory after a folder move. This skill **ships both as
bundled, stdlib-only Python scripts** under `scripts/`; run them with a plain `python3`,
no install step. This file points at the tools and states what each is for — the full
flag surface and the run recipes live in `SKILL.md`, and `--help` on each script is
authoritative.

## `project_memory.py` — opt a repo into tracked project memory

Run from the target repo's root:

| Subcommand | Does |
|---|---|
| `init [--portable] [--migrate]` | Creates `.claude/memory/MEMORY.md` (index stub) if absent; writes `autoMemoryDirectory` pointing in-repo (default: machine-local `settings.local.json` absolute path; `--portable`: a `~/`-relative path in tracked `settings.json`); adds a managed `.gitignore` block so `.claude/memory/` stays tracked. `--migrate` copies any hidden native memory dir into the repo. Never overwrites an existing memory file. |
| `status` | Shows how the current repo's memory is configured (read-only). |
| `path` | Prints the resolved memory dir for this repo. |
| `list` | Lists hidden native memory dirs that exist (migration candidates), read-only. |

After `init`, accept the workspace-trust dialog for the folder (a project-scope
`autoMemoryDirectory` is only honored after trust — the same gate that governs hooks),
then commit `.claude/memory/`.

## `migrate_memory.py` — relocated / renamed projects

For a project whose folder moved or was renamed: copies its Claude Code `memory/` (and,
with `--include-transcripts`, its `*.jsonl` transcripts) from the old path-derived slug to
the new one. **Dry-run by default** — supports `--list`, previews unless `--apply`, and
never deletes the source unless `--remove-old` (and only after the copy is verified).

## Machine-CLI equivalents (fully-provisioned dotfiles machine)

On a machine provisioned from the dotfiles repo, the same two tools are also exposed on
`PATH` as `cc-project-memory` (== `project_memory.py`) and `migrate-claude-memory`
(== `migrate_memory.py`). Prefer them by command name when they are installed; otherwise
run the bundled scripts. They implement the identical behavior.

## Not yet built

- **`cc-project-memory audit`** — the curation report named by the memory-standard
  technical design (oversized / stale / off-taxonomy / duplicate-of-global findings) is
  **not yet built**. Until it exists, curation passes are manual, run at the boundaries the
  v1 cadence default names (wrap-up / handoff).
