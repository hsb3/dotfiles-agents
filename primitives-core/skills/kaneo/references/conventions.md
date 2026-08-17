# Board conventions

One shape for every board in the workspace, so an agent that has read one can work
any of them. Deviating is fine when a project genuinely needs it — say so on the
board, don't leave it to be inferred.

## Lanes

Canonical order, left to right:

```
Documents · To Do · Up Next · In Progress · In Review · [Blocked] · Done
```

- **Documents leads and is `isFinal`.** It is the reference shelf — the handoff,
  decision records, worked examples. Nothing in it is work.
- **Done is `isFinal`.** Blocked is optional; add it only when tasks actually wait
  on someone.
- **Up Next is the queue.** Take the top of Up Next, not To Do — To Do is untriaged.

Reorder with `PUT /column/reorder/{projectId}` `{"columns":[{"id","position"}]}`.

**Never guess a status slug from a lane name.** They drift independently: one board's
lane is named `Documents` with slug `decisions`, another is named `Document` with slug
`documents`. Read `GET /column/{projectId}`, match on **name**, and write the `slug` you
read back. A guessed slug writes a task into a lane that does not exist.

## The handoff

Exactly one live handoff per board:

- Title `HANDOFF — cold-start onboarding for <repo>`, label `HANDOFF`, parked in the
  Documents lane.
- **Kept current in place.** Never file a new one per session, and never create an
  in-repo `HANDOFF.md` — the board is the only copy.
- **It is not work.** Never claim it, never assign it, never move it out of Documents.
- Superseded handoffs move to Done rather than being deleted; the live one is the
  `HANDOFF`-labelled task outside Done.

Documents being `isFinal` is load-bearing: it is what stops a `<slug>-<number>` branch
push from dragging the handoff into In Progress. Park the handoff in a non-final lane
and that protection is gone.

## Decisions

Label `DECISION` (uppercase — a lowercase `decision` exists in some palettes and is not
what these carry). Documents lane, description as Context / Decision / Consequences,
approvals as comments. Check them before contradicting one. Never claim a decision task
to settle it yourself; that is the owner's.

## Labels

Labels are **workspace-scoped and shared across every board in it** — a palette entry
you do not recognise probably belongs to a sibling project. Check
`GET /label/workspace/{id}` for attachments before deleting anything.

Every task owns its own label row, so **match on name, never on id**. Attach with
`POST /label` including both `taskId` and `workspaceId`; `attach_label_to_task` *moves*
an existing row off whatever task was holding it.

## Branch names

`<project-slug>-<taskNumber>`, optional suffix that starts with a hyphen. Matching is
case-insensitive. Push → In Progress, PR open → In Review, merge → Done; protected
branches (main/master/develop/staging/production) are skipped and final-lane tasks are
left alone.

When the branch does **not** match, the server falls back to scanning the PR title for
`#N`, `[N]`, `(N)`, a leading `N:`, or `task N`, then the PR body for
`task`/`closes`/`fixes`/`resolves N` — and it cannot tell a task number from a GitHub
issue reference. A PR titled `fix the thing` with a GitHub issue number in parens on an
unmatched branch moves the task sharing that number. Name the branch correctly and the
fallback never runs.

## Reading back a write

`GET /task/export/{projectId}` can serve a stale copy immediately after a status write —
a move that succeeded will read as unmoved for a moment. It is also the only endpoint
that hydrates labels: `GET /task/{id}` returns `labels: []` even when the task has some.
Verify a write against `GET /column/{projectId}` plus a fresh export, and do not conclude
a write failed from one immediate read.
