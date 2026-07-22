---
name: project-memory
description: >-
  Opt a git repo into tracked, in-repo auto-memory, and recover a project's memory after
  its folder moves. Use whenever the ask is "set up project memory", "make this repo's
  memory travel with it", "opt this repo into tracked memory", "my project memory
  disappeared after I moved the folder", or "migrate my project memory". Wires a repo's own
  .claude/memory/ as the auto-memory directory by writing autoMemoryDirectory into the
  repo's settings, replacing the hidden machine-local default that does not follow a clone.
  Two bundled scripts, run from the repo root: project_memory.py init/status/path/list wires
  and inspects a repo; migrate_memory.py relocates memory (and optional transcripts) after a
  move, dry-run by default. Safe-by-default — the migrate script previews unless --apply, and
  the init script never overwrites existing memory files. Not for the memory taxonomy itself
  (what to store where) — that is the memory-taxonomy reference.
---

# Project memory

Give a git repo its own tracked, transferable auto-memory. By default, project memory
lands in a hidden machine-local directory (`~/.claude/projects/<slug>/memory/`) keyed to
the folder's absolute path — it does not travel with a clone and it breaks when the folder
moves. This skill points auto-memory at the repo's own `.claude/memory/` instead, so a
project's learnings live in the repo and move with it.

Two layers, kept separate: global/user memory stays at `~/.claude/memory/` (curated,
machine-wide); project memory lives in each repo's tracked `.claude/memory/`.

## The mechanism

Opting a repo in writes `autoMemoryDirectory` into that repo's settings, pointing at its
in-repo `.claude/memory/`:

- **default** — an absolute path in `.claude/settings.local.json` (machine-local, not
  committed). Re-run `init` on each machine to recreate the local path.
- **`--portable`** — a `~/`-relative path in the tracked `.claude/settings.json`, so the
  setting itself travels; only valid when the repo lives under the home directory.

`init` also adds a managed `.gitignore` block that keeps `.claude/memory/` (and other
`.claude/` content) tracked while ignoring machine-local/transient files
(`settings.local.json`, lock files, worktrees).

## Wiring a repo (project_memory.py)

Run from the target repo's root. Inspect first, then apply:

```bash
# See how the current repo is configured (read-only)
python3 "${CLAUDE_PLUGIN_ROOT}/skills/project-memory/scripts/project_memory.py" status

# Opt the repo in (writes settings.local.json + managed .gitignore block)
python3 "${CLAUDE_PLUGIN_ROOT}/skills/project-memory/scripts/project_memory.py" init

# Opt in with a portable, committed setting and copy any hidden native memory into the repo
python3 "${CLAUDE_PLUGIN_ROOT}/skills/project-memory/scripts/project_memory.py" init --portable --migrate
```

Subcommands:

| Command | What it does |
|---|---|
| `status` | Show the configured `autoMemoryDirectory`, whether it points in-repo, and whether a hidden native dir still holds files. Read-only. |
| `init` | Create `.claude/memory/` (+ a `MEMORY.md` index stub if absent), write `autoMemoryDirectory`, and add the managed `.gitignore` block. Idempotent; never overwrites an existing memory file. |
| `path` | Print the resolved memory directory for this repo (in-repo if configured, else the hidden native default). |
| `list` | List hidden native memory dirs that still hold files — migration candidates. Read-only. |

`init` flags: `--portable` (commit the setting via `settings.json` instead of
`settings.local.json`); `--migrate` (copy files from the hidden native dir into the repo,
skipping any that already exist).

After `init`, accept the workspace-trust dialog for the folder so the setting is honored,
then commit `.claude/memory/` (and `.claude/settings.json` under `--portable`).

## Recovering memory after a folder move (migrate_memory.py)

When a project folder is renamed or moved, its memory is orphaned under the old
path-derived slug. This script copies it to the new location's slug. **It is dry-run by
default** — always preview, then re-run with `--apply`:

```bash
# List every project dir that still has a memory/ subdir
python3 "${CLAUDE_PLUGIN_ROOT}/skills/project-memory/scripts/migrate_memory.py" --list

# Preview the move (writes nothing)
python3 "${CLAUDE_PLUGIN_ROOT}/skills/project-memory/scripts/migrate_memory.py" /old/path /new/path

# Apply it, once the plan looks right
python3 "${CLAUDE_PLUGIN_ROOT}/skills/project-memory/scripts/migrate_memory.py" /old/path /new/path --apply
```

Flags: `--apply` (do the copy — omit for a dry run); `--force` (overwrite files that
already exist at the destination — off by default, so existing files are skipped);
`--include-transcripts` (also copy `*.jsonl` session transcripts); `--remove-old` (after a
verified copy, delete the source memory/ — refused if the source had a `MEMORY.md` index
but the destination does not); `--from-slug` / `--to-slug` (pass exact slugs to bypass path
derivation). Slugs are derived by replacing every non-alphanumeric character in the absolute
path with `-`; if a derived slug is not found, the script retries with the symlink-resolved
path and lists fuzzy candidates.

## Safety rules

- **Plan before you apply.** Run `status` / `--list` (read-only) and the migrate dry-run
  before any write. Present the plan, then apply.
- **Non-destructive by default.** `init` never overwrites an existing memory file; the
  migrate script never overwrites without `--force` and never deletes the source without
  `--remove-old` (and only after verifying the copy).
- **Both scripts are pure Python 3 stdlib** — run them with a plain `python3`, no install
  step.
