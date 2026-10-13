---
type: C4 Component
title: Subprocess
description: Runs every child process isolated and under a timeout
status: stable
groma:
  id: subprocess
  parent: agent-harness-cli
  technology: TypeScript
  code:
    - scanner: typescript
      file: src/subprocess.ts
---

Spawns a list-form argv, never through a shell, resolving the executable by bare name on the child's `PATH`, with stdin from `/dev/null`, `PWD` set to the child's cwd (opencode resolves its project directory from `PWD`, so an inherited one would point it outside the workspace), in its own process group. On timeout it SIGKILLs the whole group and keeps the stdout captured so far (exit code -1); after a normal exit it kills any stragglers left in the group so no process outlives a trial. It reports a missing executable distinctly. Agent CLIs, the grader, `check.py`, `--version` and codex plugin installs all run through it.
