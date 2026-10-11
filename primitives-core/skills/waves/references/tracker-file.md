# Waves on the file tracker

One Markdown file per item under `.tasks/`, specified in
[`file-tracker-format.md`](file-tracker-format.md). It is the tracker that always works, and
the fallback when a repo has no other. Inventory is a parse of the item files, the triage view
is the ignored `.tasks/triage.md`, and landing a wave is a merge plus an edit to each item it
closed. Like kata, this is a tracker and not a forge: closing an item and landing its code are
separate acts.

## Inventory

<!-- harness:claude-code -->
```sh
python3 <waves-skill-dir>/scripts/file_tracker.py list         # open items, one per line
python3 <waves-skill-dir>/scripts/file_tracker.py list --all   # done and dropped too
```

Each line is id, priority, `ready` or `blocked by <ids>`, labels, title; the footer counts
open, ready and closed items and names the next free id. Exit 1 means an item file is broken
(`BROKEN <path>: <why>` on stderr). Fix it before triaging: a file the parser cannot read is an
item the plan cannot see.
<!-- /harness -->

Ranking signals, in order: ready before blocked → `priority` → `labels` (an `epic` container,
then area) → owner rulings in the handoff. An item labelled `decision` is owner-gated.

## Triage view

`.tasks/triage.md`, ignored by `.tasks/.gitignore`. Read it, edit it, write it back whole. Use
the same template as the GitHub triage issue (see `tracker-github.md`, Init), with refs written
as `t<n>`. Write it from the main checkout, never from a worktree, because it exists only in the
checkout that wrote it; record its path in the handoff.

## Landing a wave

**Repo has a remote:** land the wave the way that forge lands code (a PR on GitHub), then
close its items.

**No remote:** merge the wave branch into the trunk locally with `git merge --no-ff <branch>`,
run the repo's gates bare on the merge commit (the same battery as Phase 5), then close.

To close, for each item: set `status: done` and append a Log line,
`- <date> done: landed <merge-sha or PR>; <how it was verified>`. Commit the closes on the
trunk, one commit per wave: `tasks: close t3 t7, landed <merge-sha>`. If an item's work is not
actually done, leave it open, append a Log line saying what remains, and add the
`needs-review` label.

Crews never edit `.tasks/`. Keep it out of every brief's owned files, so a crew diff that
touches it fails Phase 4's owned-files check.

## Init — seeding the triage view

```sh
mkdir -p .tasks && printf 'triage.md\n' > .tasks/.gitignore
```

Seed `.tasks/triage.md` from the GitHub template, with its header saying: **the item files in
`.tasks/` are the source of truth; this file is a view, ignored by git so refreshes never touch
commit history.** Commit `.tasks/.gitignore` and any item files; the view itself stays
untracked.

When `.tasks/` did not exist because no tracker was found, say so in your first message
("no tracker found; falling back to the file tracker at `.tasks/`") before creating it.

## Gotchas

- A worktree or a fresh clone has no triage view. Rebuild it from the item files rather than
  copying a stale one across.
- Concurrent sessions can mint the same id, and git reports it as an add/add conflict on
  `.tasks/t<n>.md`. Renumber the later item and every `blocked-by` that names it.
- An item's history is `git log -- .tasks/t<n>.md`; the format keeps no dates of its own.
