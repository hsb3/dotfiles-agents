# Isolating work inside one instance

An instance is already isolated from the host. This is about partitioning work *within* one
instance, so several lines of work do not tread on each other in a single `/workspace`.

## Git worktrees — the real mechanism

opencode supports git worktrees natively. Each one gets its own directory, its own branch,
and can run its own start command, so two efforts can proceed against the same repo without
sharing a checkout.

**It requires the workspace to be a git repository.** opencode refuses outright with
"Worktrees are only supported for git projects" when `.git` is absent. `--seed` copies
`.git` along with everything else and chowns `/workspace` to root, so seeding the main
checkout is all it takes — git and worktrees work immediately, with no `safe.directory`
workaround needed.

**`--seed` refuses a git worktree.** A worktree's `.git` is a pointer file to a path on
the host the container can't see, so seeding one would leave git silently broken inside
the instance. Seed from the main checkout instead.

`.git` is only absent when the instance was seeded from a `git archive` export or a plain
directory copy — that's the one case still needing the fallback:

```
docker exec ocsbx-<name>-opencode-1 sh -c 'cd /workspace && git init -q && git add -A && git commit -qm seed'
```

Worktree checkouts do not live under `/workspace`. They are created under the instance's
data volume at `/root/.local/share/opencode/worktree/<project-id>`, which `opencode-sandbox
export` does not reach either — it only backs up the workspace volume. For committed work
that is not actually a problem: a worktree's branch still lives in the shared repository at
`/workspace/.git`, so `opencode-sandbox fetch-url <name>` (`references/project-context.md`)
pulls it out by name regardless of which directory has it checked out. Only uncommitted
changes sitting in a worktree checkout are stuck — for those, `docker cp` against that
specific path is still the only way out.

## When there is no git

Without a repository the only partition available is ordinary subdirectories under
`/workspace`. That is genuinely fine for most sandbox work — separate directories per task,
and the agent scoped to one at a time. Say so plainly rather than implying more isolation
than exists.

## Or just use a second instance

Two instances are cheap, fully isolated from each other, and need no git at all. Prefer
this over worktrees when the efforts need to run in parallel: separate volumes, separate
ports, separate MCP registrations, and destroying one cannot affect the other. Name each
`<project>-<branch>` so the pair stays legible in `opencode-sandbox list`:

```
opencode-sandbox create myapp-feature-a --seed .
opencode-sandbox create myapp-feature-b --seed .
```

Ports are derived from the instance name and probed for availability, so a second instance
never collides with the first.
