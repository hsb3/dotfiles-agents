---
type: C4 Component
title: Performance View
description: Recorded runs, comparison, run evidence and campaigns
status: stable
groma:
  id: performance-view
  parent: toolbox-ui
  technology: React, Carbon, Carbon Charts
  code:
    - scanner: react
      file: ui/src/performance-view.tsx
    - scanner: typescript
      file: ui/src/performance-view.tsx
---

The Performance area. The runs list searches id, campaign, candidate, case, model and harness, filters by configuration (All, Baseline, With), sorts by record id in server order or by duration or cost ascending over every page on the client (unavailable last, ties by id), pages 25 or 50, and returns to page 1 when search, filter or sort change. A tray holds at most two selected runs, marking those off the current page. The comparison names the first failing eligibility reason, or for an eligible baseline and with-configuration pair shows the n=1 caveat, the differences and sources tables and one grouped bar chart per metric both runs have. A measurement shows only when the version 1 envelope marks it available and valid, formatted with its unit, else "Unavailable". Run detail shows the metrics, the record facts and raw disclosures, the evidence (artifacts the run owns or its events and tool calls link, deduplicated by sha256, with its completeness) opened through a file token, and the events and tool calls; "Return to runs" restores the list and its focus. Campaign search and detail cover eval runs with their facts, responses and assessments.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [ui/src/performance-view.tsx](../../../../../../ui/src/performance-view.tsx) | [ui/src/api.tsx](../../../../../../ui/src/api.tsx) | Reads runs, the comparison pair, evidence and campaigns | function call |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [ui/src/performance-view.tsx](../../../../../../ui/src/performance-view.tsx) | [ui/src/api.tsx](../../../../../../ui/src/api.tsx) | Calls imported functions: assessmentsQuery, expandedName, hashHref, isAbort, jsonText, orUnavailable, pageCount, pageSlice, searchFilter, statusOf, useClient, useLoad, useSearch; Renders imported components: DataRegion, PagedList, Pager, RecordRegion, SearchForm | typescript |
