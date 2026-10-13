---
type: C4 System
title: launchd
description: Scheduler that triggers the weekly campaign
status: stable
groma:
  id: launchd
  technology: macOS launchd
---

A user LaunchAgent (`com.hsb3.agent-harness.campaign`) fires every Monday at 09:00 and runs `scripts/launchd.sh run` with the cases directory and candidates root.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [launchd](launchd.md) | [launchd-script](../systems/harness/containers/launchd-script/container.md) | Triggers the weekly campaign | LaunchAgent plist |
