# Waves on kata

Inventory and ranking come straight from `kata list`/`kata ready`. The triage view is the body
of a dedicated epic issue, rewritten in place with `kata edit --body`. Landing code is a separate
step from closing the kata item — kata is a tracker, not a forge.

## Inventory

```sh
kata list --project <name> --status open --json
```

Fields per issue: `short_id` (the ref — legacy numeric refs don't resolve), `title`, `status`,
`priority` (0-4, 0 highest), `labels`, `parent` (epic link), `blocked_by`/`blocks`
(dependency edges), `blocked` (bool: true if any blocker is still open), `child_counts`
(open/total, on epics). Use `--agent` instead of `--json` for a human-scannable pass; drop to
`--json` when a script needs to sort or filter.

Ranking signals, in order: `blocked` false (unblocked work first — see `kata ready` below) →
`priority` → `parent`/epic grouping → `labels`.

```sh
kata ready --project <name> --limit 50 --agent      # open issues with no open blocker, ready now
kata next --project <name> --unowned --agent        # single highest-priority ready pick
```

`ready`/`next` already resolve the dependency graph (`blocked_by`) for you — don't re-derive it
by hand from `blocked_by` arrays unless you need the raw edges (e.g. to explain *why* something
is blocked).

## Labels

Labels are the grouping a wave plans against, so they carry the whole classification — a title
prefix is not queryable and does not count. The core vocabulary is a closed set of names plus
one family: exactly one type label per item from type:feat, type:fix or type:chore; the
container and behaviour labels epic, decision, handoff, meta, needs-review and up-next; and
exactly one area label, whose values each project defines for itself. A project adds labels on
top of that core, never instead of it.

Declaring the core somewhere a tool can read matters for one check: `board_health.py` takes
`--vocabulary <file>`, a declared label list, one name per line. Without it the tool has only
the board's own label options — derived from its whole history, retired names included — so its
fossil check is skipped rather than answered.

## Triage view

Backed by **one epic issue's body**, rewritten wholesale — the closest kata analog to a pinned
GitHub issue. `kata edit --body` replaces the body outright (not append), the daemon's event log
is not git history, and `kata show --render` / `kata tui` / `kata ui` give the owner a
non-session read.

```sh
kata show <epic-ref> --render                       # read the current triage view
kata edit <epic-ref> --body "$(cat /tmp/triage.md)"  # full rewrite, same shape as the GitHub body
kata comment <epic-ref> --body "refreshed $(date +%F)"  # optional pointer comment, don't rely on it for content
```

Use the same body template as the GitHub triage issue (Now / Milestone / Backlog / On hold /
Decision gaps / Delivery history) — kata renders markdown identically. `--comment` on `edit` can
append a changelog line after the mutation if a history-of-refreshes matters; the body itself
stays the durable copy.

## Landing a wave

Kata never merges code and has no PR-keyword auto-close — closing the kata item and landing the
branch are always two separate acts here.

**Repo has a GitHub remote:** land the wave as a normal PR, then close the kata item pointing at
it (kata doesn't parse close keywords out of PR bodies):

```sh
kata close <ref> --done --message "<what shipped and how it was verified>" --pr <pr-url>
```

`kata sync github` (enable/once/status) imports GitHub *issues* into kata if that sync is on.
It is one-way — a kata card never becomes a GitHub issue — and it does not link PRs or
auto-close on merge; treat it as orthogonal to landing a wave. An imported mirror is an epic to
decompose into native children, not a card to rewrite: the sync owns a mirror's body.

**No GitHub remote** (a project whose only backlog is a kata board): land on a local integration
branch gated by the repo's own DoD (tests/build run bare on the merge commit, same as Phase 5's
"full gate battery"), then close with the commit as evidence:

```sh
kata close <ref> --done --message "<what shipped and how it was verified>" --commit <sha>
```

Either path: close each item as its own wave verifies, not in a batch at the end (kata's own
guidance — `kata quickstart`). If a wave's work isn't actually done, don't close:
`kata label add <ref> needs-review` plus `kata comment <ref> --body "..."`.

## Init — seeding the triage view

```sh
kata init --project <name>                 # bind the workspace if .kata.toml doesn't exist yet
kata create "waves: triage (living plan)" --label meta \
  --body "$(cat <<'EOF'
... same template as /waves init, GitHub section swapped for kata commands ...
EOF
)"
```

If the project already has a natural epic (a parent issue with several child tasks under it),
reuse that epic's body as the triage view instead of creating a second one; record its ref in
the handoff so future sessions find it by pointer.

## Gotchas

- `--project` takes the **project name**, never the numeric `project_id` from JSON output —
  `kata list --project 57` fails `project 57 is not registered` (exit 4); use the string from
  `kata projects list`.
- Issue refs are `short_id`s (e.g. `abc4`) or `project#short_id` across projects — legacy numeric
  refs no longer resolve at all.
- `kata edit --body` overwrites the whole body; there's no patch/append mode for it — build the
  full markdown string first, same discipline as rewriting a GitHub issue body.
- `blocked_by`/`blocks`/`related`/`parent` are separate relationship types: `parent` is
  containment only and does not gate readiness; only `blocked_by` gates `kata ready`.
- No cross-tool PR-close linking: `--pr`/`--commit` on `kata close` are evidence strings, not
  live links kata verifies — the close is still a manual, separate command from the merge.
