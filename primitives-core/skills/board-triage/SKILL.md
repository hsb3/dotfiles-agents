---
name: board-triage
description: >-
  This skill should be used when the user asks to "run board triage", "triage the
  backlog", "prioritize the issues", "rank the unranked issues", "fill in
  Impact/Effort/Priority", "do the weekly triage", or wants the untriaged items on a
  task board classified so the prioritization/now/roadmap views become useful. It runs
  the export -> analyze -> apply loop: pull a snapshot, find the un-ranked/blank/stale
  items, rank them by the Impact x Effort rubric, and apply only the diffs. The
  judgment is backend-agnostic; a thin adapter does the board's I/O (kata, GitHub
  Projects v2, and Kaneo adapters ship; any board with items and fields can have one).
version: 0.2.0
---

# board-triage — the prioritization pass, whatever the board runs on

Turn a board full of captured-but-unranked items into a ranked, workable backlog, as a fast
repeatable pass. Built on the **export → analyze → apply** loop so auth stays local, the analyst
judges over a clean snapshot, and every change lands as a reviewable diff.

**The judgment lives here. The I/O lives in an adapter.** Nothing on this page names a backend;
everything backend-specific — how to pull a snapshot, how to write a cell, which rubric outputs
the board can actually store — is in one adapter file. A new backend is a new adapter file and no
edit to this page.

## When to run
The weekly (or per-sprint) pass, or any time the prioritization views look thin because items
carry no priority. The board is the source of truth; this keeps it honest.

## 1. Pick the adapter

| Backend | Adapter |
|---|---|
| GitHub Projects (v2) | [`references/adapters/github-projects.md`](references/adapters/github-projects.md) |
| Kaneo | [`references/adapters/kaneo.md`](references/adapters/kaneo.md) |
| Kata | [`references/adapters/kata.md`](references/adapters/kata.md) |

No adapter for your board? Write one against §2 — it is two commands and a field map.

## 2. The adapter contract

Every adapter supplies the same three artifacts, so §3–§5 never change.

**Snapshot** — one JSON document the analyst can read whole:

```json
{ "board":  {"name": "...", "backend": "..."},
  "fields": {"<field>": {"options": ["..."]}},
  "items":  [{"key": 232, "id": "<backend handle>", "title": "...", "state": "open",
              "labels": ["..."], "fields": {"priority": null, "status": "to-do"}}] }
```

- `key` is the **durable human handle** (issue number, task number) — changesets key on it, and
  apply re-resolves `key` → `id` from a fresh pull every run, so a stale changeset cannot write
  to the wrong item.
- `fields` is a **complete grid** of every operating field, `null` when unset — blanks have to be
  visible or triage cannot find its work.
- **No long bodies.** Labels and titles carry the board's signal; deep context comes from the
  repo's plan/spec/issue text, not the snapshot. A snapshot that overflows the analyst's context
  is a broken adapter.

**Changeset** — a TSV diff the analyst writes, one row per cell being changed, never the whole
board:

```
key	field	value
232	priority	P1
232	status	up-next
503	labels	infra,backend
```

Values are option **names**, not ids. An empty value clears the cell.

**Apply** — the adapter's writer re-pulls a fresh snapshot, resolves each `field` token against
the board's live fields, writes **only cells that differ**, is **dry-run by default**, is
idempotent, and exits non-zero on any failure.

**Field map** — each adapter states where every rubric output lands on that backend, and names
any output the backend has no home for. An unmapped output is **reported, never fabricated into
some other field.**

## 3. The rubric

The rubric emits a priority band `P0`–`P3` from Impact × Effort. Whether the board spells that
`P1`, `high`, or `2` is the adapter's field map, not this table's problem.

| | Effort S/M | Effort L/XL |
|---|---|---|
| **Impact High** | **P0–P1** (do first) | **P1–P2** (plan / decompose) |
| **Impact Low** | **P2–P3** (fill-in) | **P3** (probably don't) |

**Override:** a **dated critical path** (demo, stage gate, external commitment) forces **P0**
regardless of effort.

## 4. Procedure

1. **Snapshot.** Run the adapter's export command; read the JSON it writes.
2. **Find the work.** List items whose priority is null (untriaged), plus anything whose ranking
   looks stale — a top-band item no longer on a dated path, a blocked item whose blocker closed.
   **Drop everything the snapshot marks `state: done` first.** A rank on a closed item changes
   nothing and buries the live work; on a board that never triaged before, closed items are
   usually most of the blank cells.
3. **Judge — don't guess.** For each item, pull context from the **repo's** plan/spec/issue text
   (not the board), then apply §3. Skip epics (containers) and owner-gated or non-buildable
   items. Where there is no context to judge from, leave it blank and flag it.
4. **Emit the changeset.** One row per cell, per §2.
5. **Preview, then apply.** Run the adapter's writer dry first, read the diff, then apply.
6. **Promote.** Ready top-band items move to the board's ready lane, same changeset mechanism.

## 5. Discipline

- Every triaged item leaves with a priority band and a grouping value — that is the pass's
  definition of done.
- A dated critical path forces the top band regardless of effort.
- Don't invent Impact/Effort for items you can't see. An honest blank beats a fabricated rank —
  the next pass, or the owner, fills it. An owner-gated item (one whose scope is a decision, not
  a build) leaves blank too, and gets flagged.
- Ranking is not the only output. A pass that reads every untriaged item is the pass most likely
  to notice a duplicate, or a closed item whose defect is demonstrably still live — say so
  instead of quietly assigning it a band.
- Triage is meant to be cheap and frequent. Resist adding required fields; each one is a cell to
  fill on every pass.
- The snapshot file **is** the hand-off seam. An analyst that cannot reach the board reads the
  snapshot and returns a changeset — no special agent, no extra protocol, and the party holding
  the credentials runs both commands.
