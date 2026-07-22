# project-memory

Give a git repo its own tracked, transferable auto-memory. By default a project's memory
lands in a hidden machine-local directory keyed to the folder's absolute path — it does
not follow a clone and it breaks when the folder moves. This skill points auto-memory at
the repo's own `.claude/memory/` instead, so a project's learnings live in the repo and
travel with it.

## When it triggers

Use it to opt a repo into tracked in-repo memory ("set up project memory", "make this
repo's memory travel with it"), or to recover a project's memory after its folder was
renamed or moved ("my project memory disappeared after I moved the folder"). Two bundled,
pure-Python-3-stdlib scripts run from the repo root: `project_memory.py`
(init/status/path/list) wires and inspects a repo and never overwrites an existing memory
file; `migrate_memory.py` relocates memory — and optionally session transcripts — after a
move, previewing by default and copying only with `--apply`.

## Install

```
claude plugin install project-memory@dotfiles-agents
```

Also ships inside the `code-desk` bundle. Needs only `python3` (stdlib) and `git`.
