---
id: decision-4
title: >-
  Keep Performance lists mounted under detail routes and restore focus after the
  shell
date: '2026-10-13 04:31'
status: accepted
---
## Context

The spec asks that "Return to runs" restore the runs list and its focus, that the two-run selection last until sign-out, and that the duration and cost sorts run on the client over every page. Run detail (`#performance?run=<id>`) and campaign detail (`#performance?campaign=<id>`) are hash routes of the same area. Unmounting the list for a detail would lose its search, filter, sort, page, page size and loaded rows, or need a separate store to rebuild them. The shell (TASK-9) also focuses the main region on every route change, and React runs a parent's effects after its children's, so a child that focuses a link in its own effect loses that focus to the shell.

## Decision

`PerformanceView` stays mounted for every Performance route (AreaView renders the same component type at the same position) and holds the selection. The runs list, the selection tray, the comparison and the campaign search stay mounted while a detail shows, inside a wrapper with the `hidden` attribute, so returning shows them exactly as they were with no new read. "Return to runs" and "Return to campaigns" record which run or campaign the reader came from and set the hash to `#performance`. An effect then focuses that row's "Inspect" link (or campaign link), or the list heading when the row is gone, in a zero-delay timeout, which runs after the shell's focus on the main region. Client-side sorts gather every page with 200 records per request, then sort and page in memory. Ending the session unmounts the shell, which clears the selection and the loaded rows.

## Consequences

A deep link to a detail also mounts the hidden lists, so it reads the first runs page and the campaigns in the background; Return is then instant. While a detail shows, the hidden lists keep their rows in memory. Focus restoration depends on the shell focusing the main region synchronously in its effect; if that moves to a later tick, the timeout here must move with it. A duration or cost sort over a very large runs collection reads every page before it shows anything.
