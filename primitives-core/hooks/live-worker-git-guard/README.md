# live-worker-git-guard

Refuses a **mutating git command while this session still has delegations running**.
`PreToolUse` on `Bash`: if the command runs one of the verbs ruled *denied* in the table below
(`commit`, `push`, `pull`, `checkout`, `rm`, `bisect start`, `submodule update` and the rest),
and a subagent this session started has not settled **and shares the working tree that command
targets**, the call is denied and the deny text names the agents to wait for.

Read-only git never fires — `status`, `diff`, `log`, `show`, `branch`, `rev-list`, `rev-parse`,
`ls-files`, `fetch` are how a session orients — and so do the read-only forms of the denied verbs
(`stash list`, `apply --check`, `bisect log`, `submodule status`, `rm --dry-run`, and `--help`/
`-h` on any of them).

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

## The verb set, verb by verb

The set is ruled here rather than assembled by habit. It was widened once already, after a
review measured eight verbs that do exactly what this hook's first line describes passing
silently while a live worker shared the tree; what let them through was not disagreement but
**silence — an omission with no reason recorded reads exactly like an oversight**. So every row
below is a ruling, including every `not denied` one, and a verb cannot leave or enter the code
without its row moving with it (`tests/test_live_worker_git_guard.py`, `VerbRulingTableTests`,
pins this table to `MUTATING_VERBS` and `READ_FORMS` in both directions).

**The line is the hazard, not "writes something".** A verb is denied when it can

1. remove, overwrite or swap a tracked file in the working tree the command targets, as a whole
   or by pathspec; or
2. move the branch or `HEAD` that tree sits on; or
3. capture or publish that tree's half-finished state.

`--help` and `-h` are a read on every verb in the set, so they are not repeated per row. `bare`
in the reads column means the verb with no subcommand.

**A read form only counts as one when it is the call's own argument.** Three things are not:
anything past a `--`, where every token is a path and `git rm -- -n` deletes a file named `-n`;
anything past a shell separator, glued (`git submodule status|grep vendor`) or trailing, which
belongs to the next command; and the value of an option that takes one, so `git stash -m list`
is a stash with the message `list` and `git commit -m -h` is a commit with the message `-h`.
All three were measured passing silently against real git before they were closed.

| verb | ruling | reads that never fire | why |
|---|---|---|---|
| `add` | not denied | — | Writes the index only and takes nothing off disk. Every path from a dirty index to lost work runs through `commit`, `stash`, `reset` or `checkout`, each already denied, so denying the one call every commit sequence opens would cost a session more than it buys. Staging a worker's half-written file is recorded, not destroyed. |
| `am` | denied | — | Applies a patch series onto the working tree and moves the branch — a `merge` with a mailbox for a source. |
| `apply` | denied | `--check`, `--stat`, `--numstat`, `--summary` | Writes every file the patch names, over whatever a worker has there. |
| `bisect` | denied | `bare`, `log`, `view`, `visualize`, `terms`, `help` | `start`, `good`, `bad`, `new`, `old`, `skip`, `next`, `reset`, `replay` and `run` each check out another commit: the whole tree swaps under the workers, which is `checkout` by another name. |
| `branch` | not denied | — | `-f`, `-d`, `-D` and `-m` write a ref, but a ref move takes no file off disk, and telling them from bare `git branch` — the session's commonest ref read — needs the per-verb flag parser this guard refuses to build. Orientation has to stay cheap or the guard is what gets turned off. |
| `checkout` | denied | — | Replaces tracked files wholesale from another commit or from the index. |
| `checkout-index` | denied | — | `-a -f` writes the index's copy over every tracked file: `restore` in plumbing, with no orientation form to protect. |
| `cherry-pick` | denied | — | Applies a commit onto the working tree and moves the branch. |
| `clean` | denied | — | Deletes untracked files, which is most of what a worker has not committed yet. |
| `commit` | denied | — | Records the shared tree's half-applied edits as finished work — one of the two losses that produced this hook. |
| `config` | not denied | — | Writes `.git/config`, never tracked content or a ref a worker stands on. |
| `fetch` | not denied | — | Moves no tracked file and no local branch; it is how a session finds out what it is behind. |
| `filter-branch` | not denied | — | Refuses to run on a dirty tree, which is the only state this guard ever fires in, so it declines itself in exactly the case that matters. |
| `gc`, `prune`, `repack`, `maintenance` | not denied | — | Object database only: no tracked file changes and no ref moves. `gc --prune=now` can drop an unreachable object, which is admitted below. |
| `init`, `clone` | not denied | — | Create a repository in a fresh directory; nothing that already exists is touched, so neither ever reaches the tree comparison. |
| `merge` | denied | — | Writes the tree and moves the branch, and its conflict state strands whatever a worker had in flight. |
| `merge-file`, `mergetool`, `rerere`, `merge-index` | not denied | — | They write files named on the command line, or files already in conflict — the destructive-write case this hook has always left to worktree isolation ("What it does not cover"). `git merge-file` is not even a repository operation: measured 2026-09-08, it overwrote its first argument in a directory with no `.git` at all. |
| `mv` | denied | `--dry-run`, `-n` | Renames a working-tree file out from under whoever has it open, and stages the rename. |
| `notes` | not denied | — | Writes a `refs/notes/*` ref and nothing else: no index entry, no working-tree file. |
| `pull` | denied | — | `fetch` plus `merge`/`rebase`, and its autostash is the loss this hook was built for: `Created autostash` reads identically whether or not it raced. |
| `push` | denied | — | Publishes the shared tree's half-finished state as the branch everyone else builds on. |
| `read-tree` | denied | `--dry-run`, `-n` | `-u` writes the index's tree over the working tree. The index-only form is not carved out, for the same reason `rm --cached` is not. |
| `rebase` | denied | — | Rewrites the branch and rewrites the tree at every step, autostashing on the way in. |
| `reflog` | not denied | — | Reflog storage only, and `reflog show` is the recovery path a blocked session reaches for first. |
| `remote` | not denied | — | `add`, `set-url` and `prune` touch config and remote-tracking refs; `remote -v` is orientation. Nothing here reaches the working tree. |
| `reset` | denied | — | `--hard` discards the tree outright, and every form moves the branch a worker's next commit builds on. |
| `restore` | denied | — | Overwrites tracked files from the index or a commit, by pathspec. |
| `revert` | denied | — | Applies an inverse commit onto the working tree and commits it. |
| `rm` | denied | `--dry-run`, `-n` | Deletes working-tree files by default. Denied in **all** forms, `--cached` included: carving out the index-only one would make the guard parse flags to decide that a milder mutation is acceptable, and the flag it would have to trust sits one word away from the destructive spelling. |
| `send-pack`, `fast-import` | not denied | — | Plumbing that moves objects and refs and takes nothing off disk here. `push` is in the set for the half-finished state it publishes, and that state is a `commit` this guard already denied. |
| `sparse-checkout` | denied | `bare`, `list`, `check-rules` | `set`, `add`, `init`, `reapply`, `disable` and `clean` remove tracked files from the working tree — `clean`'s own man page warns about deleting worktree files. |
| `stash` | denied | `list`, `show` | Takes the whole uncommitted tree off disk, which is the loss in its purest form; bare `git stash` is `push`, so bare is not a read here. |
| `submodule` | denied | `bare`, `status`, `summary` | `update`, `deinit`, `add` and `sync` check out or remove submodule contents, and `foreach` runs an arbitrary command in each. Bare is `status` (measured 2026-09-08, exit 0). |
| `switch` | denied | — | `checkout`'s branch half, with the same wholesale tree replacement. |
| `symbolic-ref` | not denied | — | `git symbolic-ref --short HEAD` is how a script asks what branch it is on; the write form differs only by one extra argument, which needs an arity parser this guard does not have. Repointing `HEAD` moves no file either way. |
| `tag` | not denied | — | Bare `git tag` lists, and only `-a`, `-f` and `-d` write. Same parser objection as `branch`, and a tag ref takes nothing off disk. |
| `update-index` | not denied | — | Index only, ruled with `add` and for the same reason. |
| `update-ref` | denied | — | The plumbing spelling of the ref move `reset` is denied for in every form: it moves the branch a live worker's next commit builds on. Unlike `branch` and `tag` it has no orientation form at all, so there is nothing to carve out and nothing to lose by denying it. |
| `worktree` | not denied | — | Operates on OTHER working trees. `add`, `remove` and `prune` take no file off disk in the tree the command targets, which is the only tree this guard reasons about. |

### What the boundary still admits

The set above is deliberately not "everything that writes", so these still pass silently while
workers are live. Each is a stated cost, not an oversight:

- **Ref writes that also have an everyday read spelling** — `branch -f`, `branch -D`, `tag -f`,
  `tag -d`, `symbolic-ref HEAD refs/heads/x`, `reflog expire`, `remote prune`. The ref-move
  hazard is closed only in `update-ref`, `reset` and the branch-moving porcelain, because those
  are the spellings that can be denied without denying orientation.
- **The object database** — `gc --prune=now` and `repack` can drop an object nothing references,
  including a commit a worker orphaned and would have recovered from the reflog.
- **Other working trees** — `worktree remove` aimed at a worktree-isolated agent's checkout
  destroys that agent's tree. The guard's whole model is the tree the command targets, and an
  isolated agent is exempt from it by construction.
- **File-level writes** — `merge-file`, `mergetool`, `rerere`, and any `>` redirect. This is the
  destructive-write case named in "What it does not cover": catching it needs an ownership
  registry mapping briefs to paths, and worktree isolation solves it instead.
- **Foreign-SCM front ends and GUIs** — `git svn rebase`, `git p4 sync`, `git quiltimport`,
  `git citool`. Each is a denied verb wearing another tool's name, and none is installed, or in
  the GUIs' case reachable without a display. A session that starts using one adds its row first.
- **A value-taking option the hook does not list.** `OPTS_WITH_VALUE` names the options whose
  next token is data rather than a subcommand or a help flag, and it is a list, so it is
  incomplete. The failure is one-sided: an unlisted option makes its value *visible* to the
  read-form match, so the residual miss is an unlisted option whose value happens to spell
  `-h`, `--help`, or a read subcommand. Adding a row costs nothing; the alternative is the
  per-verb flag parser this guard refuses to grow.
- **The tokenizer ceiling**, which is a different axis entirely and has its own section:
  ["What it cannot see"](#what-it-cannot-see). A verb in the set still goes unread when the `git`
  word itself is displaced.

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

`env`, `command`, `builtin`, `eval`, `exec`, `nice`, `time`, `xargs`, `timeout`, `sudo`,
`nohup`, `stdbuf`, `setsid`, chained (`nice time git commit`), and each in the `g`-prefixed
coreutils spelling Homebrew installs (`gtimeout`).

Each wrapper carries **the list of its own options that take a separate value**, taken from that
tool's man page, so a value is not misread as the command word: `nice -n 10`, `xargs -I % -J % -R
2 -S 300`, `env -u NAME -P PATH -a ARGV0`, `sudo -u NAME -T 30`, GNU `time -o FILE`. `timeout`'s
bare positional duration is skipped too. **The guarantee is only as good as those lists** — an
option that is not on one is skipped as a valueless flag, and the accuracy of each list is
whatever the man page said. Options whose argument is OPTIONAL are deliberately absent
(`xargs -i`/`-l`/`-e`/`--replace`/`--eof`, `git --exec-path`): such an argument must be glued, so
consuming the next token would eat the command word.

**Shell grammar displaces the command word the same way, and is read the same way.** After `do`,
`then`, `else`, `elif`, `if`, `while`, `until` or `!`, the next word is a command, so
`for f in *; do git commit -m x; done`, `if true; then git commit; fi` and
`while git pull; do sleep 1; done` all deny — as does a keyword and a wrapper together
(`for f in *; do nice git commit; done`), and the cwd check sees a wrapped or keyword-preceded
`cd` (`for d in a b; do cd "$d" && git commit; done`). `for` and `in` are deliberately absent:
the word after them is a loop variable, not a command. The **verb** may carry a glued separator
(`while git pull; do`), which is stripped — that shape, and the plainer `git commit; ls`, were
missed before.

One accepted over-denial comes with this: a bare keyword sitting as an ARGUMENT immediately
before a git call — `echo do git commit` — denies, because telling that `do` is `echo`'s argument
needs a parser. A false deny costs one override; a miss costs a live worker's uncommitted files.
**Quoting the keyword alone does not make it inert** — `shlex` strips the quotes and `echo "then"
git commit` denies exactly as the bare form does. Only a keyword inside a MULTI-WORD quoted string
is inert, because that string is one token (`git commit -m "then git push"` denies on the real
`commit`, never on the string).

Two places a keyword is deliberately NOT read: after a `#` and after a `<<`. A trailing comment
(`make ci  # then git commit`) and a heredoc body (a script being written that contains a loop
around a git call) are text, not command lines, and both were silent before the keyword rule
existed. Separators still open command position inside them, exactly as they always did.

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
  (`git pull;`) is stripped; it is only the command word the separator still hides. **Asymmetry,
  deliberate:** the cwd check DOES strip a leading `(` before testing for `cd`, because
  `(cd elsewhere && git commit)` is how a subshell cd is normally written and resolving it to the
  wrong tree returns an affirmative "no block"; the verb scan does not, so `(git commit)` stays a
  missed deny in the SAME tree;
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
  env assignment, after a leading exec wrapper and its options, or after a shell keyword
  (`; do`, `; then`) outside a comment or heredoc body. `man git commit`, `which git` and
  `command -v git` are not git calls. Quoted text is tokenized with `shlex`, so a multi-word
  string mentioning a git command is one token and cannot fire — a single quoted WORD is not
  protected, since `shlex` strips its quotes.
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
