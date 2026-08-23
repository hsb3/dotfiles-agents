# Getting project context into an instance

## `--seed` copies verbatim

`--seed <dir>` tars the directory into the fresh workspace volume before the instance
first starts. It applies **no filtering beyond `.DS_Store`** — no `.gitignore`, no skip
list otherwise. A `node_modules`, a `.git` with years of history, a `dist/` — all of it
goes in, costing copy time and disk, and all of it is visible to the agent as ordinary
files.

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

## After creation: getting files in and out

Seeding only happens at create time. For a single loose file afterward, `docker cp`
against the instance's backend container — named `ocsbx-<instance>-opencode-1` — still
works, and a file pushed in this way is immediately visible to the agent through the MCP
bridge, no restart needed:

```
docker cp ./notes.md ocsbx-review-opencode-1:/workspace/notes.md
```

**Pulling work back out is host-pull only, deliberately** — no credentials ever go into
an instance, so nothing inside it ever needs to reach out with a token:

- **A git branch, with its history.** `opencode-sandbox fetch-url <name>` prints a `git
  fetch` line that speaks git's wire protocol over `docker exec` stdio; run it from your
  project's own repo and the branch, its commits, and its files land locally, ready to
  review before you push with your own credentials. `docker cp`ing a checkout gives you a
  detached directory with no history — use `fetch-url` for anything you'll want to diff
  or merge.
- **The whole workspace.** `opencode-sandbox export <name> <dir>` reads the workspace
  volume directly and copies it to a host directory. It works even while the instance is
  stopped, and refuses to write into a non-empty destination.

**Export before destroying.** `destroy` deletes the workspace volume and everything in
it; `opencode-sandbox export <name> <dir>` is the right last step before that.
