# worktree-root

Takes over Claude Code's worktree creation so worktrees land under the project's
`checkout-root` instead of `.claude/worktrees/`. One `hook.py` handles three events.

| Event | What it does |
|---|---|
| `WorktreeCreate` | Creates `<root>/<name>` on branch `worktree-<name>` (`/` becomes `+`) and prints the resolved path |
| `SubagentStop` | Removes an agent's worktree and branch when the tree is clean and the branch holds no commit that no other branch, tag or remote ref has |
| `WorktreeRemove` | Removes the registered worktree (`ExitWorktree` with remove) and deletes its `worktree-*` branch |

## Placement

`<root>` is the `checkout-root:` key of the main checkout's atelier activation file,
read through the shared `_lib/atelier_local.py`. Unset means the native
`<main checkout>/.claude/worktrees`. Both are anchored on the **main** checkout, so a
dispatch from inside a linked worktree never nests.

Creation fails loudly (exit 1, reason on stderr) when the key is invalid (a `$`
variable, a path outside the project or inside `.git`, a symlink that escapes), or the
name is empty, absolute, holds a `..` segment, resolves outside `<root>`, or already
exists. There is no silent fallback to the native location.

## Parity with native creation

- **Base ref**: `worktree.baseRef: "head"` (settings.local.json, then settings.json,
  then user settings) branches from the session's HEAD; otherwise the local
  `refs/remotes/origin/HEAD` without a fetch, falling back to HEAD.
- **`.worktreeinclude`**: copies files that are untracked, gitignored, and matched by
  its gitignore-syntax patterns. Tracked files, unignored files and symlinks are never
  copied.
- **Agent cleanup**: the harness keeps every hook-created agent worktree, so
  `SubagentStop` restores native cleanup. It acts only when the stop's `cwd` is
  exactly `<root>/agent-<agent_id>` on branch `worktree-agent-<agent_id>`.

`SubagentStop` always exits 0 and writes nothing to stdout.

## Configuration

| Setting | Where | Meaning |
|---|---|---|
| `checkout-root` | activation file frontmatter | Directory, relative to the main checkout, that holds new worktrees |
| `worktree.baseRef` | Claude Code settings | `head` branches from HEAD; anything else follows origin/HEAD |
