---
type: C4 Container
title: Run dirs
description: Ephemeral per-trial workspaces and per-run homes
status: stable
groma:
  id: run-dirs
  parent: harness
  technology: temp directories
---

One `harness-<harness>-<candidate>-<case>-<config>-<trial>-<random>/` directory per trial under the OS temp dir (honouring `$TMPDIR`). It holds `ws/`, the copy of the case fixture the agent works in, and every per-run home and config dir the injection writes into, so the owner's real home and config are never touched. Deleted after a passing trial, a skip row and a smoke run; kept after a failing trial, with `ws/` recorded in the row.
