# The file tracker format

The tracker that always works: plain Markdown files in the repo, readable with no tool and
parseable by a short stdlib script. It is the fallback when a repo has no kata board, no GitHub
issues in use and no Backlog.md board, and it is a complete tracker in its own right.

## Where it lives

- `.tasks/` at the repo root. Its presence is what detection looks for. When no tracker is
  found, the first write creates it, and the session says so.
- One file per item: `.tasks/t<n>.md`. A closed item stays where it is (its `status` changes,
  its path never does), so a ref never dangles.
- Item files are **tracked in git**. They are the inventory, and in a repo with no remote, git
  is the only durable copy.
- The triage view is `.tasks/triage.md`, **ignored** by `.tasks/.gitignore` (one line:
  `triage.md`), so refreshing it never touches commit history.

## Ids

- `t<n>`, where n is 1 + the highest number ever used in `.tasks/`, closed items included.
  Never reused.
- Two branches that mint the same id collide as a git add/add conflict on `.tasks/t<n>.md`.
  That is loud, and the fix is to renumber the later one. Only the session files items, so this
  happens only between concurrent sessions; if concurrent filing becomes routine, move to
  random short ids.

## Item file

```markdown
---
id: t12
title: Time out hung scans and kill the scanner process tree
status: open
priority: P1
labels: [type:fix, area:scanner]
blocked-by: [t9]
---
Free markdown: the description, then a `## Acceptance criteria` checklist.

## Log
- 2026-10-11 triage: P1, high impact, effort M, on the demo path
- 2026-10-12 done: landed 3f2a91c; scan ends in 4s, the regression test failed before the fix
```

Every file carries every key, in this order. An empty value means unset: `priority:` for a
scalar, `[]` for a list.

| Field | Values | Notes |
|---|---|---|
| `id` | `t<n>` | equals the filename |
| `title` | one line, never empty | |
| `status` | `open` / `done` / `dropped` | no in-progress lane; readiness is computed from `blocked-by` |
| `priority` | `P0`-`P3`, or empty | the triage rubric's band stored verbatim; empty means untriaged |
| `labels` | `[a, b]` | a free set; a project's label vocabulary applies as on any board; an owner-gated item carries `decision` |
| `blocked-by` | `[t<n>, ...]` | real prerequisites only; an item is ready when every blocker is `done` or `dropped` |

**Body:** free markdown. `## Log` is always the last section: dated lines, append-only. It does
the job of comments: triage reasoning, owner rulings, and close evidence (`done: landed <sha or
PR>` plus how it was verified).

**Grammar:** line-based, and not YAML. The frontmatter sits between the first two `---` lines,
one `key: value` per line, split on the first `: `. A list is `[a, b]` on one line and nothing
else. A file that breaks this is an error reported by its path, never skipped quietly: a missing,
unknown, duplicate or out-of-order key, a block list, an empty title, an id that differs from
the filename, an unknown status or priority, a `blocked-by` that names no item, and a `.md` file
in `.tasks/` that is neither an item nor `triage.md`.

## Writes

- Plain file edits, no CLI. Only the session writes `.tasks/`; a crew's diff that touches it is
  outside its owned files.
- To close an item, set `status: done` (or `dropped`) and append a Log line with the evidence.
  Closes for one landing go in one commit on the trunk after it lands:
  `tasks: close t3 t7, landed <merge-sha>`.
- A triage pass writes `priority` and `labels` in place and commits the pass as one commit.
- To file an item, take the next id, write every key, and commit it. `priority` and `labels`
  may stay empty until the next triage pass; several filings can share one commit.

## The triage view

`.tasks/triage.md` uses the same template as a GitHub or kata triage view (Now / Milestone /
Backlog / On hold / Decision gaps / Delivery history / Maintenance protocol), with refs written
as `t<n>`. Its header states that the item files are the source of truth and the view is a view
of them. The handoff records its path.

Known ceiling: the view is untracked, so it exists only in the checkout that wrote it, not in
worktrees or other clones, and its delivery history goes with it. That is acceptable for a view
rebuilt from the item files; tracking it would put every refresh into commit history.

## Left out on purpose

- Assignee or claims: the session is the only writer.
- Created and updated dates: `git log` has them.
- A parent or epic field: grouping is done with labels, and `epic` marks a container.
- Milestones: use a label or a triage-view section.

<!-- harness:claude-code -->
## The parser

`scripts/file_tracker.py` in this skill implements the grammar above, stdlib only, run from the
repo root (`--root` points it elsewhere):

| Command | Does |
|---|---|
| `detect` | names the tracker in play and why: `kata`, `github`, `backlog` or `file`; a `tracker:` key in `.claude/tracker.local.md` wins over detection |
| `list [--all]` | one line per open item: id, priority, `ready`, `owner-gated` (labelled `decision`) or `blocked by ...`, labels, title; a footer with counts and the next id |
| `export [--out FILE]` | a triage snapshot of the open items |
| `apply --changeset FILE [--apply]` | writes `priority`/`labels` cells that differ; dry-run by default |

A broken file prints as `BROKEN <path>: <why>` on stderr. `list` still prints what parsed and
exits 1; `export` and `apply` refuse to run until the tracker parses clean.
<!-- /harness -->
