---
id: TASK-9
title: 'Toolbox UI: shell, sign-in, catalog and documentation'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:09'
updated_date: '2026-10-13 04:17'
labels: []
milestone: m-0
dependencies:
  - TASK-8
references:
  - toolbox-ui
  - main
  - app
  - api
  - catalog-view
  - documentation-view
  - browse-the-catalog-and-documentation
modified_files:
  - .groma/systems/evals/containers/toolbox-ui/components/api.md
  - .groma/systems/evals/containers/toolbox-ui/components/app.md
  - .groma/systems/evals/containers/toolbox-ui/components/catalog-view.md
  - .groma/systems/evals/containers/toolbox-ui/components/documentation-view.md
  - .groma/systems/evals/containers/toolbox-ui/components/main.md
  - .groma/systems/evals/containers/toolbox-ui/container.md
  - SOP-FEEDBACK.md
  - ui/src/main.tsx
  - >-
    .backlog/decisions/decision-3 -
    Cancel-UI-reads-with-tracked-AbortControllers-and-end-sessions-in-SDK-send-hooks.md
  - .groma/flows/browse-the-catalog-and-documentation.md
  - test/ui-api.test.ts
  - test/ui-views.test.tsx
  - ui/src/api.tsx
  - ui/src/app.tsx
  - ui/src/catalog-view.tsx
  - ui/src/documentation-view.tsx
  - ui/src/styles.scss
priority: high
type: feature
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Authenticated readers need a read-only browser view of the catalog and the stored documentation, served from pb_public. This slice builds the Carbon shell, the in-memory session, the shared data region and safe links, Home, Catalog and Documentation. Builds the app, api, catalog-view and documentation-view components and the toolbox-ui container.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Sign-in keeps the token in memory only, clears the password after each attempt, shows the documented failure messages and ends the session on Log out, JWT expiry or any 401; a deep link survives sign-in
- [x] #2 The shell has the documented header, caption, side navigation, skip link, breadcrumb, hash routes and Home cards
- [x] #3 Every data region shows exactly one of loading, access, error, empty or records with the documented texts; lists page 25 per page with named fields and id as the last sort key; filters use escaped parameters; superseded requests are cancelled
- [x] #4 Catalog and Documentation show the documented records, links and texts; record text renders as text and only safe URLs become links
- [x] #5 tsc covers ui/src and bun run build:ui produces ui/dist; logic is unit-tested without a browser
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun run build:ui && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. ui/src/api.tsx: in-memory PocketBase client (BaseAuthStore), sign-in messages, session end (log out, JWT exp timer and pre-send check, any 401 via afterSend), tracked AbortController cancellation, paged list reads with named fields and id last, pb.filter params, DataRegion, PagedList, RecordRegion, Pager, SearchForm, ExtenderList, safe URL helper, hash links.
2. ui/src/app.tsx: sign-in screen, Carbon shell (header, caption, Log out, side nav, skip link, breadcrumb), hash routes with params, focus on route change, Home cards, placeholders for Performance and Evaluations.
3. ui/src/catalog-view.tsx and ui/src/documentation-view.tsx per spec texts.
4. ui/src/main.tsx mounts App with ui/src/styles.scss (Carbon).
5. Tests: test/ui-api.test.ts (pure logic + real PocketBase client checks) and test/ui-views.test.tsx (static render).
6. Gate; groma scan, accept app/api/catalog-view/documentation-view/toolbox-ui, accept api -> pocketbase-service, author the component relations (accept refused: two scanners per .tsx), callback relations, flow; lint clean; decision-3; notes; finish; commit.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Exports of ui/src/api.tsx for TASK-10:
- client and session: `ToolboxClient` (`pb`, `signedIn`, `subscribe`, `isSignedIn`, `signIn(email, password)` -> `Notice | null`, `beginSession()`, `signOut()`, `track()`, `release()`, `inFlight`, `filter(expr, params)`, `list<T>(ListQuery, signal)`, `one<T>(collection, id, fields, signal, expand?)`, `get<T>(path, signal)`), `ClientProvider`, `useClient`, `Timers`, `ListQuery`, `PAGE_SIZE` (25), `sortWithIdLast`, `listOptions`, `tokenExpiry`, `statusOf`, `isAbort`, `signInFailure`, `Notice`, `SIGN_IN_REJECTED`, `SIGN_IN_UNAVAILABLE`.
- loads and regions: `Load<T>`, `Loader<T>`, `useLoad(load, deps)`, `runLoad`, `failureState`, `DataRegion` (props subject, state, isEmpty?, emptyText?, children), `RegionMessage`, `regionText`, `RegionKind`, `isEmptyData`, `PagedList<T>` (subject, label, query(client), deps, item, emptyText?; key it by the search round), `RecordRegion<T>` (subject, collection, id, fields, expand?, children).
- paging, search, links: `Pager` (label, page, totalPages, onPage, optional pageSize/pageSizes/onPageSize for 25 or 50), `pageCount`, `pageSlice`, `useSearch` (query, round, search), `SearchForm` (label, onSearch), `safeUrl`, `SafeLink` (url, label?, fallback?), `hashHref(area, params)`.
- extenders: `ExtenderList` (query, selected?), `ExtenderSummary`, `EXTENDER_LIST_FIELDS`, `extenderSearchFilter`, `extenderLabel`.
- app.tsx exports `AREAS`, `AREA_TITLES`, `Route`, `parseHash`, `routeKey`, `AreaView`, `AreaPlaceholder`, `ShellFrame`, `Home`, `SignIn`, `App`; TASK-10 replaces the `default:` placeholder branch of `AreaView` with its views (they receive `route.params`).

Product calls (the spec leaves these open):
- 401, 403 and 404 answers show the access state; other failures the error state; a cancelled read shows nothing new.
- Searches apply on submit (Search button or Enter), trimmed; "Reset search" clears the box and the search. The packaged search, the extender search and all three Catalog pagers reset on every search; distributions are not filtered by the search (the spec gives them no search expression), only their pager resets.
- "<slug> · <n> member record(s)" is rendered literally with "record(s)".
- Breadcrumb on Home is just "Home"; other areas "Home / <area>".
- An unknown hash fragment keeps the whole current route (area and parameters); the URL is not rewritten.
- Missing values read "<thing> unavailable": "Entry file unavailable", "Source unavailable", "Publisher kind unavailable", "Maintenance unavailable", "Role unavailable"; a reader file with no content shows "No stored content."; the detail heading is "Extender <id>" (the named fields carry no name); without a selection Documentation says "Choose an extender to read its documentation.".
- The reader files region shows "This metadata-only extender has no stored reader files." as its empty state.
- Performance and Evaluations show "<area> is not available in this build yet." until TASK-10.
- The password field is cleared when each attempt finishes; the session also ends at once if a fresh token is already expired.
- Safe links also refuse control characters anywhere and any "@" in the authority (e.g. "http://@host"); external links carry rel="noreferrer" and open in the same tab.

Evidence:
- `bunx tsc --noEmit && bun run build:ui && bun test` exit 0: tsc clean over src, test and ui/src; vite built ui/dist (index.html + assets, 0 *.map files); 149 pass, 0 fail across 12 files (61.8 s).
- test/ui-api.test.ts (22 tests): safe URLs; sort id last, named fields, requestKey null + signal; escaped pb.filter literals; paging; sign-in message mapping (400/401/403 vs others, unreachable server); BaseAuthStore (not LocalAuthStore); JWT exp timer with fake timers incl. >2^31 ms re-arm and already-expired token; signOut aborts tracked requests; superseded reads ignored; hash route parsing (unknown keeps current, params, round trip); catalog search, shape check and labels; against a real PocketBase: wrong then right sign-in, 25 per page, only named fields returned, case-insensitive escaped search, injection attempt returns 0, files by relpath, HTML body kept as data, catalog route parsed, sign-out cancels an in-flight read, a refused token gets 401 from the catalog route and ends the session.
- test/ui-views.test.tsx (15 tests, renderToStaticMarkup): each data region state with exact texts and only one state; records rendered as escaped text; SafeLink; pager; sign-in form with empty password; shell header "Toolbox", caption, Log out, side navigation order, skip link to #main-content, main tabindex -1, breadcrumb "Home Catalog"; Home texts and cards; placeholder for Evaluations; packaged matches 10 per page workflows first; extender details, source facts safe/unsafe URL, reader file disclosure.
- `groma scan`: matched 4 (app, api, catalog-view, documentation-view); `groma accept` app, api, catalog-view, documentation-view, toolbox-ui; `groma accept relation api pocketbase-service`; the six component relations were refused by accept ("<id> owns 2 files" / "not a draft relationship", react+typescript scanners list each .tsx twice), so each was authored with `groma add relation <files>` carrying the planned description and technology and the draft row removed with `groma remove relation`; added api -> catalog-view and api -> documentation-view (supplied callbacks); flow browse-the-catalog-and-documentation added; api and catalog-view overviews rewritten. app -> evaluations-view / performance-view and the TASK-10 view relations stay draft.
- Final `groma scan && groma lint`: created 0, refreshed 15, matched 0; "No findings" (33 elements, 47 relationships, 6 flows, 26 task references). The first lint flagged SourcePanel/ExtenderPanel as duplicates; refactored into the shared RecordRegion.
- decision-3 recorded; `backlog doctor` clean.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Built the Toolbox UI shell slice. ui/src/api.tsx holds the in-memory PocketBase client (BaseAuthStore, SDK auto-cancel off), sign-in with the documented messages, session end on Log out / JWT exp / any 401 with cancellation of tracked requests, paged named-field reads with id last and pb.filter parameters, and the shared pieces (DataRegion with the five exact states, PagedList, RecordRegion, Pager, SearchForm, ExtenderList, safeUrl/SafeLink, hashHref). ui/src/app.tsx renders sign-in and the Carbon shell (header, caption, Log out, collapsible side nav, skip link, breadcrumb, hash routes, main focus, deep links, Home cards, placeholders for Performance/Evaluations). catalog-view and documentation-view implement the spec texts; main.tsx mounts App with Carbon styles. Verified by the DoD gate (149 tests pass, build without source maps), 37 new UI tests incl. a live PocketBase run, and a clean groma scan/lint with the four ghosts and toolbox-ui accepted and a new flow.
<!-- SECTION:FINAL_SUMMARY:END -->
