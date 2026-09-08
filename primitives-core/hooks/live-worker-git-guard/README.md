# live-worker-git-guard

Refuses a **mutating git command while this session still has delegations running**.
`PreToolUse` on `Bash`: if the command contains `git commit`, `push`, `merge`, `pull`, `rebase`,
`checkout`, `switch`, `stash`, `reset`, `cherry-pick`, `revert`, `clean`, `restore`, `am` or
`apply`, and a subagent this session started has not settled **and shares the working tree that
command targets**, the call is denied and the deny text names the agents to wait for.

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

## Which tree the command targets

Being live is only half the question; the other half is whether the command can reach them. The
pending set is keyed on the session's transcript, so on its own it says nothing about where a
command points: a session can hold workers in its own tree while a call runs in a checkout of a
different repo, where those workers have nothing to lose.

So the guard resolves both trees and compares them:

| side | how |
|---|---|
| the tree the command targets | `git rev-parse --show-toplevel` from the payload `cwd`, moved by any `-C` (cumulative, as git applies them) |
| the tree the workers occupy | the same resolution from `CLAUDE_PROJECT_DIR`, which Claude Code sets on the hook process to the session's **main checkout** |

Same tree, decide as before. Different trees, no block — a worker with no `worktreePath` sits in
the session's own tree, and that is the only sound proxy for where the workers are, because a
sidecar carries no per-worker `cwd`.

`--show-toplevel` and not `--git-common-dir`, deliberately: the hazard is a shared **working
tree**, not a shared repository. A sibling linked worktree of the same repo has its own working
tree and its own index, so a `commit` there stages only its own files and a `push` moves only
refs — neither takes a worker's uncommitted file off disk in the main checkout. Repo identity
would block a whole class of calls that cannot cause the loss.

**Ambiguity fails closed**, the one place this hook is not fail-open. These are the cases where
the guard *sees* a mutating call but cannot place it — what it does not see at all is a separate
section below. Each leaves it deciding exactly as it did before it could compare trees:

- no `git` binary, or a `cwd` that is missing, not a string, or outside any repository;
- an unset or non-repo `CLAUDE_PROJECT_DIR`;
- a `--git-dir` or `--work-tree` flag, which relocate the working tree by a rule the hook does not
  reimplement;
- `GIT_DIR`, `GIT_WORK_TREE` or `GIT_COMMON_DIR` assigned in the command line — the same
  relocation spelled as environment, which git honours identically;
- a `cd`, `pushd` or `popd` in command position before the `git` word, which makes the payload's
  `cwd` stale — bare, or under an exec wrapper (`command cd …`, `builtin cd …`, `eval cd …`);
- a wrapper option that moves the tree the git call runs in (`env -C DIR`, `sudo -D DIR`,
  `env -S`), per the section above.

The same rule a corrupt sidecar gets: a record that exists and cannot be read keeps its agent
live. `init` and `clone` are not mutating verbs, so making a repo in a fresh directory never
reaches the comparison.

## Exec wrappers and shell keywords

**A leading wrapper that execs the real command is stepped over**, and the command-position scan
resumes after it, for both the `git` word and the `cd`. Not for the adversarial case — an agent
that wants through has the override, which is cheaper and leaves a row — but for the honest one:
`time git push`, `timeout 60 git push` and `nice git commit` are things a session writes for real
reasons, and until this each lost its deny silently.

`env`, `command`, `builtin`, `eval`, `nice`, `time`, `xargs`, `timeout`, `sudo`, `nohup`,
`stdbuf`, `setsid`, chained (`nice time git commit`), and each in the `g`-prefixed coreutils
spelling Homebrew installs (`gtimeout`). Each wrapper's own options are skipped **with their
values**, so a value is never misread as the command word (`nice -n 10`, `xargs -I {}`,
`env -u NAME`, `sudo -u NAME`, GNU `time -o FILE`), and `timeout`'s bare positional duration is
skipped too.

**Shell grammar displaces the command word the same way, and is read the same way.** After `do`,
`then`, `else`, `elif`, `if`, `while`, `until` or `!`, the next word is a command, so
`for f in *; do git commit -m x; done`, `if true; then git commit; fi` and
`while git pull; do sleep 1; done` all deny — as does a keyword and a wrapper together
(`for f in *; do nice git commit; done`), and the cwd check sees a wrapped or keyword-preceded
`cd` (`for d in a b; do cd "$d" && git commit; done`). `for` and `in` are deliberately absent:
the word after them is a loop variable, not a command. The **verb** may carry a glued separator
(`while git pull; do`), which is stripped — that shape, and the plainer `git commit; ls`, were
missed before.

One accepted over-denial comes with this: a bare keyword sitting as an ARGUMENT immediately before
a git call — `echo do git commit` — denies, because telling that `do` is `echo`'s argument needs a
parser. A false deny costs one override; a miss costs a live worker's uncommitted files. A quoted
keyword is inert (`git commit -m "then git push"` denies on the real `commit`, never on the
string).

Two deliberate non-widenings. `command -v git` and `command -V git` are lookups, not calls — the
same exclusion `which git` already had. And a wrapper option that **relocates the tree** is
fail-closed, never skipped past: `env -C DIR`, `env --chdir=DIR`, `sudo -D DIR` and `env -S`
(which packs a shell string this tokenizer cannot read) make the target unknowable, which reads as
"shares the tree" and denies. A relocating option counts only on the wrapper chain that reaches
the `git` word: `env -C DIR true && git commit` aims `true`, not the git call.

## What it cannot see

Stated as a rule rather than a list, because a list of ways to hide a word invites the belief that
it is complete. **The `git` word and the `cd` are read only in command position** of the single
command string the hook is handed, so whatever still displaces them is invisible:

- an exec wrapper that is **not in the list above** — `flock`, `watch`, `parallel`, `script`,
  `arch`, `caffeinate`, and every site-local wrapper script;
- anything that re-parses a **string**, which is past a tokenizer by construction: `bash -c "..."`,
  a `$( )` substitution, a quoted `eval "cd x && git commit"`, `env -S 'git commit'`, and heredoc
  body text;
- a **command word** glued to a separator (`ls&&git commit`, `(git commit)`) — a glued wrapper
  option is fine (`nice -n10`, `env -uNAME`, `xargs -I%`), and a separator glued to the *verb*
  (`git pull;`) is stripped; it is only the command word the separator still hides;
- a `GIT_*` variable **exported by an earlier Bash call** — the same ceiling in another place, since
  it is not among this command's tokens at all.

Deliberately out of scope rather than missed: `ssh host git commit` and `docker run … git commit`
run in a different tree entirely, so silence is the correct answer.

None of these is the sanctioned bypass. The override is, and it leaves a row. Seeing through the
remaining ones means interpreting the command line rather than tokenizing it, which is a larger
change with its own over-denial surface.

## Override

```bash
ATELIER_GIT_GUARD_OVERRIDE=1 git commit -m "unrelated work"
```

The assignment must come **before** the `git` word; the same string as an argument is not an
override. The command goes through, and a `systemMessage` states that the override was used and
which agents are still live.

**Every use of the override is logged, including one that suppressed nothing.** A prefix on a
command the guard was not going to block (no live workers, or a different tree) prints no
`systemMessage` — there is nobody to name — but still writes its row, so reaching for the escape
hatch is visible afterwards rather than silent. An empty `pending` in the row is what separates
the two cases. A prefix on a command with no mutating verb writes nothing at all: the stream is a
record of contested commands, not of every Bash call.

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
| `ATELIER_GIT_GUARD_OVERRIDE` | unset | `=1` as a command prefix allows one mutating call, and is logged whether or not it suppressed a block |
| `CLAUDE_PROJECT_DIR` | set by Claude Code | The session's main checkout, resolved to the working tree the workers occupy. Unset or outside a repo, the tree comparison fails closed |
| `SUBAGENT_TELEMETRY_LOG_PATH` | `${XDG_DATA_HOME:-~/.local/share}/agent-logs/claude-code/atelier/delegation.jsonl` | The delegation ledger it reads to learn who settled |
| `SUBAGENT_TELEMETRY_TAIL_BYTES` | `262144` | Bounds how much of the delegation ledger's tail is read to compute the settled set |
| `LIVE_WORKER_GIT_GUARD_LOG_PATH` | `…/agent-logs/claude-code/atelier/live-worker-git-guard.jsonl` | Its own ledger |

## Design notes

- **Fail-open on an absent record.** No `transcript_path`, no `subagents/` directory, an
  unreadable ledger, a malformed payload — every one exits 0 with no output. A guard that cannot
  read its own records has no grounds to block, and the session is left exactly as unguarded as it
  was before this hook existed. **Fail-closed on an unreadable one**, in the two places a record
  exists and will not yield: a sidecar that does not parse, and a tree comparison that does not
  resolve.
- **An unreadable ledger is not an empty one.** `settled_ids` raises rather than returning an
  empty set, because rendering "cannot tell" as "nothing has settled" would deny on every agent
  the session ever started.
- **`git` only counts in command position** — first token, after a shell separator, after an
  env assignment, or after a leading exec wrapper and its options. `man git commit`,
  `which git` and `command -v git` are not git calls. Quoted text is tokenized with `shlex`, so a
  git command mentioned inside a string is one token and cannot fire.
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

One row per **decision that reached the session** — a deny or an override — plus one for an
override used where nothing was going to block, so no use of the escape hatch is silent. Never
one per Bash call. `pending` lists the live delegations sharing the tree the command targets, so
an empty list is an override that suppressed nothing. Ledgers live outside the project, in the
partitioned root shared with every other hook in this plugin; the append path is
`hooks/_lib/agentlog.py`.

```json
{"v":1,"plugin":"atelier","harness":"claude-code","stream":"live-worker-git-guard",
 "ts":"2026-09-02T15:37:08.666Z","project":"/repo/x","session_id":"...",
 "decision":"deny","verb":"pull","pending":["a31412cbc7cdb39e8"]}
```
