# worktree-root

Takes over Claude Code's worktree creation so worktrees land under the project's
`checkout-root` instead of `.claude/worktrees/`. One `hook.py` handles three events.
Delivered as a plugin it covers subagent `isolation: worktree` and `EnterWorktree`;
`claude --worktree` creates its worktree before plugin hooks load, so that path stays native.

| Event | What it does |
|---|---|
| `WorktreeCreate` | Creates `<root>/<name>` on branch `worktree-<name>` (`/` becomes `+` in both) and prints the resolved path; a name already registered as a linked worktree is resumed (path printed, tree untouched) |
| `SubagentStop` | Removes the agent's worktree `<root>/agent-<agent_id>` and its branch when every removal guard passes; otherwise keeps both. Always exits 0 |
| `WorktreeRemove` | Removes a worktree (`ExitWorktree` with remove) under `<root>` or, with the key set, the native `.claude/worktrees`, when every removal guard passes; a failed guard exits 1, names the reason and leaves everything in place |

## Removal guards

Both removal paths share one check. The path must be exactly `<root>/<leaf>`, registered
with git on branch `worktree-<leaf>` (the shape this hook creates), with no tracked change
and no untracked file (`git status --porcelain --untracked-files=all`, so
`status.showUntrackedFiles=no` cannot hide one; ignored files do not count), no
assume-unchanged entry and no skip-worktree entry present on disk, and its
branch must hold no commit that no other branch, tag or remote ref has. Removal is
`git worktree remove` without `--force`, so a locked worktree is refused too, then
`git branch -d`: when the branch is not merged into the main checkout's HEAD, the branch
is kept and a stderr note says so.

A worktree someone made by hand in the root is caught by the branch-name guard (any other
branch) or, when it reuses the `worktree-<leaf>` name, by the unique-commit guard. A
clean, same-named worktree whose commits all live on other refs is indistinguishable
from a hook-created one and is removed; that loses nothing.

## Placement

`<root>` is the `checkout-root:` key of the main checkout's atelier activation file,
read through the shared `_lib/atelier_local.py`. Unset means the native
`<main checkout>/.claude/worktrees`. Both are anchored on the **main** checkout, so a
dispatch from inside a linked worktree never nests.

A repo with no main checkout (`--separate-git-dir`, or a session inside a submodule)
falls back to native placement anchored on `git rev-parse --show-toplevel`:
`<toplevel>/.claude/worktrees`. The key is refused there, because there is no main
checkout to resolve it against.

Creation fails loudly (exit 1, reason on stderr) when the key is invalid (a `$`
variable, a path outside the project or inside `.git`, a symlink that escapes), when the
root resolves outside the main checkout (a committed `.claude` or `.claude/worktrees`
symlink), or when the name is empty, absolute, holds a `..` segment, is a symlink, or
names an existing path that is not a registered worktree. There is no silent fallback to
the native location. A `.worktreeinclude` copy error rolls the new worktree and branch back.

## Parity with native creation

- **Base ref**: `worktree.baseRef: "head"` (settings.local.json, then settings.json,
  then `$CLAUDE_CONFIG_DIR/settings.json` or `~/.claude/settings.json`) branches from the
  session's HEAD. Otherwise, when `origin` exists and `FETCH_HEAD` is missing or older
  than a day, it runs `git fetch origin <default branch>` (15 s cap; failure is a stderr
  note), then uses `origin/HEAD`, else `origin/main`, else HEAD.
- **`.worktreeinclude`**: copies files that are untracked, gitignored, and matched by
  its gitignore-syntax patterns. Tracked files, unignored files and symlinks are never
  copied.
- **Agent cleanup**: the harness keeps every hook-created agent worktree, so
  `SubagentStop` restores native cleanup through the removal guards.

`SubagentStop` always exits 0 and writes nothing to stdout.

## Configuration

| Setting | Where | Meaning |
|---|---|---|
| `checkout-root` | activation file frontmatter | Directory, relative to the main checkout, that holds new worktrees |
| `worktree.baseRef` | Claude Code settings | `head` branches from HEAD; anything else follows origin (see Base ref) |

## Known limits

- **Settings files, not effective settings.** `worktree.baseRef` is read from the files
  above, so `--settings`, `--setting-sources` and managed settings can give the hook a
  different base than native creation would pick (measured live).
- **SubagentStop runs beside other SubagentStop hooks.** When another hook blocks the
  stop, this one may already have removed the clean worktree the subagent keeps using.
- **Native session features are not replicated.** `EnterWorktree` by path only accepts
  worktrees under `.claude/worktrees`, and native `--worktree` sessions git-lock their
  worktree; worktrees created under a `checkout-root` get neither.
- **Ignored files do not count as work.** They pass the cleanliness guard and are deleted
  with the worktree, including a changed `.worktreeinclude` copy such as `.env`.
- **No main checkout, no nesting guard.** In the `--separate-git-dir` and submodule
  fallback, a session inside a linked worktree anchors on that worktree's toplevel.
- **`--worktree` exit is unmeasured.** Removal of a native `.claude/worktrees` path is
  accepted while the key is set, but whether the harness fires this hook on that exit,
  and whether it unlocks the native session lock first, was not measured.
