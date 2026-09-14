---
name: project-memory
description: >-
  The agent-memory taxonomy (layers, loading modes, memory vs rule vs skill, the birth rule) and
  the scripts that wire a repo for it or migrate it after a move. Use for "where does this
  memory go", "promote a memory", "run a curation pass", "memory vs rule vs skill", "set up
  project memory", "opt this repo into tracked memory", or "my project memory disappeared after
  I moved the folder".
---

# Project memory — taxonomy and tooling

**Codex scope:** this skill documents and configures Claude Code memory. Codex may use the
taxonomy or maintain an existing Claude setup, but `autoMemoryDirectory` and the migration
scripts do not configure native Codex memory. Do not run `init` merely to make Codex remember
something. Follow the consuming project's AGENTS.md memory instructions; native Codex memory
setup is outside this skill's supported scope.

Resolve `<plugin-root>` to the installed package directory containing this skill's `skills/`
parent, using the loaded skill's absolute path. Do not assume a shell variable is set by the
client. Substitute that absolute path in the commands below; both Claude Code and Codex can
run them from the target repository.

The **single consultable source** for where agent memory lives, how it moves, and how a
repo is wired to hold it. The first half is the memory taxonomy standard a session applies;
the second half is the two bundled scripts that realize its structural side. The system
*design* behind it — storage mechanics, loading semantics, settings precedence — is the
memory-standard technical design (`docs/design/memory-standard.md`); this content is the
standard a session applies plus the as-built tools, and it links to that design rather than
restating it.

Three consumers read this identical content: a human/agent session (you, now), the
repo-compliance-audit skill (checks structure against `references/checklist.md`), and the
owner at curation time.

---

## Part 1 — the taxonomy (where does this go)

| Question is about… | Read |
|---|---|
| The layers, loading modes, kinds, birth rule, promotion mechanism, v1 defaults | `references/taxonomy.md` |
| A specific compliance check, its `MEM-xx` ID, or its pass condition | `references/checklist.md` |
| The bundled scripts (and their machine-CLI equivalents) that opt a repo in or migrate it | `references/tooling.md` |

Answer from the reference content directly — do not reconstruct the taxonomy from memory or
from how some repo happens to look. The essentials:

- **Two layers.** *Global* memory lives in dotfiles-managed files symlinked into
  `~/.claude/` and travels via the dotfiles repo; *project* memory lives in each repo's
  **git-tracked** `.claude/memory/` and travels via the project repo. Both are plain
  markdown under version control — never hidden machine-local state.
- **Two loading modes.** The always-on `MEMORY.md` index (one line per topic file,
  `- [Title] → topic-file.md — hook` — a markdown link plus a short hook, loaded every
  session) vs situational topic files behind it
  (freeform, one theme each, pulled in only when relevant — the on-demand shape of a skill).
- **Three kinds.** *Memory* = facts / state / decisions-as-record; *rules* = path-scoped
  standing directives; *skills* = invocable procedures. Triage: is it a fact → memory; a
  directive tied to certain files → rule; a procedure you run → skill. Specs and decisions
  are none — they graduate to `docs/` / ADRs with at most a one-line pointer in memory.
- **Birth rule (one hot-path question).** *Secret / live-op?* (credentials, DSNs, live URLs)
  → `_meta/operations/`, untracked, **never memory**. Everything else → the project layer:
  write a topic file under `<repo>/.claude/memory/`, add one index line, commit with the
  repo. No global-vs-project agonizing at birth — curation routes a global-worthy fact later.
- **Promotion (at curation, never automatic).** When a project memory proves generalizable,
  distill it into the global layer and add its global index pointer **only if it fits the
  index cap** (prune/merge first if not), then prune the project copy.
- **v1 defaults (approved 2026-07-02).** Curation cadence is triggered by project boundaries
  (wrap-up / handoff), not a calendar; the always-loaded index is hard-capped at ~1 screen
  (~40 lines) with no cap on lazily-loaded topic files; the three-kinds triage above is the
  rule/skill/memory criterion.

## Error path — repo not opted in (read this before writing any memory)

If the current repo has **no git-tracked `.claude/memory/` with a `MEMORY.md` index**, the
structure this standard requires is missing. Do NOT silently fall back to Claude Code's
hidden machine-local default (`~/.claude/projects/<slug>/memory/`) — that is exactly the
invisible, non-portable state this standard eliminates. Instead:

1. **Name the gap to the user**: this repo is not opted into tracked project memory.
2. **Point at the fix**: run `project_memory.py init` in the repo (Part 2 below), or use the
   mise-en-place scaffold skill, then commit `.claude/memory/`.
3. If the session must proceed before the structure exists, **flag** that anything written
   meanwhile lands in the hidden default and should be migrated (`init --migrate`, or
   `migrate_memory.py`) once the repo is opted in.

---

## Part 2 — the tooling (wire a repo, recover after a move)

Two bundled, stdlib-only Python scripts realize the taxonomy's structural side. By default
Claude Code auto-memory lands in a hidden machine-local dir (`~/.claude/projects/<slug>/
memory/`) keyed to the folder's absolute path — it does not travel with a clone and it
breaks when the folder moves. These scripts point auto-memory at the repo's own tracked
`.claude/memory/` instead, and relocate it if the folder later moves. They are the only
supported path — see `references/tooling.md`.

### Wiring a repo (`project_memory.py`)

Run from the target repo's root. Inspect first, then apply:

```bash
# See how the current repo is configured (read-only)
python3 "<plugin-root>/skills/project-memory/scripts/project_memory.py" status

# Opt the repo in (writes settings.local.json + managed .gitignore block)
python3 "<plugin-root>/skills/project-memory/scripts/project_memory.py" init

# Opt in with a portable, committed setting and copy any hidden native memory into the repo
python3 "<plugin-root>/skills/project-memory/scripts/project_memory.py" init --portable --migrate
```

| Subcommand | What it does |
|---|---|
| `status` | Show the configured `autoMemoryDirectory`, whether it points in-repo, and whether a hidden native dir still holds files. Read-only. |
| `init` | Create `.claude/memory/` (+ a `MEMORY.md` index stub if absent), write `autoMemoryDirectory`, and add the managed `.gitignore` block. Idempotent; never overwrites an existing memory file. |
| `path` | Print the resolved memory directory for this repo (in-repo if configured, else the hidden native default). |
| `list` | List hidden native memory dirs that still hold files — migration candidates. Read-only. |

`init` flags: `--portable` (commit the setting via `settings.json` with a `~/`-relative
path, instead of an absolute path in machine-local `settings.local.json`; only valid when
the repo lives under `~/`); `--migrate` (copy files from the hidden native dir into the
repo, skipping any that already exist).

After `init`, accept the workspace-trust dialog for the folder so the setting is honored,
then commit `.claude/memory/` (and `.claude/settings.json` under `--portable`).

### Recovering memory after a folder move (`migrate_memory.py`)

When a project folder is renamed or moved, its memory is orphaned under the old
path-derived slug. This script copies it to the new location's slug. **It is dry-run by
default** — always preview, then re-run with `--apply`:

```bash
# List every project dir that still has a memory/ subdir
python3 "<plugin-root>/skills/project-memory/scripts/migrate_memory.py" --list

# Preview the move (writes nothing)
python3 "<plugin-root>/skills/project-memory/scripts/migrate_memory.py" /old/path /new/path

# Apply it, once the plan looks right
python3 "<plugin-root>/skills/project-memory/scripts/migrate_memory.py" /old/path /new/path --apply
```

Flags: `--apply` (do the copy — omit for a dry run); `--force` (overwrite files that
already exist at the destination — off by default, so existing files are skipped);
`--include-transcripts` (also copy `*.jsonl` session transcripts); `--remove-old` (after a
verified copy, delete the source `memory/` — refused if the source had a `MEMORY.md` index
but the destination does not); `--from-slug` / `--to-slug` (pass exact slugs to bypass path
derivation). Slugs are derived by replacing every non-alphanumeric character in the absolute
path with `-`; if a derived slug is not found, the script retries with the symlink-resolved
path and lists fuzzy candidates.

### Safety rules

- **Plan before you apply.** Run `status` / `--list` (read-only) and the migrate dry-run
  before any write. Present the plan, then apply.
- **Non-destructive by default.** `init` never overwrites an existing memory file; the
  migrate script never overwrites without `--force` and never deletes the source without
  `--remove-old` (and only after verifying the copy).
- **Both scripts are pure Python 3 stdlib** — run them with a plain `python3`, no install
  step.

---

## What this skill does NOT do

- **No memory system implementation** — storage, loading, and settings precedence are the
  memory-standard technical design; the bundled scripts wire and migrate structure, they do
  not implement the runtime.
- **No auditing** — this skill supplies the `MEM-xx` rows in `references/checklist.md` and
  stops there. Turning those rows into pass/gap verdicts is a compliance audit's job, and
  whichever bundle you have it from reads the checklist out of this skill's directory.
- **No content judgment** — the `MEM-xx` rows are structure-only; what a memory *says* is the
  owner's curation judgment, never a compliance surface.
- **No layout ownership** — that `.claude/memory/` appears in the repo layout at all is the
  repo-meta-structure standard's row (`CLAUDE-03` / `IGNORE-12`); everything memory-specific
  beyond placement is owned here.
- **No repo layout or scaffolding** — layout standards are repo-meta-structure, scaffolding is
  mise-en-place-scaffold.
- **No cross-harness memory rendering** — this standard is Claude Code-native; a memory
  equivalent for other harnesses is an open question owned by the translation service, and
  this content ships as ordinary skill text on all targets.

## For the audit (machine consumer)

- Checklist contract: `references/checklist.md` — a table `ID | Area | Check | Pass
  condition` with stable `MEM-xx` IDs, same contract as the repo-meta-structure checklist
  (closed check-type vocabulary; see the file's header). IDs are stable across skill renames.
- Locate this content from a sibling skill via the plugin root:
  `<plugin-root>/skills/project-memory/references/checklist.md`.
