# Waves on Kaneo

Inventory and the buildable/owner-gated split read off the board's lanes and labels; the triage
view is a dedicated Document-lane task rewritten in place; landing a wave stays two separate
steps — merge the code on the forge, then close the task on the board.

## Inventory

Pull every open task through the `kaneo` skill's tools, never the MCP `list_tasks` tool for a
full-board read on its own. It fails a wide board two independent ways: it silently clamps
`limit` to 100 and returns a partial page with no error, so a board over 100 tasks looks
complete and isn't (measured: a 107-task project returned 100, and a triage count read 21 where
the truth was 25); and it returns every task description in full, which overflows the reader
before triage starts. Use the `board-triage` skill's Kaneo adapter export — it reads the board's
per-project task endpoint, which returns every task unpaginated — or, if the MCP tool is the
only option, page through `pagination.totalPages` by hand and accept the payload cost.

Per task, capture: id (task number), title, lane (column name — read live, never guess a slug
from the name), and the ranking signals waves needs: labels (including `DECISION`), the priority
field, and relations (`get_task_relations`: subtask / blocks / related) for parent/epic and
blocked-by links. Drop `done` immediately — it is the largest slice of a fresh export and carries
no ranking signal.

## Triage view

Backed by one dedicated task in the Documents lane (`isFinal`, so branch-driven automation can
never drag it out of place), labelled distinctly from ordinary work, refreshed by rewriting its
description in place — the same pattern this kind of board already uses for its session handoff
task. Never a commit; never a new task per session.

Chosen over the lanes themselves as the source: lanes are live work state, mutated by every
claim and status write, so treating a queue lane as the whole plan loses the ranked ordering,
the decision queue, and the delivery-plan table the seam needs to survive a session boundary.
The task description holds all three; the lanes still drive the buildable/owner-gated split
below. Body shape mirrors the GitHub triage issue: a ranked backlog, a decision queue, and the
wave-planning delivery table (`Wave | Branch | Task(s) resolved | Gate`) — refreshed the same
way a session already refreshes its handoff, edited in place, never touching history.

The queue lane (the one positioned just before active work) is the ranked, buildable order at a
glance; an untriaged intake lane earlier in the board is not — never read that lane as ranked or
let a crew self-select from it. Anything blocked on an owner ruling is a `DECISION`-labelled
task parked in Documents, not sitting in the queue lane — a crew never picks up a decision task
to settle it.

## Landing a wave

Two separate steps, because Kaneo is a tracker, not a forge:

1. **Land the code** — merge the PR on the forge, per the base skill's Phase 4. If the board's
   forge integration is wired and the branch is named `<project-slug>-<task-number>[-suffix]`,
   push / PR-open / merge already drive the task through in-progress / in-review / done on their
   own — don't hand-set those for a matched branch. Verify the automation actually landed
   (re-read the column plus a fresh export) rather than trusting that the merge happened.
2. **Close the task** — for anything the automation didn't reach (no integration, an unmatched
   branch, or a task with no linked PR at all), the session does the claim ritual's finish step
   by hand: status `done` via the field-scoped write, plus a closing comment naming what shipped
   and linking the merged PR. There is no PR-keyword close here — a task has no built-in backlink
   the way a forge issue does, so the comment is the only record of what closed it.

## Init — seeding the triage view

No existing task to adopt: create the Documents-lane task per the shape above, seed its
description with an empty ranked-backlog table, a decision-queue section, and an empty delivery
plan, then run the Inventory step once to populate it. A board with an existing untriaged
backlog (not one `waves` filed itself) is migrated with the `kaneo` skill's onboarding script,
never by hand — creating tasks one at a time, or fanning that out across agents, is exactly the
bulk-data-movement mistake that script exists to avoid.

## Gotchas

- `list_tasks` clamps `limit` to 100 with no error — a wide board silently loses its tail; the
  Inventory step above must page or use the unpaginated export path, not the raw MCP call.
- Bulk status writes can be reverted seconds later by an unattributed write and still report as
  applied. A single-field status write plus a delayed re-read is the only proof a lane move
  landed — never trust a writer's own success line for a wave's status moves.
- Full-object task replace is a full-object REPLACE, not a merge, and 400s on a partial body.
  Field-scoped writes (assignee, status, priority) avoid this entirely; prefer them for every
  wave-driven write, including the triage-view task's own updates where a field-scoped route
  exists.
- Claiming is a root-session-only ritual; a wave's crews get read-only board access (list, read,
  comment, create), never claim or status authority — the base skill's "crews build, the session
  merges" rule is enforced here by the board's own access model, not just convention.
- Branch-driven automation only fires on a matched branch name; an unmatched one falls back to
  scanning the PR title and body for a task number and cannot tell that number from a forge
  issue reference — name wave branches correctly or the wrong task moves.
