# board-triage

Runs the prioritization pass over a task board: pulls a compact snapshot, finds the items
missing a rank (or carrying a stale one), judges each against the repo's own plan/issue
context, and applies only the diff rather than guessing a rank it can't justify. Turns a
board full of captured-but-unranked items into a workable, ranked backlog.

The judgment is backend-agnostic and lives in `SKILL.md`. The board's I/O lives in a thin
adapter under `references/adapters/` — **GitHub Projects (v2)** and **Kata**
ship, each with its own export/apply script in `scripts/`. A new backend is a new adapter
file: two commands and a field map, no edit to the rubric.

Every adapter writes only on `--apply`. The default run is a preview you read first, and it
refuses the same rows the write would, so an unresolvable changeset is caught before it
touches the board. A refused row is a failure on every adapter alike: it prints as a `SKIP` on
stderr and the run exits non-zero, while the rows that did resolve are still applied. So
`apply || abort` behaves the same whichever board is underneath. Both diagnostics go to
stderr — a `SKIP` for a row the adapter refused, a `FAIL` for one the board rejected — so
stdout is only ever the row log, and piping it into a diff or a counter never has to
filter them out.

## Deciding whether a pass is due

`scripts/board_health.py <snapshot.json>` (or on stdin) is the other half: six decay checks
that answer whether the board has rotted enough to be worth a pass, and afterwards whether the
pass took. It reads the same §2 snapshot every adapter already emits, so it is backend-agnostic
for free and talks to no board itself.

One of the six needs an input the board cannot supply: `--vocabulary` takes a declared label
list, one name per line, and `scripts/core-labels.txt` ships as that declaration. Without it
the fossil check reports SKIP on every run, because the only label set a snapshot carries is
derived from the board's whole history and so can never go green. The shipped file holds the
core vocabulary — one type label, the container and behaviour names — and deliberately no area
name, since areas are each project's own. `area:docs` is the single exception and is recorded
there as a comment rather than as a declared line (owner ruling 2026-09-08): it is recognised as
core, so a board may use it without adding it to its own list, but declaring it would make every
board with no open documentation work report a fossil it could never clear. A project that adds labels on top of the core points
`--vocabulary` at its own copy. On a board that has not adopted the vocabulary yet, read the
fossil finding as the adoption gap rather than as retired vocabulary — the adapter says so.
A project with no open items exports as an empty snapshot rather than crashing, and every
check then has nothing to judge, which is not the same answer as a clean board.

It measures whether a field **discriminates**, not just whether it is filled — a priority band
holding most of the backlog, items with no band or no label at all, a grouping convention living
in title prefixes that no filter can reach, and two spellings of one concept splitting it across
two filters. Exit 0 is clean, 1 is any finding, 2 is an input it could not read. `--json` for
machine output; `--skew-threshold` and `--prefix-threshold` tune it for a board with different
norms. Every check that can fail judges open items only, so a board's retired label history can
never hold it red; `grouping-latent` is the one documented exception, and SKILL.md says why.

## Putting a board back on the vocabulary

`scripts/relabel_board.py` migrates one project's labels onto the core set: it reads the
rename table in `scripts/label-map.yaml` beside it, computes the minimum label delta per open
card, and prints the plan. **It is a dry run unless `APPLY=1` is set in the environment** — not
a flag, so it cannot be half-typed into a live run, and every mutating call goes through the
one place that checks it. Three things it refuses to do rather than guess: it skips a GitHub
mirror (the sync owns a mirror's labels and re-applies them), it plans nothing at all for a
card that would end up with two `type:` or two `area:` labels, and it reports a label absent
from the map instead of inventing a home for it. The map is the only file that changes when a
mapping decision changes, and a label deliberately left out of it is a decision, not an
oversight. The two-of-a-family veto is not hypothetical: `doc`/`docs`/`documentation` rename
onto `area:docs` under that ruling, additively — the card still needs a type — so a card that
already carries its own area is reported rather than given a second one. An apply that fails
partway stops, prints every operation that had already
landed, and exits 3 rather than 1, so a wrapper can tell a half-written board from a list
of findings. Title-prefix promotion is a separate mode, `--strip-prefixes`, off by default and
inert unless the caller supplies that project's area list with `--areas` — with no list it
promotes nothing and reports every prefixed title, which is the fail-safe.

The Kata adapter also states how kata's import-only GitHub sync constrains the loop: a mirror is an
epic to decompose, and anything rewritten in place must be a native card.

Triage is one move in a longer loop, and its tools are split across plugins. The Kata adapter
writes that loop out end to end — wiring check, per-card definition audit, health check, the
pass, health again — under "The maintenance rhythm", including why a per-card audit and a
whole-board health check are not redundant.

**Every check reads open items only, the label ones included.** An adapter builds
`fields.labels.options` from the board's whole history, so a label surviving on closed cards is
not a live vocabulary and no edit to open work could ever clear it — judging a live board by its
history is how a check ends up permanently red, which is the noise this script exists to remove.

That makes the fossil check meaningless without a real declaration, so it takes one:
`--vocabulary FILE`, one label per line, `#` comments ignored. Without it the check is **skipped
and says so in the report** rather than quietly omitted, and a skip never affects the exit code.
`scripts/check_labels.py`'s `VOCABULARY` constant in this repo is exactly the kind of declaration
it consumes — a closed set someone chose, not a set the board accumulated.

## Reconcile GitHub mirrors

`scripts/reconcile_github.py [--project <name>] [--apply]` compares the selected Kata
project with the GitHub repository selected by `gh` in the consuming checkout. Omit
`--project` to use Kata's normal checkout selection. Run against the repository that
project imports. Dry-run reports tracked, stale and untracked issues; only `--apply`
closes stale mirrors. It never creates cards or issues. Reverse drift is informational.
GitHub reads are capped at 500 issues per state; larger repositories need a pagination
change before this can serve as a complete sweep. The Kata adapter reference documents
the separate kata plugin required for wiring and per-card definition audits.

## When it triggers

Use it to "run board triage", "triage the backlog", "prioritize the issues", "rank the
unranked issues", "fill in Impact/Effort/Priority", or "do the weekly triage" so the
prioritization and roadmap views become useful instead of drifting into noise.

## Install

```
claude plugin install board-desk@dotfiles-agents
```

Ships in the `board-desk` bundle. Every adapter is self-contained — no second plugin to
install. What each one needs is the backend's own client: the GitHub Projects adapter wants
`gh` authenticated with `project` scope (`gh auth refresh -s project`), the Kata adapter
wants the `kata` binary pointed at the right daemon. Each adapter says so at the
top of its own file, and carries its backend's one-time setup (project/board creation, field
provisioning, views and workflows) alongside the day-to-day export/apply commands. Where a
setup step is a board write rather than a read, the adapter says so at that step and names
the legal values, so a snippet is never copied blind.

Codex uses the same Kata and GitHub board adapters. Resolve bundled scripts from the installed
skill path; adapter prerequisites and write authorization remain part of the board workflow.
