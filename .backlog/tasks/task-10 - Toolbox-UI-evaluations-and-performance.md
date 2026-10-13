---
id: TASK-10
title: 'Toolbox UI: evaluations and performance'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:09'
updated_date: '2026-10-13 04:34'
labels: []
milestone: m-0
dependencies:
  - TASK-9
references:
  - evaluations-view
  - performance-view
  - api
  - app
  - compare-two-runs
  - review-assessments-and-coverage
modified_files:
  - .groma/scanners.json
  - .groma/systems/evals/containers/toolbox-ui/components/api.md
  - .groma/systems/evals/containers/toolbox-ui/components/app.md
  - .groma/systems/evals/containers/toolbox-ui/components/documentation-view.md
  - .groma/systems/evals/containers/toolbox-ui/components/evaluations-view.md
  - .groma/systems/evals/containers/toolbox-ui/components/performance-view.md
  - SOP-FEEDBACK.md
  - test/ui-api.test.ts
  - test/ui-views.test.tsx
  - ui/src/api.tsx
  - ui/src/app.tsx
  - ui/src/documentation-view.tsx
  - ui/src/main.tsx
  - ui/src/styles.scss
  - >-
    .backlog/decisions/decision-4 -
    Keep-Performance-lists-mounted-under-detail-routes-and-restore-focus-after-the-shell.md
  - .groma/flows/compare-two-runs.md
  - .groma/flows/review-assessments-and-coverage.md
  - test/ui-evaluations.test.tsx
  - test/ui-performance.test.tsx
  - ui/src/evaluations-view.tsx
  - ui/src/performance-view.tsx
priority: high
type: feature
ordinal: 10000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Readers review current assessments and coverage, and compare one baseline with one with-configuration run on recorded evidence without overclaiming. This slice builds the Evaluations and Performance areas: runs list, selection, comparison and charts, run detail with token-gated evidence, and campaigns. Builds the evaluations-view and performance-view components.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Evaluations lists assessments (optionally per extender) and job coverage with the documented texts and links
- [x] #2 The runs list supports search, configuration filter, client-side duration/cost sort with unavailable last, 25 or 50 per page, and a selection tray of at most two
- [x] #3 Comparison eligibility returns the documented first failing reason; an eligible pair shows the n=1 caveat, the differences table, the sources table and a grouped bar chart per available metric
- [x] #4 Measurements show only when the v1 envelope marks them available and valid, formatted as specified; run detail, evidence via file token, events, tool calls and campaign detail follow the spec
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun run build:ui && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. ui/src/api.tsx: shared helpers both views need (orUnavailable moved from documentation-view, expandedName, jsonText, searchFilter, the assessments query) and ToolboxClient.fileToken.
2. ui/src/evaluations-view.tsx: assessments (named fields + expanded names, ?extender filter, by created, id last) and job coverage with the documented texts and links; pure label builders exported.
3. ui/src/performance-view.tsx: pure logic (measurement display and formatting, eligibility reasons, difference rows and percentages, chart data, client-side sort, runs filter, page gathering, evidence load/dedup/opener), the runs list with search/filter/sort/page size, selection tray, comparison tables and a GroupedBarChart per available metric, campaign search, run detail with evidence, events and tool calls, campaign detail; lists stay mounted under detail routes (decision-4).
4. ui/src/app.tsx renders both views with route.params; main.tsx imports the Carbon Charts styles; styles.scss adds table, facts and chart layout.
5. Tests: test/ui-performance.test.tsx (pure logic, static render, fake token server, live PocketBase) and test/ui-evaluations.test.tsx; ui-views placeholder test replaced.
6. Gate; groma scan, accept evaluations-view and performance-view, author the four planned relations by file pair and remove the draft rows, author api -> view callback relations, flows compare-two-runs and review-assessments-and-coverage, acknowledge the cross-container isObject duplicate, overviews; lint clean; decision-4; notes; finish; commit.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Product calls (the spec leaves these open):
- Missing values read "<thing> unavailable" with the thing capitalised: "Framework unavailable", "Element unavailable", "Extender name unavailable" (replaces "extender <name>"), "Assessor unavailable", "Evidence unavailable", "Eval run unavailable" (replaces "eval run <id>"), "Job name unavailable", "Status unavailable", "Disposition unavailable", "Rationale unavailable". Run metrics and other measured values read "Unavailable", as the spec words it.
- Evaluations with `?extender=<id>` says "Showing assessments for extender <id>." with a "Show all assessments" link. Job coverage is not filtered by extender (it has none), and is sorted by created then id. The job coverage eval run links to its campaign as well.
- Booleans (passed, skill_used) show "Yes"/"No". exit_code needs only to be an integer (negative signal codes stay visible); every other metric must be a finite non-negative number.
- Eligibility checks each identity field for missing, then mismatch, before moving to the next field (campaign, candidate, case, harness, model). The reason shows as "Reason: <code>" under the documented sentence.
- The differences table cells carry units ("1,466,021 ms"). The percentage is formatted like a number plus "%", and "Unavailable" unless baseline > 0. Charts cover the seven numeric run metrics (duration, cost, four token counts, turns), one GroupedBarChart each when both values are available. The table shows Duration and Cost as the spec lists.
- Runs list: changing the page size also returns to page 1. Client-side sorts gather every page, 200 per request. The tray entry is "<id> · <config> · <candidate>" with " (off page)", and a click removes it. Campaigns are "<slug> · <kind> · <status>", sorted by slug.
- Run detail: an empty object summarises as "0 entries". Preconditions summarise like checks (keys). Owned artifacts are listed by created, then linked ones in event/tool-call order. Sizes print as plain digits ("5001 bytes"). An artifact without a stored blob shows "Could not access evidence." with no token request. 401, 403 and 404 on the token request read "Access denied."; anything else reads "Could not access evidence.".
- "Open evidence" navigates the same tab (window.location.assign), as the spec says. Because the token lives in memory only, coming back means signing in again, and the deep link survives sign-in.
- Selection lives in PerformanceView. Sign-out unmounts the shell, which clears it. It survives moving to run or campaign detail and back.

Evidence:
- `bunx tsc --noEmit && bun run build:ui && bun test` run verbatim: exit 0. tsc clean. vite built ui/dist (Carbon chunk-size warning only). 185 pass, 0 fail across 14 files (62.5 s).
- test/ui-performance.test.tsx (26 tests): availability (version, available flag, negative, Infinity, wrong types, legacy envelope -> every metric Unavailable), booleans and integer exit_code, formatting (0.0005 -> "5.00e-4", -0.0005, 0.001, 1,466,021, 0.086, 1,234.568, units), eval-response availability. Every eligibility reason in order (select-exactly-two, duplicate-record, missing-/-mismatch for each field, configuration-mismatch, execution-invalid). Differences and percentage only when baseline > 0; chart data only when both values are available; ineligible text and reason. Eligible pair: caveat, both tables, 5 chart holders when cost and turns are unavailable on one side. Runs filter escaping; sort with unavailable last and id ties; client paging. Columns, hostile candidate `fixture-<img src=x onerror=alert(1)>` escaped, checkbox disabled at two; tray "(off page)" and count; the area and both details render (lists hidden). Run facts and disclosures; events and tool calls; evidence dedup, labels, completeness, URL and failure texts. A fake token server shows a newer click superseding the older one, plus the 403/500/no-blob messages. Against a real PocketBase: search over case, config filter, an injection attempt returning 0, duration sort over all pages, eligibility of the seeded pair, evidence (owned + linked via event and tool call), assessments with expanded names, the blob refused without a token and served (200, exact bytes) with the token from evidenceOpener.
- test/ui-evaluations.test.tsx (10 tests): named fields, by created, escaped extender filter, exact assessment and coverage lines, eval run link, missing values, hostile text escaped, filter notice.
- groma scan: matched 2 (evaluations-view, performance-view). groma accept for both. `groma accept relation app evaluations-view` was refused ("app owns 2 files"), and with file names ("not a draft relationship"), so the four planned relations were authored with `groma add relation <files>` carrying the planned description and technology, and the draft rows removed with `groma remove relation`. Also authored api -> evaluations-view and api -> performance-view (supplied callbacks). Flows compare-two-runs and review-assessments-and-coverage added. Overviews of api, app, evaluations-view and performance-view rewritten. The first lint flagged ui/src/performance-view.tsx#isObject as a duplicate of src/logs.ts#isObj (CLI vs browser bundle, which must not import each other), so it was acknowledged (.groma/scanners.json).
- Final `groma scan && groma lint`: created 0, refreshed 17, matched 0; "No findings" (33 elements, 49 relationships, 8 flows, 27 task references across 11 tasks).
- decision-4 recorded; `backlog doctor` clean.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Built the Toolbox UI Evaluations and Performance areas. ui/src/evaluations-view.tsx lists assessments (optionally per extender) and job coverage with the documented lines, eval runs linking to their campaigns. ui/src/performance-view.tsx has the runs list (escaped search, configuration filter, server id order or client-side duration/cost sort with unavailable last, 25/50 per page, reset to page 1), a two-run selection tray, comparison eligibility with the documented reasons, the n=1 caveat, differences and sources tables, and Carbon grouped bar charts. Measurements follow the v1 envelope and the number format. Run detail has metrics, record facts, disclosures, sha256-deduplicated evidence opened via POST /api/files/token, and events and tool calls. Campaign search and detail cover eval runs. Shared helpers (orUnavailable, expandedName, jsonText, searchFilter, the assessments query, fileToken) live in ui/src/api.tsx; app.tsx routes both views. Verified by the DoD gate (185 tests pass, incl. 36 new UI tests with a live PocketBase run and a fake token server) and a clean groma scan/lint with both ghosts accepted, the planned relations authored, two new flows and decision-4.
<!-- SECTION:FINAL_SUMMARY:END -->
