---
type: C4 Container
title: Campaign logs
description: Console transcript of each campaign
status: stable
groma:
  id: campaign-logs
  parent: harness
  technology: log files
---

Everything a campaign prints is appended to `<dir of --results>/campaign-logs/<label>.log`, so a same-day rerun appends to the same file. Git-ignored.
