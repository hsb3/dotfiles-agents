# branch-activity-surfacer

Warns a starting session that this branch has moved since anyone last looked, and names **what
changed** — the old and new tip, the commits between them with their authors, the merged PR that
carried them — instead of a bare "someone else is here". It also names the other sessions whose
processes are still alive on the branch. A session that plans against a base another session
already moved plans against a tree that no longer exists.

## Why

Two sessions on one branch is normal here: two Macs share this repo, a worker runs in a linked
worktree, and a merge on GitHub moves the tip with no local session involved at all. Nothing told
the next session about any of it. The first symptom is a rebase or a conflicting commit against a
base that was replaced hours ago.

The obvious mechanism — a pushed `coord/<date>` branch of marker commits — was rejected: it needs
network and push rights at every session start, pollutes the remote, needs a pruning job, and only
reports the sessions that remembered to push to it. This hook records locally and derives the
interesting half from git, which is why a move made on the other machine or by a GitHub merge
still shows up once this checkout has the commits.

## When it fires

`SessionStart`, on `startup`, `clear`, `resume` and `fork`. Not on `compact` — context is already
present there, and a second warning about the same branch is noise. Subagent sessions are skipped
(`agent_type` present and not `main`): a worker inherits its dispatcher's branch by construction,
so it would warn about its own session every time.

It emits nothing at all unless a signal fires, and exits 0 on every path.

## The two signals

They are keyed differently, on purpose, and may describe different prior rows.

| Signal | Compared against | Fires when | Reads as |
|---|---|---|---|
| `moved` | the most recent session row for this repo+branch, **from any session including this one** | that row's tip differs from the current tip | the old and new SHAs, the commits between them with their authors, a merged PR carrying the new tip when one is found, or — on a rewind — how many commits are gone |
| `peer` | the most recent row per **other** session | that session's owning process is still alive and it started inside the TTL | up to three sessions named, each with its age and cwd, plus a count when there are more |

`moved` deliberately does not filter by session. The question is "has the branch moved since
anyone last looked", and the peer that moved it usually restarts — recording the new tip — before
this session next starts, which would hide the move behind a session filter.

`peer` is keyed on the **owning `claude` process**, not on `session_id`. `/clear` mints a new
session id inside the same process (measured: 64 of 64 real `clear` events did), so a session_id
key reports the operator to themselves as a live peer. The hook walks up the process tree with
`ps` to find its owning `claude`, records that pid on each row, treats a row carrying its own pid
as the same session, and reports a peer only when `os.kill(pid, 0)` says that process still
exists.

Deliberately silent: a detached HEAD (no branch to key on), an unborn branch, a cwd outside a
repository, and any start where nothing changed and no other session is alive.

## Activation

No per-project activation file. The hook is armed by being present in an installed plugin's
`hooks.json`, and it is inert wherever there is nothing to say.

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `BRANCH_ACTIVITY_PEER_TTL_SECONDS` | `3600` | How recent another session's start must be to be reported as possibly live. `0` disables the peer signal; `moved` is unaffected. |
| `BRANCH_ACTIVITY_MAX_BYTES` | `1048576` | How much of the ledger's tail is read. The ledger grows without bound; session start must not slow down with it. |
| `BRANCH_ACTIVITY_LOG_COMMITS` | `5` | Cap on the commits listed for a move. |
| `BRANCH_ACTIVITY_GH` | `1` | `0` turns the PR lookup off entirely, for an offline or `gh`-less machine that would rather not spend the subprocess. |
| `BRANCH_ACTIVITY_OWNER_PID` | *(derived by walking up to the owning `claude`)* | Supplies the session-identity pid directly. For a harness that already knows it, and for tests, where every hook subprocess shares one parent and the walk would give them all the same owner. |
| `BRANCH_ACTIVITY_LOG_PATH` | `${XDG_DATA_HOME:-~/.local/share}/agent-logs/claude-code/atelier/branch-activity.jsonl` | Ledger |

## Install

```
claude plugin install atelier@dotfiles-agents
```

## Design notes

- **The ledger is read before this session's own row is appended**, and the row is appended last
  on every non-skipped path. The reverse order would make every session its own peer.
- **Rows are ordered by `ts`**, which agentlog stamps as ISO-8601 Zulu and which therefore sorts
  lexically in the order it sorts chronologically. A stamp with no zone is treated as unreadable
  rather than as a naive datetime: subtracting one raises, and fail-open would then swallow this
  session's own row, so a single bad line would disable the hook for that branch permanently.
- **The move is stated without attributing agency.** The ledger records that an earlier start saw
  a different tip, not who moved it — and since `moved` now compares against this session's own
  rows too, the "other session" often is you. Each commit line's author carries the attribution.
- **A corrupt ledger degrades to silence, not to a crash.** Unparseable lines are skipped, the
  partial line after a tail seek is dropped, and a row whose `head`, `ts` or `session_id` is
  missing or implausible is ignored rather than half-read.
- **The PR clause is the only network path and it is fully optional.** It runs only when `gh` is
  on PATH and `BRANCH_ACTIVITY_GH` is not `0`, is capped at four seconds, and any non-zero exit,
  timeout, parse failure or empty result drops the clause silently.
- **The timeout budget is bounded below the hook's own 20s timeout**: the pid walk is capped at
  8 hops and 1.5s total, each git call at 3s, `gh` at 4s. A hook killed on timeout never writes
  its row, which would make it invisible to the next session — the failure this exists to stop.
- **Fail-open.** Any internal error is logged as an `error` row and the hook exits 0 with no
  stdout. Session start is never allowed to break on this.

## Known limits

- **Pid reuse inside the TTL** can produce one spurious peer warning: a recycled pid answers
  `os.kill(pid, 0)`. The TTL is the second gate, and the cost is one wrong line, not a wrong
  action.
- **A session started on a detached HEAD records nothing**, so it is invisible to the next
  session — including mid-rebase and mid-bisect, exactly when a concurrent move hurts most.
  Keying such a session would mean inventing an identity for "no branch"; it was not worth it.
- **A row written before the lineage key existed carries no `owner_pid`**, so it falls back to
  `session_id` identity with no liveness check — old rows behave exactly as they used to.
- **Sessions running under different `XDG_DATA_HOME` values write different ledgers** and are
  mutually blind. Point `BRANCH_ACTIVITY_LOG_PATH` at one shared file if that is your setup.
- **No lock.** Two sessions starting in the same instant can each read a ledger without the
  other's row and both stay silent about each other. The cost is one missed warning in a race.

## Ledger

Rows are appended to the `branch-activity` stream by `hooks/_lib/agentlog.py`, in the partitioned
root every hook in this plugin shares:

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
 "session_id":"beta","owner_pid":4711,"source":"startup","cwd":"/repo/x",
 "surfaced":true,"signals":["moved","peer"]}
{"v":1,"plugin":"atelier","harness":"claude-code","stream":"branch-activity",
 "ts":"2026-09-08T18:02:11.204Z","project":"/repo/x",
 "event":"skip","session_id":"gamma","source":"compact",
 "surfaced":false,"reason":"source not eligible"}
```

The `skip` rows are what distinguishes "never fired" from "fired and had nothing to say" after
the fact, and their reasons are kept distinct — `not a git repository`, `git could not be run`,
`detached HEAD` and `no commits` are four different diagnoses, not one.

## Codex

Codex uses its own ledger harness label and follows the native Codex process ancestry for peer liveness. Existing Git branch/head comparisons and session sources are retained; activation is checked before emitting context.

Codex session IDs distinguish peers even when an app-server process hosts both sessions; the shared process ID supplies liveness, not session identity.
