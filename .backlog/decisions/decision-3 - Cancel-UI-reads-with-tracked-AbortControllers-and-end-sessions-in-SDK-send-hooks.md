---
id: decision-3
title: >-
  Cancel UI reads with tracked AbortControllers and end sessions in SDK send
  hooks
date: '2026-10-13 04:15'
status: accepted
---
## Context

The Toolbox UI (SPEC.md, "Toolbox UI") must cancel a request superseded by navigation, paging or sign-out and ignore its answer, and must end the session on "Log out", when the token's JWT `exp` passes, and on any 401 answer. The PocketBase JS SDK 0.28.1 has its own auto-cancellation: a later request with the same automatic `requestKey` (method and path) cancels an earlier one. That key is per path, not per screen region, so two regions reading the same collection would cancel each other, and it does not cancel anything on sign-out. The SDK also offers `beforeSend`/`afterSend` hooks that see every request, including ones a future view issues directly (file tokens).

## Decision

- `ui/src/api.tsx` creates one client with `new PocketBase(window.location.origin, new BaseAuthStore())` and turns SDK auto-cancellation off (`autoCancellation(false)`, and `requestKey: null` on every call).
- Every read gets an `AbortController` from `ToolboxClient.track()`; its `signal` goes into the SDK options. `useLoad` aborts the previous controller when its inputs change or its region unmounts, and `runLoad` drops any answer or error once its controller is aborted. `signOut()` aborts every tracked controller, clears the in-memory token and the expiry timer.
- `afterSend` ends the session on any 401 answer while signed in (it runs before the SDK raises the error); `beforeSend` ends it when the token's `exp` has passed, in addition to a timer set at sign-in for the `exp` (re-armed in steps of at most 2^31-1 ms).
- 401, 403 and 404 answers show the access state of a region; any other failure the error state.

## Consequences

- Cancellation is per region and per session, independent of URL paths; views written later (TASK-10) get it by using `useLoad`, `PagedList` or `RecordRegion`.
- A 401 from any SDK call, including ones made outside `useLoad`, returns the reader to sign-in.
- A read cancelled by sign-out reports nothing, so no stale record reaches a new session.
- Requests sent without a tracked signal are not cancelled on sign-out; views must use the client's helpers.

