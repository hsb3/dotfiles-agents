---
type: C4 Container
title: Trial logs
description: Per-run raw agent stdout under runs/
status: stable
groma:
  id: trial-logs
  parent: harness
  technology: log files
---

One file per agent run under `--runs-dir` (default `<pkg>/runs`, git-ignored, never deleted by the harness). A trial log starts with a `# preconditions:` header line followed by the agent's raw stdout; a smoke log is raw stdout with no header. Rows link to their log through `log_path`, relative to the ledger's directory.
