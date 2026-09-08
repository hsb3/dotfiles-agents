# branch-activity-surfacer

Warns a starting session that another session has been working the same branch, and names
**what changed** — the commit the tip moved to, who wrote it, and the merged PR that carried
it — instead of a bare "someone else is here". A session that plans against a base another
session already moved plans against a tree that no longer exists.

## Why

Two sessions on one branch is normal here: two Macs share this repo, a worker runs in a linked
worktree, and a merge on GitHub moves the tip with no local session involved at all. Nothing
told the next session about any of it. The first symptom is a rebase or a conflicting commit
against a base that was replaced hours ago.

The obvious mechanism — a pushed `coord/<date>` branch of marker commits — was rejected: it
needs network and push rights at every session start, pollutes the remote, needs a pruning job,
and only reports the sessions that remembered to push to it. This hook records locally and
derives the interesting half from git, which is why a move made on the other machine or by a
GitHub merge still shows up once this checkout has the commits.

## When it fires

`SessionStart`, on `startup`, `clear` and `resume`. Not on `compact` — context is already
present there, and a second warning about the same branch is noise. Subagent sessions are
skipped (`agent_type` present and not `main`): a worker inherits its dispatcher's branch by
construction, so it would warn about its own session every time.

It emits nothing at all unless a signal fires, and exits 0 on every path.

## The two signals

Both are computed against `prior` — the most recent ledger row for this repo and branch written
by a **different** `session_id`.

| Signal | Fires when | Reads as |
|---|---|---|
| `moved` | `prior`'s tip differs from the current tip | the old and new SHAs, the commits between them with their authors, and a merged PR carrying the new tip when one is found |
| `peer` | `prior` was written inside the TTL | that session's id, its age in minutes, and its cwd |

Both can fire at once. The repo key is `git rev-parse --git-common-dir`, so a main checkout and
its linked worktrees share **one** key and see each other's rows; the branch is part of the key,
so a worktree on another branch is correctly silent.

Deliberately silent: a detached HEAD (no branch to key on), an unborn branch, a cwd outside a
repository, and a repeat start from the same `session_id`.

## Activation

No per-project activation file. The hook is armed by being present in an installed plugin's
`hooks.json`, and it is inert wherever there is nothing to say.

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `BRANCH_ACTIVITY_PEER_TTL_SECONDS` | `3600` | How recent a prior session start has to be to count as a live peer. `0` disables the peer signal; `moved` is unaffected. |
| `BRANCH_ACTIVITY_MAX_BYTES` | `1048576` | How much of the ledger's tail is read. The ledger grows without bound; session start must not slow down with it. |
| `BRANCH_ACTIVITY_LOG_COMMITS` | `5` | Cap on the commits listed for a move. |
| `BRANCH_ACTIVITY_GH` | `1` | `0` turns the PR lookup off entirely, for an offline or `gh`-less machine that would rather not spend the subprocess. |
| `BRANCH_ACTIVITY_LOG_PATH` | `${XDG_DATA_HOME:-~/.local/share}/agent-logs/claude-code/atelier/branch-activity.jsonl` | Ledger |

## Install

```
claude plugin install atelier@dotfiles-agents
```

## Design notes

- **The ledger is read before this session's own row is appended**, and the row is appended
  last on every non-skipped path. The reverse order would make every session its own peer.
- **The prior row is chosen by `ts`**, which agentlog stamps as ISO-8601 Zulu and which
  therefore sorts lexically in the order it sorts chronologically. No re-parsing to order.
- **A corrupt ledger degrades to silence, not to a crash.** Unparseable lines are skipped, the
  partial line after a tail seek is dropped, and a row missing `head`, `ts` or `session_id` is
  ignored rather than half-read.
- **The PR clause is the only network path and it is fully optional.** It runs only when `gh` is
  on PATH and `BRANCH_ACTIVITY_GH` is not `0`, is capped at four seconds, and any non-zero exit,
  timeout, parse failure or empty result drops the clause silently. Offline, the warning simply
  arrives without it.
- **Attribution degrades in one more place**: if `prior`'s tip is not in this checkout (history
  rewritten, or the commits not fetched), the commit range cannot be listed, so the warning
  names both SHAs and says the range is unavailable rather than inventing one.
- **Fail-open.** Any internal error is logged as an `error` row and the hook exits 0 with no
  stdout. Session start is never allowed to break on this.
- **No global lock.** Two sessions starting in the same instant can each read a ledger without
  the other's row and both stay silent about each other. The cost is one missed warning in a
  race; a lock file on the session-start path is not worth it.

## Ledger

Rows are appended to the `branch-activity` stream by `hooks/_lib/agentlog.py`, in the
partitioned root every hook in this plugin shares:

```
${XDG_DATA_HOME:-~/.local/share}/agent-logs/<harness>/<plugin>/<stream>.jsonl
```

Every row carries the identity envelope — `v`, `plugin`, `harness`, `stream`, `ts` (ISO-8601
UTC), `project` — plus an `event` naming which of the three shapes it is (`session`, `skip`,
`error`). Only `session` rows are read back:

```json
{"v":1,"plugin":"atelier","harness":"claude-code","stream":"branch-activity",
 "ts":"2026-09-08T18:02:11.204Z","project":"/repo/x",
 "event":"session","repo":"/repo/x/.git","branch":"dev","head":"71b6d1f...",
 "session_id":"beta","source":"startup","cwd":"/repo/x",
 "surfaced":true,"signals":["moved","peer"]}
{"v":1,"plugin":"atelier","harness":"claude-code","stream":"branch-activity",
 "ts":"2026-09-08T18:02:11.204Z","project":"/repo/x",
 "event":"skip","session_id":"gamma","source":"compact",
 "surfaced":false,"reason":"source not eligible"}
```

The `skip` rows are what distinguishes "never fired" from "fired and had nothing to say" after
the fact.
