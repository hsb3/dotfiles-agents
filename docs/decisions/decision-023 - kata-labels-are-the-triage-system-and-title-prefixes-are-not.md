---
id: decision-023
title: kata labels are the triage system and title prefixes are not
date: '2026-09-08'
status: accepted
---
## Context

The shipped doctrine contradicted itself about where a card's grouping lives. `task-authoring`
forbade `feat:`/`fix:`/`chore:` title prefixes — "labels carry type; the prefix burns the
highest-value characters in the title" — and prescribed the shape `area: outcome` four lines
above it, so it banned one prefix family and mandated another for the same reason it banned the
first. `board-triage`'s own `grouping-latent` check already treats a prefix convention as a
smell: it fires when a board's grouping lives in title text no query can filter on. The skill
that authors the card and the skill that audits the board disagreed, and the board they both ran
on followed the authoring skill.

Nothing named a core vocabulary that crosses projects, either. AGENTS.md's "board conventions"
paragraph is real and enforced by habit, but it is *this repo's* paragraph — a convention that
lives in one repo's law file cannot be the default anywhere else.

Derived live across the 30 kata boards with open work, 2026-09-08 (counts as of that date; the
boards grow):

- 817 open items carrying 143 distinct labels.
- 161 of those label uses are still `kaneo-status:*` — residue from a tracker this repo retired
  on 2026-09-02 (decision-014), never swept anywhere.
- `type` is spelled eleven ways: `bug`, `feature`, `enhancement`, `task`, `chore`, `doc`,
  `docs`, `documentation`, `type:feat`, `type:fix`, `type:chore`.
- On three of the boards most open items carry no label at all.

143 label names over 817 items is not a vocabulary; it is a per-board dialect apiece. Raised on
kata cards `k1x9` and `3pyz`.

## Decision

Owner ruling, 2026-09-08 (sign-off item D), ratified as proposed.

1. **Labels are the triage system. Titles carry no prefix of any kind.** A title is the outcome
   in one clause, 70 characters or fewer. An `area:` or `type:` prefix in a title is the same
   defect as a `feat:` prefix: it puts the grouping where no query can reach it and spends the
   characters a scanner reads first.
2. **Type, exactly one of** `type:feat`, `type:fix`, `type:chore`.
3. **Containers and behaviour:** `epic`, `decision`, `handoff`, `meta`, `needs-review`,
   `up-next`.
4. **`area:<x>`, exactly one, project-defined.** It is the only per-project family: the names are
   a project's business, the shape is not.
5. **Retired outright:** `bug`, `feature`, `enhancement`, `task`, `chore`, `doc`, `docs`,
   `documentation`, and every `kaneo-status:*`.
6. **A project may add labels on top of the core, never instead of it.** A board that renames
   `type:fix` to `bug` is off the vocabulary; a board that adds `owner-gated` on top of the core
   is not.
7. **The core is declared in one tracked file** — `primitives-core/skills/board-triage/scripts/core-labels.txt`,
   one name per line — which is what `board_health.py --vocabulary` reads. Before that file
   existed, the script's `vocabulary-fossils` check was SKIPped on every run for want of a
   declaration, because **a board's own label history is not a declaration**: an adapter derives
   it from closed work too, so a check fed from it can never go green. `area:<x>` is deliberately
   absent from the file — a family has no fixed name to declare.

## Relationship to decision-016

The two vocabularies are not the same set, and a reader who meets them a week apart will assume
they are.

decision-016 closes **this repo's GitHub label set** at exactly `type:feat`, `type:fix`,
`type:chore`, `decision`, `epic`, enforced by `scripts/check_labels.py` against the live repo.
That set is a **subset** of the core declared above. The board-only names — `handoff`, `meta`,
`needs-review`, `up-next`, and the whole `area:*` family — never reach GitHub, because kata's
GitHub sync here is import-only and board labels do not propagate outward. `make labels` is what
proves it: it reads the live GitHub set against decision-016's closed vocabulary and would go red
the first time a board label appeared there.

The subset relation is pinned by a stdlib test so the two cannot drift apart silently — a name
added to decision-016's closed set and not to the core file is red. Nothing in decision-016
changes: its set, its gate, and its CI-only placement all stand as written.

## Consequences

- **`task-authoring` now states the whole title rule** and stops carrying the `area: outcome`
  shape (card `6nv9`, same PR). Its kind-prefixes for non-work items (`DECISION:`, `REF:`,
  `HANDOFF —`) go the same way under point 1: `decision`, `handoff` and `meta` are labels in the
  core, so the prefix only repeats what the label already sorts.
- **AGENTS.md's board-conventions paragraph points here** instead of restating the vocabulary.
  One copy of a rule: a restatement in a law file is exactly the thing that goes stale the first
  time this record is amended.
- **The `board-triage` kata adapter and the `waves` kata tracker reference name the core set as
  the default `--vocabulary`**, so `vocabulary-fossils` stops skipping on an ordinary run.
- **A relabel script and a label map land with this record** (card `wf9y`), dry-run by default.
  **The sweep across the other 29 boards is an owner decision and is not executed by this
  record** — relabelling that many open items is a change to working state on boards this repo
  does not own, and a script that is safe to run is not the same thing as permission to run it.
- **`solo-skills`, `mise-en-place`, `code-desk` and `atelier` ship changed bytes and bump** per
  `check_version_bump.py`.

## Open question: where documentation work goes

`doc`, `docs` and `documentation` retire into `type:chore` under point 5, which loses the one
fact they carried — that an item is documentation work. Whether `area:docs` joins the area
vocabulary as the replacement is an owner call, and **this record does not make it**. Until it
is made, documentation work is `type:chore` plus whichever `area:*` its subject already sits in.

**Amended 2026-09-08 — the call is made: `area:docs` is a core area.** The owner ruled that
documentation is a domain, not a kind of work, so `doc`, `docs` and `documentation` map to
`area:docs` rather than to `type:chore`, and the rename is **additive**: it supplies the area
and the card still needs one of `type:feat|fix|chore`. `area:docs` is the one `area:` name the
core vocabulary recognises, so a board may use it without adding it to its own area list. It is
recorded in `core-labels.txt` as a comment and not as a declared line, because a declared name
is checked against open items and every board with no open documentation work would otherwise
report a permanent vocabulary fossil. The paragraph above stands as the record of what was open;
this note is what closed it.
