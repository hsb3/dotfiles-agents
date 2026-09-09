# worktree-isolation

`PreToolUse` on the `Agent` tool. When the project's activation file turns it on, a dispatch that
would put a **writing** worker in the orchestrator's own checkout is rewritten to carry
`isolation: "worktree"`, so the worker gets its own git worktree instead of sharing the working
tree and index the session is using.

It fails open on every error path and never denies a dispatch — forcing a worktree is a
correction, not a refusal.

## Why

`builder` and `manager` edit files, and a subagent inherits the parent session's working directory
by default. Two writers in one wave, or one writer alongside a strategist who is mid-edit, share an
index and a tree; the cross-contamination is invisible until integration. The delegation skill has
always *asked* for isolation on write-waves, but a request in prose is honoured only when the
dispatching session remembers it.

## What it deliberately does not isolate

A git worktree is a clean checkout of a ref, so **uncommitted and untracked files in the parent
checkout do not exist inside it**. A `scout` sent to inventory the working diff, or a `reviewer`
sent to re-derive a claim from files the session has not committed, would silently read a different
tree and report on nothing. Read-only roles stay in the parent checkout, which is also where they
are cheapest.

`scout`, `reviewer`, `Explore`, `Plan`, and `fork` are never rewritten, even when named explicitly
in an `isolate:` list. `fork` is excluded for a second reason: it inherits the conversation, so its
premise is continuity with the caller.

## Activation

Shared with the other atelier hooks: `<project>/.claude/atelier.local.md`, YAML frontmatter, parsed
by a small tolerant reader (stdlib only, no PyYAML).

```markdown
---
enforce: strict
isolate: writers
---
```

This hook reads only `isolate:`. Two forms:

| `isolate:` | Effect |
|---|---|
| absent, `off`, any other scalar, or an unparseable file | inert |
| `writers` | isolates `builder`, `manager`, `general-purpose` |
| a list (block or `[a, b]` inline) | isolates exactly those agent types |
| an empty list, or a bare `isolate:` with no items | inert — an empty set is an empty intent, not a request for the built-ins |

A plugin-namespaced type matches its bare form, so `atelier:builder` is covered by `builder`. A
dispatch with no `subagent_type` resolves to `general-purpose`, which carries the full tool set, so
absence counts as a writer.

### In a linked worktree

Enforcement follows the main checkout's activation file into worktrees. This hook creates the
situation the others have to survive, and it is not exempt from it: a `manager` that was itself
isolated fans out its own writers from inside a linked checkout, where the activation file —
normally gitignored — does not exist. When no activation file sits at the project dir, the hook
asks `git rev-parse --git-common-dir` whether that dir is a linked worktree and, if it is, reads
the **main checkout's** activation file instead, so the isolation policy the project armed still
applies one level down.

The lookup is lazy — it costs a `git` subprocess only when the direct path holds no file. The
consequence is that a **tracked** activation file is seen at its committed version there: inside a
worktree, a tracked activation file wins as checked out on that worktree's branch, not as the main
checkout currently has it in its working tree. `ATELIER_ACTIVATION_FILE` still wins outright and is
never re-resolved, and with no `git` on `PATH` — or a project dir that is not a linked worktree —
behaviour is exactly what it was.

## Nesting is intended

A dispatcher that is itself in a linked worktree — a `manager` that was isolated on the way in —
gets its writers put in **nested** worktrees, one per worker, each on its own branch. That is the
designed outcome, not a misconfiguration, and the hook does not stand down there. Two reasons,
recorded so this is not re-litigated:

1. **Sharing the dispatcher's worktree reintroduces the exact hazard this hook exists for.** A
   manager runs builders in parallel; standing them all in its single worktree gives them one index
   and one working tree. The dispatcher being one level down does not make two concurrent writers
   safe — it only moves the shared tree.
2. **It would contradict how the activation file is resolved.** The resolver above deliberately
   follows policy *into* a worktree. A hook that reads its policy through a worktree and then
   stands down inside one is incoherent.

What nesting actually costs is integration ergonomics: the dispatcher has to collect each worker's
commits and clean up the leftovers. So the notice on a nested rewrite carries the integrate step,
at dispatch time rather than at the end of the wave:

```
… You are standing in a linked worktree yourself, so this one is NESTED under it on its own
branch — intended, not a misconfiguration. To integrate when it reports: `git worktree list`
for its path and branch, then `git cherry HEAD <branch>` and READ it — `+` lines are commits
you have not picked yet, `-` lines are already in — then `git cherry-pick <the + SHAs>` if
there are any. Repeat that pair each round; it never re-applies. Finally
`git worktree remove <path> && git branch -D <branch>` to clean up.
```

**Why not the obvious `git cherry-pick HEAD..<branch>`, which the notice used to carry.** A worker
reports more than once, and integration is per-round. Picking a commit rewrites it, so the original
on the worker's branch stays unreachable from the dispatcher's HEAD and the range still spans it on
a later round; cherry-pick's own patch-id filter then drops every one of them and the command dies
with `error: empty commit set passed`, exit 128. That fatal was reproduced by hand against a real
repo before this step was rewritten.

`git cherry <upstream> <branch>` answers the same question without it. It prints one line per commit,
`-` for one whose patch-id is already upstream and `+` for one that is not, so `git cherry HEAD
<branch>` names exactly the set still to take — correct after an earlier round changed the SHAs, and
correct under either `worktree.baseRef` setting (with `head` the worker's branch starts at the
dispatcher's HEAD, with `fresh` at the default branch; the range is "what this branch has that mine
does not" either way).

**Two commands the dispatcher reads between, deliberately, not one shell one-liner.** A pipeline
like `picks=$(git cherry …); git cherry-pick $picks` is wrong twice over. The notice is pasted into
a **zsh** shell, and zsh does not word-split an unquoted expansion — every SHA arrives as a single
argument and `git cherry-pick` dies with `fatal: bad revision`. And guarding on an empty `$picks`
cannot tell "nothing to pick" from "`git cherry` failed", so a stale branch name would exit 0 with
nothing integrated, which is exactly the silent no-op this step exists to prevent. Passing the SHAs
as literal arguments has no splitting surface in any shell, needs no empty-set special case, and a
failed listing is seen because you read it before picking. `xargs` is not a fix either: BSD `xargs`
skips the utility on empty input, GNU `xargs` runs it once with no arguments.

`tests/test_worktree_isolation.py` drives this procedure as argv over several rounds against a real
linked worktree: two commits taken, a round with nothing new that applies nothing and exits 0, a
round that takes exactly the one new commit, and a mistyped branch name that fails rather than
reporting success.

**The ceiling.** Patch-ids match content, not identity. A commit whose content changed while you
resolved a conflict on an earlier round no longer matches its original, so `git cherry` still lists
it `+` and picking it applies it again. Reading the `+` lines before you pick is what catches that,
which is the other reason these stay two commands.

To sweep for strays after a wave, from the dispatcher's own worktree:

```sh
git worktree list --porcelain | sed -n 's,^branch refs/heads/,,p' \
  | grep '^worktree-agent-' | grep -vx "$(git branch --show-current)"
```

(The harness names each worker's branch after its worktree, so the prefix filter finds them; the
second `grep` drops the dispatcher's own branch, which the same listing includes.)

Deliberately three commands rather than one loop: `git cherry-pick` can stop on a conflict, and a
loop fanning out over branches would keep going past it and leave a half-integrated tree with no
one having read the failure. The dispatcher should see each worker's result.

## Inert paths

Beyond an unarmed activation file, the hook stands down when:

- the dispatch already sets `isolation` (including `remote`, which it must not downgrade);
- the dispatch sets `cwd`, documented as mutually exclusive with `isolation: "worktree"`;
- the agent type is in the never-isolate set above;
- the project is not a git repository. This one is not cosmetic: Claude Code raises
  `Cannot create agent worktree: not in a git repository`, so forcing isolation there would turn a
  guardrail into a hard failure on every dispatch.

## Install

1. Copy this directory into `primitives-core/hooks/`.
2. Symlink it into the plugin assembly the way the other hooks are wired:
   `ln -s ../../../primitives-core/hooks/worktree-isolation plugins/atelier/hooks/worktree-isolation`
3. Add a roster row to `primitives-core.yaml` (id `worktree-isolation`, type `hook`, source
   `primitives-core/hooks/worktree-isolation`, origin `authored`, disposition `qualified`, targets
   `[claude-code]`) — `make ci` reconciles the roster against disk and requires every field,
   `targets` included.
4. Add the `PreToolUse` entry inside the **existing top-level `"hooks"` object** of
   `plugins/atelier/hooks/hooks.json` (wrapper shown for placement; do not add a second one):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/worktree-isolation/hook.py\"",
            "statusMessage": "Checking worker isolation...",
            "timeout": 10,
            "type": "command"
          }
        ],
        "matcher": "Agent"
      }
    ]
  }
}
```

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `CLAUDE_PROJECT_DIR` | set by Claude Code | Anchor for the activation file and the git check; falls back to the payload `cwd` |
| `ATELIER_ACTIVATION_FILE` | `$CLAUDE_PROJECT_DIR/.claude/atelier.local.md` | Activation file location |
| `WORKTREE_ISOLATION_LOG_PATH` | `${XDG_DATA_HOME:-~/.local/share}/agent-logs/claude-code/atelier/worktree-isolation.jsonl` | Ledger override |

## Ledger

One row per armed dispatch, appended to the `worktree-isolation` stream once the activation file
is on. Nothing is logged while the hook is inert (unarmed, `isolation`/`cwd` already set, or no
resolvable project dir) — those paths exit before the logger is even opened.

```
${XDG_DATA_HOME:-~/.local/share}/agent-logs/claude-code/atelier/worktree-isolation.jsonl
```

Each row carries the identity envelope (`v`, `plugin`, `harness`, `stream`, `ts`, `project`) plus
`session_id`, `agent_type`, `mode`, `isolated` (bool), and `reason` (`null` when isolated, else
`"agent type not armed"` or `"project dir is not a git repo"`). A row written from the fail-open
error path also carries `error` and a truncated `traceback`.

Rewrite rows carry one more field, `nested` (bool): whether the **dispatcher** was itself standing
in a linked worktree, which is what makes the worker's worktree a nested one. It answers the
stray-branch audit — how many leftover worker branches a wave should have produced, and under whom
— from the ledger instead of from `git branch`. It appears only on rewrite rows: it costs a `git`
subprocess and every non-rewrite row is a path where no worktree was created, so there is nothing
to audit.

The question is answered by comparing `git rev-parse --git-dir` against `--git-common-dir` (equal
in a main checkout, `<common>/worktrees/<name>` vs `<common>` in a linked one), with both sides
resolved through symlinks first. Not by the common dir's literal value: that is `.git` only at a
main checkout's *root* and a relative `../../.git` from any subdirectory of the same checkout, so a
string test reports every subdirectory as a worktree.

## Design notes

- **Rewrite, never deny.** `hookSpecificOutput.updatedInput` (PreToolUse only) replaces the tool
  input in place, so the dispatch proceeds with isolation added rather than bouncing back for the
  model to retry. Verified by live probe against Claude Code 2.1.220: the subagent landed in
  `.claude/worktrees/agent-<id>`.
- **Announced, not silent.** The rewrite moves the worker to a checkout where the session's
  uncommitted work does not exist. That is worth one line of `systemMessage`, so a surprised reader
  can trace the behaviour to this hook rather than to the harness.
- **Fail-open, always.** Every path exits 0. An un-isolated worker is the pre-hook status quo and
  merely risky; a hook that crashes on every dispatch is an outage.
- **The activation parser is shared; the sourcing is not.** Parsing lives in
  `hooks/_lib/atelier_local.py` — `_lib/` is a member of every hooks assembly (ADR 0017), so
  importing it is safe where importing another hook's module is not. This hook keeps its own path
  resolution, size cap and fail-open default.
- **Base ref is a separate setting.** A new worktree branches from `origin/<default-branch>` unless
  the project sets `{"worktree": {"baseRef": "head"}}` in settings.json (values `fresh`, the
  default, or `head`). Where the default branch is a publish-only surface, `head` is the one that
  gives workers the branch the session is actually on.
- **No restart needed to change policy.** The activation file is read on every dispatch, so edits
  take effect on the next one. Only a change to `hooks.json` requires restarting the session.

## Codex workers

Codex hook commands select `ATELIER_HARNESS=codex`. `SubagentStart` calls the shared
`codex_workers.ensure_worker(payload)` before tools; worker-context may call it too,
so registration does not depend on sibling hook ordering. Registry updates are atomic
and locked per actual session/agent identity. The first rollout `session_meta` record
must match the worker ID. Its immediate `parent_thread_id` selects the registered
manager checkout as the child branch's base; the root session is the only parent
allowed without a worker record. Missing ancestry or registration denies later tools.

`PreToolUse` routes normalized `Bash` command text into that checkout and rewrites
all `apply_patch` Add/Update/Delete/Move paths. Existing worker absolute paths remain
valid; parent paths map into the worker; traversal, symlink escapes, other worktrees,
Git metadata edits and unsupported tool inputs are denied. Inherited Git routing
variables are cleared for commands and hook Git lookups. Each guard independently
resolves the same effective payload, retaining `original_cwd`; none relies on another
PreToolUse hook having already rewritten the input.

State lives under the repository's common Git directory:
`atelier-codex/workers/<session>/<agent>.json` and
`atelier-codex/checkouts/<session>/<agent>`. There is no automatic branch or worktree
deletion. With `workspace-write`, the caller must authorize the checkout directory,
`.git/worktrees` and `.git/objects` as writable roots. Registration failure never
silently leaves an armed worker operating in its inherited checkout. Unarmed projects
are inert, including non-Git projects; existing mappings persist across policy edits
so an already-isolated worker never falls back to the parent by accident.

This provides worktree collision avoidance. The native thread's cwd metadata and
sandbox remain inherited. Absolute shell paths, explicit shell cwd changes and scripts
can still access other permitted trees; this is not an OS containment boundary.
Read-only roles cannot use patch tools. Builder/scout/reviewer/code-reviewer roles
cannot invoke native or collaboration spawn/message/control tools; their shell
read-only obligations remain part of their role instructions.
