# Waves on Backlog.md

Inventory comes from the `backlog` CLI's JSON output, the triage view is an ignored file beside
the board, and landing a wave is a merge plus one CLI edit per item it closed. Backlog.md is a
tracker and not a forge: closing an item and landing its code are separate acts.

**Every write to a task, decision or doc goes through the `backlog` CLI**, never a hand edit
under `.backlog/`: the CLI owns those files' sections and ids. `.backlog/config.yml` is the one
file edited by hand. Paths below assume the board lives in `.backlog/`; on a board in the
default `backlog/` directory, substitute that.

## Inventory

```sh
backlog task list --json --exclude-status Done   # open tasks: id, title, status, priority, labels, milestone, parentTaskId, isReady
backlog task list --ready --plain                # only tasks whose dependencies are all done
backlog task view <ID> --json                    # one task with its dependencies and body
```

Status names are per board: `backlog config get statuses` lists them, and the last one is the
done status. Substitute it for `Done` where a board renames it. The list includes done tasks
until someone archives them, so always exclude the done status.

Ranking signals, in order: `isReady` → `priority` (high, medium, low) → milestone, then
parent task → labels → owner rulings in the handoff. A task labelled `decision` is owner-gated.

## Triage view

`.backlog/triage.md`, ignored by `.backlog/.gitignore`. It is deliberately not a `backlog doc`:
docs are tracked files, and a refresh must stay off commit history. Read it, edit it, write it
back whole, using the same template as the GitHub triage issue (see `tracker-github.md`, Init)
with refs written as task ids (`TASK-12`). Adapt its GitHub-only lines: drop pinning and the
dependabot and self-exclusion notes, write the merge commit where the plan table says PR when
there is no remote, and take the ranking inputs from this binding. It exists only in the checkout that wrote it, so
write it from the main checkout and record its path in the handoff.

## Landing a wave

**Repo has a remote:** land the wave the way that forge lands code (a PR on GitHub), then
close its tasks.

**No remote:** merge the wave branch into the trunk locally with `git merge --no-ff <branch>`,
run the repo's gates bare on the merge commit (the same battery as Phase 5), then close.

```sh
backlog task edit <ID> -s Done --final-summary "landed <merge-sha or PR>; <how it was verified>"
```

Task files are tracked, so commit the closes on the trunk, one commit per wave:
`tasks: close TASK-3 TASK-7, landed <merge-sha>`. A board with `auto_commit: true` in its
config commits each edit itself; skip that commit there. If a task's work is not actually done,
leave its status alone and run
`backlog task edit <ID> --comment "<what remains>" --add-label needs-review`.

Crews never run `backlog` writes. Keep `.backlog/` out of every brief's owned files.

## Init — seeding the triage view

```sh
printf 'triage.md\n' >> .backlog/.gitignore
```

Seed `.backlog/triage.md` from the GitHub template, with its header saying: **the Backlog.md
tasks are the source of truth; this file is a view, ignored by git so refreshes never touch
commit history.** Commit `.backlog/.gitignore`.

Never create a Backlog.md board just to run waves; the file tracker is the fallback. When the
owner asks for one, `backlog init <name> --agent-instructions none --backlog-dir .backlog
--defaults` creates it without writing a guideline block into the repo's agent-instructions
files.

## Gotchas

- Priority has three levels, so the triage rubric's P0 and P1 both land as `high`.
- `backlog task edit --priority ""` does not clear a priority, and no flag does.
- `-l` replaces a task's whole label set; `--add-label` and `--remove-label` edit it.
- On a repo with no remote, every command warns that `remoteOperations` is on;
  `backlog config set remoteOperations false` silences it.
