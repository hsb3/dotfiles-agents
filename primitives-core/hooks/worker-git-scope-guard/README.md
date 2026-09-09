# worker-git-scope-guard

Activation location follows the [shared selection rules](../../skills/activation/SKILL.md):
fresh Codex projects use `.codex/atelier.local.md`; Claude Code and Codex legacy fallback
use `.claude/atelier.local.md`. Explicit overrides win; policies are never merged.

Refuses a **subagent's** mutating git call that would destroy work the subagent does not
own. `PreToolUse` on `Bash`, two independent halves:

| Half | Fires when | Armed by |
|---|---|---|
| **Stash in a shared tree** | a worker runs a mutating `git stash` form while the resolved directory is the **main checkout**, not its own linked worktree | nothing — live wherever the hook is installed |
| **Write on a protected branch** | `commit`, `merge`, `rebase`, `cherry-pick`, `revert`, `am` with HEAD on a protected branch, or a `push` whose refspec targets one | `protected-branches:` in the selected `atelier.local.md` |

Read-only git never fires. Neither do the read forms of the verbs above: `stash list` and
`stash show` are how a session orients, and are never blocked — the same read/write split
`live-worker-git-guard` documents.

## Why

**The stash half** answers an observed loss. Six workers were dispatched into one shared
checkout with disjoint file ownership — the recommended default, cheaper than isolating
every worker — and each of them ran `git stash` to get a clean tree. A stash is not scoped
to the files you own; it takes the whole tree. One conflicted pop plus a drop, and nine
files of sibling work were gone with nothing left to recover from. Prose could not stop
it, and the doctrine text did not even cover it: a stash in a shared tree is not "touching
state outside your own worktree", because there is only one tree.

**The protected-branch half** answers the other direction. A worktree shares the repo's
`.git` and its remote, so isolation is no protection at all here — a commit made with HEAD
on a protected branch lands on the real branch, and a push aimed at one reaches the real
remote. One instance reached for `--no-verify` to get past a repo hook. That flag skips
git's own hooks and has no effect on this one: a `PreToolUse` hook runs in the harness,
before git is ever invoked.

## Its sibling, and what each one covers

`live-worker-git-guard` is the **complementary** hook, not an alternative — a reader
should never merge or skip one thinking the other has it.

| | `live-worker-git-guard` | `worker-git-scope-guard` |
|---|---|---|
| Protects | an orchestrator from clobbering **its own** live children | a worker from clobbering **peer** workers and shared branches |
| Fires for | any session holding unsettled delegations, root or manager | subagents only |
| Keys off | the invoking session's pending-child set | the resolved directory and the configured branch list |
| Blind spot the other fills | two peer workers, neither the other's parent, each with an empty pending set | a root session with live children, which is not a subagent at all |

Both are needed. Running only the first leaves the observed six-builder loss unguarded;
running only this one lets a root session pull the rug out from under its own workers.

## Who it fires for

**Subagents only**, both halves. The payload carries `agent_id` / `agent_type` inside a
subagent and neither in the main session. Widening it to the root session was considered
and rejected: that session's checkout is the operator's own hands, it explicitly owns
branch, commit, push, and merge, and `live-worker-git-guard` already covers the one case
where its git is genuinely dangerous — holding live children. A guard that denied the
orchestrator the integration work it is responsible for would be turned off within a day,
and a guard that is off protects nobody.

## Configuration

One key, in the project's selected `atelier.local.md` frontmatter:

```yaml
protected-branches:
  - main
  - release
```

The inline form `protected-branches: ["main", "release"]` works too. A trailing comment on
the key line is fine — `protected-branches:  # publish only` is a blank value, so the block
below it is still read.

Three rules worth stating outright:

- **This is a distinct key from `protected:`.** That one names protected *file paths* for
  `config-custody` and is never read here — a file glob must not become a branch name.
  The two coexist in one frontmatter block and each hook asks for its own key by name.
- **There is no built-in list.** Absent, empty, or unparseable means the protected-branch
  half is **inert**. Shipping a `{main, master}` default would be wrong wherever the
  default branch is a publish-only surface and day-to-day work happens elsewhere: it would
  guard a branch nobody commits to while leaving the real integration branch open.
- **Names are matched exactly**, against the branch at HEAD or the last segment of a push
  refspec. No globs.

The stash half needs no configuration and has no off switch short of not installing the
hook. It is armed by the shape of the checkout, not by a setting.

### Where the key is read from

In order, first hit wins:

1. `$ATELIER_ACTIVATION_FILE`, if set. It wins outright and is never second-guessed.
2. the harness-selected activation path.
3. **The main checkout's copy, when the project directory is a linked worktree.**

That third step exists because without it this half switches itself off precisely where it
is needed. A linked worktree is a clean checkout and the activation file is conventionally
gitignored, so a worker dispatched into one finds no file, the list parses empty, and every
protected branch is open to it — while that same worktree shares the `.git` and the remote
that make its commit land on the real branch. The main checkout is resolved from the same
`--git-common-dir` / `--git-dir` pair the shared-tree test uses, and only on the miss: this
hook runs on every `Bash` call, so it must not shell out on each one. A command with no
`git` token in it skips the whole lookup, since no invocation can be found in one anyway.

The fallback touches the **read of the key only**. Tree-kind detection is untouched, so a
worker in its own worktree still stashes freely while now inheriting the main checkout's
protected branches — the two halves stay independent.

`activation.py check` (via `/atelier:activate`) reports what this key actually resolved to
— armed, inert, or not configured — by calling this hook's own loader.

## How the shared-tree test works

For the resolved directory of each git call:

```
git -C <dir> rev-parse --git-common-dir --git-dir
  fails / empty / OSError   -> not a repo, or no git: stay silent
  basename is not `.git`    -> bare repo or submodule: stay silent, never guess
  the two resolve equal     -> main checkout: SHARED, a stash is denied
  they differ              -> linked worktree: the worker's own tree, stash allowed
```

Comparing the two paths is deliberate and was measured, not assumed. `--git-common-dir`
alone does not identify the main checkout: at the checkout root git answers `.git`, but
from any **subdirectory** of the same checkout it answers a relative `../../.git`. Testing
for the literal string `.git` therefore reads every subdirectory of a shared tree as a
worktree and lets the exact stash this guard exists to stop straight through.
`--git-dir` is the same directory in a main checkout and points into
`.git/worktrees/<name>` in a linked one, so equality separates them from anywhere. Both
sides are resolved with `realpath` before comparison — git answers one of the two with its
own already-resolved absolute path, so on a platform with a symlinked temp or home
directory an unresolved compare mismatches and, again, silently allows the stash.

## Honest scope — this is a tripwire, not containment

A worker that writes a shell script and runs that, or drives git through a tool other than
`Bash`, is not caught. Command parsing splits on raw text, so a separator inside a quoted
argument can still fragment a command and hide an invocation. That is the ceiling any
string-based Bash tripwire has, and it is worth accepting for the same reason: catching the path agents
actually take, and leaving a refusal in the transcript, is worth much more than the
partial coverage costs — but it is not a sandbox and must not be sold as one.

**Server-side branch protection is the layer above this one.** A local hook cannot stop a
determined or novel path to the remote; a protected-branch rule on the forge can. This
guard's job is to turn an easy accident into a refusal the worker reads and reports,
early, in the transcript. Where the branch genuinely matters, configure both.

Fail-open everywhere: an unparseable payload, an unreadable activation file, a `git` that
is missing or slow, an exception anywhere in the decision — every one exits 0 with no
output. A guard that cannot read its own inputs has no grounds to block, and the session is
left exactly as unguarded as it was before the hook existed.

## Install

1. Copy this directory into `primitives-core/hooks/`.
2. Symlink it into the plugin assembly the way the other hooks are wired:
   `ln -s ../../../primitives-core/hooks/worker-git-scope-guard plugins/atelier/hooks/worker-git-scope-guard`
3. Add a roster row to `primitives-core.yaml` (id `worker-git-scope-guard`, type `hook`,
   source `primitives-core/hooks/worker-git-scope-guard`, origin `authored`, disposition
   `qualified`, targets `[claude-code]`).
4. Add the `PreToolUse` entry inside the **existing top-level `"hooks"` object** of
   `plugins/atelier/hooks/hooks.json` (wrapper shown for placement; do not add a second one):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/worker-git-scope-guard/hook.py\"",
            "statusMessage": "Checking worker git scope...",
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

The stash half fires wherever the plugin is installed; the protected-branch half waits for
`protected-branches:`.

## Design notes

- **Promoted from a field-tested implementation in another repo by the same author**,
  installed and running there before it was generalized here. The command parsing
  (`strip_heredocs`, `_cd_resolves`, `invocations`, `target_branches`) and the
  resolver-as-argument shape of `decide()` come across unchanged; the stash half, the
  configurable branch list, and the shared-tree test are new.
- **`decide()` takes its resolvers as arguments** — branch, tree kind, and the protected
  set are all injected. That is what lets the whole decision be tested with no git repo
  and no activation file, and it is the property to preserve in any change here.
- **No ledger.** Every other guard in this bundle appends a row; this one deliberately does
  not, because nothing yet reads it and a deny is already visible where it matters — in the
  transcript, to the worker that hit it. Add one when there is a question to answer with it.
- **The frontmatter parser is shared; the sourcing is not.** Parsing lives in
  `hooks/_lib/atelier_local.py`, which every reader of the activation file imports — six
  hand-rolled copies used to disagree about the same shapes. Which bytes to parse stays
  here, because this hook's fallback to the main checkout's copy is its own rule.
  `activation.py check` still reports every key by calling the hooks' own loaders rather
  than parsing the file itself.
- **An unknown `stash` subcommand is left alone.** Only the first token after `stash` can
  be a subcommand — a later bare word is a message or a pathspec, so `git stash -m list`
  does not read as `git stash list`.

## Codex

With `ATELIER_HARNESS=codex`, the shared worker registry supplies the effective cwd
and native identity before parsing Git commands. Existing protected-branch and stash
rules still apply. Literal mutating Git commands aimed at another checkout in the
same repository are denied; unrelated repositories and read-only verbs retain their
existing treatment. Missing identity in an armed project denies instead of evaluating
the inherited parent checkout. Shell scripts and indirect Git invocation remain outside
this parser's contract; this guard is not filesystem containment.
