---
type: C4 System
title: Agent harness output
description: Ledger and trial logs the agent harness writes
status: stable
groma:
  id: agent-harness-output
  technology: JSON Lines and log files
---

Read through `--ledger` and `--runs-dir`, never written: one JSON Lines ledger row per trial and one raw CLI log per trial (claude stream-json, opencode or codex JSONL). The harness produces these files and never calls evals.
