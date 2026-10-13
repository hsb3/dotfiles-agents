---
type: C4 Component
title: Performance View
description: Recorded runs, comparison, run evidence and campaigns
status: draft
groma:
  id: performance-view
  parent: toolbox-ui
  technology: React, Carbon, Carbon Charts
  draft: v1
---

The Performance area: the runs list with search, configuration filter, client-side duration or cost sort and a two-run selection tray; the comparison of an eligible baseline and with-configuration pair (tables and grouped bar charts, n=1, no causal claim); run detail with metrics shown only when the measurement marks them available, the record, events, tool calls and evidence opened through a file token; and campaign search and detail over eval runs and their responses and assessments.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [performance-view](performance-view.md) | [api](api.md) | Reads runs and evidence | function call |
