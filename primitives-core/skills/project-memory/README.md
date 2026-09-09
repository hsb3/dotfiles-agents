# project-memory

The memory taxonomy and the tooling that realizes it. Give a git repo its own tracked,
transferable auto-memory: by default a project's memory lands in a hidden machine-local
directory keyed to the folder's absolute path — it does not follow a clone and it breaks
when the folder moves. This skill points auto-memory at the repo's own `.claude/memory/`
instead, so a project's learnings live in the repo and travel with it.

## When it triggers

Use it for the reference question — where memory lives (global vs. project-level), memory
vs. rules vs. skills, and when a fact is worth promoting up a layer — as well as the
operational one: opting a repo into tracked in-repo memory ("set up project memory", "make
this repo's memory travel with it"), or recovering a project's memory after its folder was
renamed or moved ("my project memory disappeared after I moved the folder"). Two bundled,
pure-Python-3-stdlib scripts run from the repo root: `project_memory.py`
(init/status/path/list) wires and inspects a repo and never overwrites an existing memory
file; `migrate_memory.py` relocates memory — and optionally session transcripts — after a
move, previewing by default and copying only with `--apply`.

## Install

```
claude plugin install code-desk@dotfiles-agents
claude plugin install mise-en-place@dotfiles-agents
```

Ships inside the `code-desk` and `mise-en-place` bundles. `mise-en-place` carries it as a
hard dependency rather than a convenience: this skill owns the `MEM-xx` rows in
`references/checklist.md`, and that bundle's audit and scaffold both load the file off their
own plugin root and refuse to start without it. Issuing the pass/gap verdict over those rows is
not this skill's job. Needs only `python3` (stdlib) and `git`.
