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

The optional `scripts/launchd.sh`, POSIX `sh`. `install <cases-dir> <candidates-root>` writes `~/Library/LaunchAgents/com.hsb3.agent-harness.campaign.plist` (runs `/bin/sh <pkg>/scripts/launchd.sh run <cases> <root>` in the package dir every Monday at 09:00, not at load, logging to `~/Library/Logs/agent-harness-campaign.{out,err}.log`), boots any loaded copy out, bootstraps it and prints the `launchctl kickstart -k` next step that approves a keychain prompt once. `uninstall` boots it out and deletes the plist; `status` prints the state, last exit and next fire lines or `agent not loaded`. `run` prepends the bun, local, Homebrew and `/usr/local` bin dirs to `PATH`, fills an unset `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` from `secret get` without printing it, runs the campaign with bun, posts an ok or failed notification through `osascript` and exits with the campaign's code.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [launchd-script](container.md) | [agent-harness-cli](../agent-harness-cli/container.md) | Runs the campaign | bun, argv |
