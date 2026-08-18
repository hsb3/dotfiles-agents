# Isolating work inside one instance

An instance is already isolated from the host. This is about partitioning work *within* one
instance, so several lines of work do not tread on each other in a single `/workspace`.

## Git worktrees — the real mechanism

opencode supports git worktrees natively. Each one gets its own directory, its own branch,
and can run its own start command, so two efforts can proceed against the same repo without
sharing a checkout.

**It requires the workspace to be a git repository.** opencode refuses outright with
"Worktrees are only supported for git projects" when `.git` is absent — and `.git` is absent
whenever the instance was seeded from a `git archive` export or a plain directory copy.
Either seed the working tree including `.git`, or initialize inside the container:

```
docker exec ocsbx-<name>-opencode-1 sh -c 'cd /workspace && git init -q && git add -A && git commit -qm seed'
```

Worktree checkouts do not live under `/workspace`. They are created under the instance's
data volume at `/root/.local/share/opencode/worktree/<project-id>`, which means
`docker cp` of `/workspace` will not collect them — copy from the worktree path explicitly
if the work you want is on a branch.

## When there is no git

Without a repository the only partition available is ordinary subdirectories under
`/workspace`. That is genuinely fine for most sandbox work — separate directories per task,
and the agent scoped to one at a time. Say so plainly rather than implying more isolation
than exists.

## Or just use a second instance

Two instances are cheap, fully isolated from each other, and need no git at all. Prefer
this when the two efforts share nothing: separate volumes, separate ports, separate MCP
registrations, and destroying one cannot affect the other.

```
opencode-sandbox create feature-a --seed .
opencode-sandbox create feature-b --seed .
```

Ports are derived from the instance name and probed for availability, so a second instance
never collides with the first.
