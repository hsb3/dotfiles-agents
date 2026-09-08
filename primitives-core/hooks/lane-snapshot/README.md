# lane-snapshot

Commits every agent worktree's working tree — tracked, untracked, staged, unstaged — to
`refs/lane-snapshots/<name>` every three minutes, so a worker's uncommitted output survives a
crash, a killed session, or a mistaken `git worktree remove`. A `SessionStart` hook starts one
daemon per repo; concurrent sessions share it.

Recover a file from a lane that is gone:

```sh
git show refs/lane-snapshots/<name>:<path>          # one file, as of the last snapshot
git ls-tree -r --name-only refs/lane-snapshots/<name>   # what the snapshot holds
git log --oneline refs/lane-snapshots/<name>       # the snapshot history for that lane
git restore --source refs/lane-snapshots/<name> -- .    # the whole tree, into your cwd
```

## Why

The delegation doctrine tells sessions to isolate workers in git worktrees and never prune a
locked one — because workers hold read-only git and their output stays uncommitted until
hand-over. Nothing shipped preserved that work, so every consuming repo hand-rolled it.

One that did lost a lane's work anyway. Its daemon carried a hardcoded absolute root pointing at
the repo's pre-rename path, so its worktree glob matched nothing and it took **zero** snapshots
for its entire life, silently: a failed glob and a healthy sleep loop are indistinguishable from
the outside. Three live worktrees were unprotected at the moment it was discovered.

Both halves of that failure are designed against here. The root is always derived, never
hardcoded, and a scan that matches no worktrees writes an explicit warning row rather than
looking identical to a working net.

## When it fires

`SessionStart`, every source (`startup`, `resume`, `clear`, `compact`). The hook resolves the
repo root, checks `pgrep` for a daemon already running against that same root, and launches one
only if there is none. It injects no context, never waits on the daemon, and exits 0 on every
path — including a failed launch. Session start is not allowed to get slower because of this.

The daemon then loops: one pass over every matching worktree, one `sleep`, repeat.

## Activation

No per-project activation file. The hook is armed by being present in an installed plugin's
`hooks.json`, and it is inert wherever there is nothing to protect:

- The session's `cwd` is not inside a git repository -> nothing launches.
- No worktree matches the glob -> the daemon runs and logs `"lanes": 0` with a `warning`, which
  is the whole point: silence would be a false all-clear.

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `LANE_SNAPSHOT_ROOT` | *(unset)* | Repo root to protect. Highest precedence; overrides what the hook derives. |
| `LANE_SNAPSHOT_INTERVAL` | `180` | Seconds between passes. Also sets the `--check` staleness threshold, at 2x. |
| `LANE_SNAPSHOT_WORKTREES` | `.claude/worktrees/agent-*` | Glob, relative to the root, naming the lanes to snapshot. |
| `LANE_SNAPSHOT_LOG_PATH` | `${XDG_DATA_HOME:-~/.local/share}/agent-logs/claude-code/atelier/lane-snapshot.jsonl` | Ledger |

The worktree glob is an override rather than a constant because a repo that parks its worktrees
somewhere else must not have to fork the hook to say so. That reach is deliberately not fenced —
worktrees legitimately live outside the repo — so the glob is joined onto the root and nothing
more: `../sibling-*` or an absolute pattern will snapshot directories outside the root, and their
refs still land in the root's `refs/lane-snapshots/` namespace. Set it to a path you meant.

### Root resolution, in precedence order

1. `$LANE_SNAPSHOT_ROOT`.
2. `argv[1]`, which the hook fills in from the `SessionStart` payload's `cwd`, resolved with
   `git rev-parse --show-toplevel`.
3. `git rev-parse --show-toplevel` run from the **daemon script's own directory**.

(3) is the mechanism this hook was specified around, and it is deliberately the *fallback*, not
the primary: shipped as a plugin, the script lives in the plugin cache under
`${CLAUDE_PLUGIN_ROOT}`, not inside the repo it is protecting, so its own location resolves to
the wrong repository or to none at all. It is correct and sufficient for a repo-local install,
where the script does sit in the tree it guards. What holds in all three cases is the property
that actually failed in the field: **no absolute path is ever hardcoded.** When nothing resolves,
the daemon refuses to run rather than guessing a tree.

## Install

Add the `SessionStart` entry inside the **existing top-level `"hooks"` object** of
`plugins/atelier/hooks/hooks.json` (wrapper shown for placement; do not add a second one):

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "command": "LANE_SNAPSHOT_INTERVAL=\"${LANE_SNAPSHOT_INTERVAL:-180}\" LANE_SNAPSHOT_WORKTREES=\"${LANE_SNAPSHOT_WORKTREES:-.claude/worktrees/agent-*}\" python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/lane-snapshot/hook.py\"",
            "statusMessage": "Starting the lane-snapshot daemon...",
            "timeout": 10,
            "type": "command"
          }
        ],
        "matcher": "*"
      }
    ]
  }
}
```

The daemon module `snapshot_lanes.py` ships beside `hook.py` in this directory and is launched by
path, so the directory symlink into the assembly carries both.

## Design notes

- **Pruning: adds only.** The daemon creates and fast-forwards refs; it never deletes one. A
  lane's ref outliving its worktree is not litter, it is the case recovery exists for — the
  origin story is auto-cleanup destroying work — and a snapshot commit chain over an idle lane
  costs nothing. Delete one by hand when you are sure:

  ```sh
  git update-ref -d refs/lane-snapshots/<name>
  ```

  `--check` lists refs whose worktree is gone so you know what is holding disk, and never fails
  on them.
- **The worktree is never modified.** `git add -A` runs against a scratch `GIT_INDEX_FILE` outside
  every worktree, keyed by a hash of the repo root so two repos with a same-named lane cannot
  collide. A live agent's own index and `git status` read exactly as they did before. The index
  file must not pre-exist — git rejects an empty one — so each pass unlinks it first and again in
  a `finally`.
- **A commit is written only when the tree hash actually changed.** Idle lanes cost one
  `write-tree` per pass and nothing else.
- **One failing lane never kills the daemon.** Every git call returns a code instead of raising,
  each lane is wrapped, and a bad pass is logged and slept off rather than ending the loop. The
  original was a `set -u`-only shell script for the same reason.
- **Snapshot commits carry a pinned identity** (`lane-snapshot@localhost`), which keeps them
  identifiable and, operationally, means `commit-tree` still works on a machine with no
  `user.email` configured.
- **`.gitignore` is respected**, because `git add -A` respects it. Work living only in ignored
  paths is not covered; that is the same limit a real commit has.
- **The `pgrep` guard is racy by construction.** Two sessions starting in the same instant can
  both see no daemon and both launch one. The cost is duplicate snapshot commits with identical
  content, which is why it was not worth a lock file. On a machine with no `pgrep` the hook
  launches unconditionally, for the same reason: a possible second daemon is the cheap failure,
  no daemon at all is the expensive one.

## Liveness

"Armed" and "actually snapshotting" must not be able to diverge quietly, so there are two checks
answering different questions.

**Did it run?** The ledger. The daemon writes a `start` row, a `snapshot` row per commit it
writes (so the first successful snapshot of a session is always on record), an `error` row per
failing lane, and a `scan` row per pass carrying the lane count — with an explicit `warning` when
that count is zero.

**Is it still working?** Doctor mode, which measures rather than assumes:

```sh
python3 hooks/lane-snapshot/snapshot_lanes.py --check [<root>]
```

Exit 0 when every live lane has a snapshot ref newer than 2x the interval. Exit 1 when a live
lane has no ref at all, when a ref is stale, or when the refs cannot be read — a gate that cannot
measure reports red, never green.

## Ledger

Rows are appended to the `lane-snapshot` stream by `hooks/_lib/agentlog.py`, in the partitioned
root every hook in this plugin shares:

```
${XDG_DATA_HOME:-~/.local/share}/agent-logs/<harness>/<plugin>/<stream>.jsonl
```

Every row carries the identity envelope — `v`, `plugin`, `harness`, `stream`, `ts` (ISO-8601
UTC), `project` — plus an `event` naming which of the five shapes it is (`hook`, `start`,
`snapshot`, `scan`, `error`):

```json
{"v":1,"plugin":"atelier","harness":"claude-code","stream":"lane-snapshot",
 "ts":"2026-09-08T04:22:55.765Z","project":"/repo/x",
 "event":"snapshot","lane":"agent-probe1",
 "ref":"refs/lane-snapshots/agent-probe1","commit":"cd6b9be..."}
{"v":1,"plugin":"atelier","harness":"claude-code","stream":"lane-snapshot",
 "ts":"2026-09-08T04:22:55.765Z","project":"/repo/x",
 "event":"scan","root":"/repo/x","lanes":0,
 "warning":"no worktrees matched .claude/worktrees/agent-* under /repo/x — snapshotting nothing"}
```

The `scan` rows are the dataset that answers "was the net ever actually up?" after the fact.
