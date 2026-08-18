# Getting project context into an instance

## `--seed` copies verbatim

`--seed <dir>` tars the directory into the fresh workspace volume before the instance
first starts. It applies **no filtering at all** — no `.gitignore`, no skip list. A
`node_modules`, a `.git` with years of history, a `dist/` — all of it goes in, costing copy
time and disk, and all of it is visible to the agent as ordinary files.

So decide deliberately what "the project" means for this sandbox:

**Whole working tree**, when the sandbox should behave like a clone of the real thing and
the repo is small:

```
opencode-sandbox create review --seed .
```

**Tracked files only**, which is usually what you want for a large repo — it drops build
output and ignored files while keeping the real structure:

```
git archive HEAD --prefix=proj/ | (mkdir -p /tmp/seed && tar -C /tmp/seed -x)
opencode-sandbox create review --seed /tmp/seed
```

**A subdirectory**, when the task only concerns one package: point `--seed` straight at it.
The agent then cannot be distracted by, or leak context from, the rest of the repo.

**Keep `.git` deliberately.** Worktrees inside the instance require it (see
`workspaces.md`), and `git archive` output has no `.git` at all. If the agent needs to
branch or diff, seed the working tree instead, or `git init` inside the container
afterward.

## After creation: `docker cp` both directions

Seeding only happens at create time, and the CLI has no copy subcommand. Use Docker
directly against the instance's backend container, named `ocsbx-<instance>-opencode-1`:

```
docker cp ./notes.md ocsbx-review-opencode-1:/workspace/notes.md          # push in
docker cp ocsbx-review-opencode-1:/workspace/out/report.md ./report.md    # pull out
```

Both are verified working, and a file pushed in this way is immediately visible to the
agent through the MCP bridge — no restart needed.

**Pull results out before destroying.** `destroy` deletes the workspace volume and
everything in it. There is no undo and no snapshot.
