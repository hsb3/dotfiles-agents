# live-worker-git-guard

Refuses a **mutating git command while this session still has delegations running**.
`PreToolUse` on `Bash`: if the command contains `git commit`, `push`, `merge`, `pull`, `rebase`,
`checkout`, `switch`, `stash`, `reset`, `cherry-pick`, `revert`, `clean`, `restore`, `am` or
`apply`, and any subagent this session started has not settled, the call is denied and the deny
text names the agents to wait for.

Read-only git never fires — `status`, `diff`, `log`, `show`, `branch`, `rev-list`, `rev-parse`,
`ls-files`, `fetch` are how a session orients — and the read-only forms of the verbs above
(`stash list`, `stash show`, `apply --check`) are reads too.

## Why

Two losses, both observed, neither needing bad judgement. A root session polling for a green test
suite committed a tree a builder had temporarily broken mid-sweep. A routine post-merge
`git checkout dev && git pull --ff-only` autostashed five uncommitted files out from under a live
manager: `Created autostash` / `Applied autostash.` reads identically whether or not it raced, so
a loss leaves no artifact to check afterwards.

The narrow-path discipline that works for a commit (stage explicit paths, never `git add -A`) has
no equivalent for a pull — there is no way to fast-forward "only these paths". The only safe
answers are to wait, or to work from a separate worktree. A local `rebase.autoStash=false` was
tried first; it refuses unconditionally, does not travel to a fresh clone, and explains nothing,
which is why the guard is a hook that names the live workers instead of a config that merely
refuses.

## What it does not cover

The destructive-write case: a root session backing up, breaking and restoring a file a live
worker owns. Catching that needs an ownership registry mapping briefs to paths, and briefs are
prose — the registry does not exist. **Worktree isolation covers it by construction** (`isolate:`
in `.claude/atelier.local.md`, the `worktree-isolation` hook): an agent with its own checkout
cannot be hurt by anything done in this tree, which is also why this guard skips it.

## Who counts as live

The pending set comes from `hooks/_lib/pending.py`, shared with `subagent-telemetry` so the two
cannot disagree about who is live: the `agent-*.meta.json` sidecars in this session's
`subagents/` directory, minus every `agent_id` a bounded tail of the delegation ledger has
already settled.

Excluded: an agent whose sidecar carries `worktreePath`. Included: everything else, read-only
scouts too — a `checkout` or `pull` changes the tree a scout is reading mid-read.

The guard is not main-session-only. A manager holding live builders is the same hazard as a root
session holding them, and the deny text fits it unchanged. A delegating agent is excluded from
its own pending set, and an agent holding its own worktree is exempt entirely — it is not looking
at this tree.

## Override

```bash
ATELIER_GIT_GUARD_OVERRIDE=1 git commit -m "unrelated work"
```

The assignment must come **before** the `git` word; the same string as an argument is not an
override. The command goes through, and a `systemMessage` states that the override was used and
which agents are still live. Both the deny and the override are logged.

Do **not** `git stash` by hand to get around a deny. That reopens the exact window the guard
closes, and the work lands in a stash entry the agent will never look for. The deny text says so.

## Install

1. Copy this directory into `primitives-core/hooks/`.
2. Symlink it into the plugin assembly the way the other hooks are wired:
   `ln -s ../../../primitives-core/hooks/live-worker-git-guard plugins/atelier/hooks/live-worker-git-guard`
3. Add a roster row to `primitives-core.yaml` (id `live-worker-git-guard`, type `hook`, source
   `primitives-core/hooks/live-worker-git-guard`, origin `authored`, disposition `qualified`,
   targets `[claude-code]`).
4. Add the `PreToolUse` entry inside the **existing top-level `"hooks"` object** of
   `plugins/atelier/hooks/hooks.json` (wrapper shown for placement; do not add a second one):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/live-worker-git-guard/hook.py\"",
            "statusMessage": "Checking for live workers...",
            "timeout": 10,
            "type": "command"
          }
        ],
        "matcher": "Bash"
      }
    ]
  }
}
```

No activation file: the guard fires wherever the plugin is installed.

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `ATELIER_GIT_GUARD_OVERRIDE` | unset | `=1` as a command prefix allows one mutating call |
| `SUBAGENT_TELEMETRY_LOG_PATH` | `${XDG_DATA_HOME:-~/.local/share}/agent-logs/claude-code/atelier/delegation.jsonl` | The delegation ledger it reads to learn who settled |
| `SUBAGENT_TELEMETRY_TAIL_BYTES` | `262144` | Bounds how much of the delegation ledger's tail is read to compute the settled set |
| `LIVE_WORKER_GIT_GUARD_LOG_PATH` | `…/agent-logs/claude-code/atelier/live-worker-git-guard.jsonl` | Its own ledger |

## Design notes

- **Fail-open, always.** No `transcript_path`, no `subagents/` directory, an unreadable ledger, a
  malformed payload — every one exits 0 with no output. A guard that cannot read its own records
  has no grounds to block, and the session is left exactly as unguarded as it was before this hook
  existed.
- **An unreadable ledger is not an empty one.** `settled_ids` raises rather than returning an
  empty set, because rendering "cannot tell" as "nothing has settled" would deny on every agent
  the session ever started.
- **`git` only counts in command position** — first token, after a shell separator, or after an
  env assignment. `man git commit` and `which git` are not git calls. Quoted text is tokenized
  with `shlex`, so a git command mentioned inside a string is one token and cannot fire.
- **The override emits no `permissionDecision`.** `"allow"` would short-circuit every other
  permission check in the session; this hook's opinion is only about live workers.
- **A stale sidecar blocks until the ledger settles it.** There is no age threshold: an agent that
  died without a `SubagentStop` stays pending until a `stall` row names it. The override is the
  escape hatch, and the ledger row is the evidence if it turns out to be frequent.
- **A `/clear` mid-wave hides the live agent.** The re-homed session's `subagents/` directory
  holds the transcript, not the sidecar, so the started universe misses it and the guard goes
  quiet — the same asymmetry `subagent-telemetry` documents, and deliberately not widened here:
  scanning sibling session dirs would sweep in every historical delegation under the slug.

## Ledger

One row per **decision that reached the session** — a deny or an override, never one per Bash
call. Ledgers live outside the project, in the partitioned root shared with every other hook in
this plugin; the append path is `hooks/_lib/agentlog.py`.

```json
{"v":1,"plugin":"atelier","harness":"claude-code","stream":"live-worker-git-guard",
 "ts":"2026-09-02T15:37:08.666Z","project":"/repo/x","session_id":"...",
 "decision":"deny","verb":"pull","pending":["a31412cbc7cdb39e8"]}
```
