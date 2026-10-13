---
type: C4 Container
title: launchd script
description: Installs the weekly schedule and runs the campaign from launchd
status: stable
groma:
  id: launchd-script
  parent: harness
  technology: POSIX sh
---

The optional `scripts/launchd.sh`. `install` writes the `com.hsb3.agent-harness.campaign` LaunchAgent plist (Mondays 09:00) and bootstraps it; `uninstall` and `status` manage it; `run` sets up `PATH`, fills missing API keys from a `secret` command without printing them, runs `agent-harness campaign`, posts a notification and exits with the campaign's code.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [launchd-script](container.md) | [agent-harness-cli](../agent-harness-cli/container.md) | Runs the campaign | bun, argv |
