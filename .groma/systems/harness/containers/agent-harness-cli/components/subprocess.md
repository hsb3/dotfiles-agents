---
type: C4 Component
title: Subprocess
description: Runs every child process isolated and under a timeout
status: draft
groma:
  id: subprocess
  parent: agent-harness-cli
  technology: TypeScript
  draft: v1
---

Spawns a list-form argv, never through a shell, with stdin from `/dev/null`, in its own process group. On timeout it SIGKILLs the whole group and keeps the stdout captured so far; it reports a missing executable distinctly. Agent CLIs, the grader, `check.py`, `--version` and codex plugin installs all run through it.
