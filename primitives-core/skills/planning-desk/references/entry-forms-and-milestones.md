# Standards: backlog / bench entry forms + the shared milestone set

Two cross-project standards the planning desk enforces. They answer *what shape a unit of work takes
to enter a queue* (the entry forms) and *what gate/milestone vocabulary a board speaks* (the shared
milestone set). Cite them from item/plan authoring and from board setup; do not restate their fields
inline elsewhere — link here.

- **Origin:** the ratified `use-case-driven-backlog` decision (an extender enters a queue because a
  named project or workflow needs it, ranked by how soon the need is real; the vendor/resources list
  is a sourcing catalog, not a backlog). Formalizes what the originating backlog request asked for;
  the bench form is the owner amendment (2026-07-11).
- **Status:** the entry-form core fields and the milestone-set vocabulary are grounded in shipped
  practice below; the unranked-wishlist rule was ratified by owner ruling 2026-07-12.

---

## Part 1 — Entry forms

A "well-defined unit of work" does not enter a queue as a bare title. It enters carrying a fixed set
of fields so it can be ranked, picked up cold, and judged. There is **one shared core**, then **two
applications** of it: the backlog-entry form (a use case entering a project backlog) and the
bench-entry form (a candidate entering `<incubator-repo>/incubator/`).

### The shared core (both forms carry these)

| Field | What it states | Independently verifiable by |
| --- | --- | --- |
| Driving use case | the named project or workflow that needs this, and how soon the need is real (not "would be nice") | a reader can name the project/workflow and its need |
| Deliverables | what gets built, named to file/target/endpoint so no rediscovery is needed | each deliverable names a concrete artifact |
| Acceptance criteria | how it is judged, each check independently verifiable by someone who did not build it | "X returns Y", "test Z passes", "gate fails on drift" — never "works well" |
| Known overlaps | existing primitives/candidates this duplicates or supersedes; if it supersedes one, which | a reader can check the named item is or is not a near-duplicate |
| Source pointers | where the driving material lives — `path:line`, a linked tracker ref, a decision record | each pointer resolves |

**Machine-agnostic:** source pointers and deliverables use repo-relative paths or tracker refs, never
machine-absolute paths (`/Users/...`), personal vault names, or `~/Documents|Desktop` locations.

### Application A — backlog-entry form (a use case enters a project backlog)

A use case enters the backlog as a **tracked work item** whose body carries the sections the desk's
conformance gate keys on — the same bar `_utils/conformance.py` enforces and the `task-authoring`
skill writes to, so the entry form and the item-body standard are the same gate. The shared core maps
onto the item body:

| Core field | Lands in the item body as | Notes |
| --- | --- | --- |
| Driving use case | opening framing / `> Tracking:` blockquote | the "why now"; cites the decision or the requesting project |
| Deliverables | **Deliverables** section | file/endpoint targets named |
| Acceptance criteria | **Acceptance criteria** section (required) | conformance gate keys on this heading |
| Known overlaps | **Dependencies & gates** (required) or Deliverables | name superseded/near-dup items or primitives |
| Source pointers | inline `path:line` / a linked tracker ref throughout | grounds every load-bearing claim |

**Representation choice — which shape:** an entry is a **project-task item** (the default: one
feature-sized item on the board). A **user story** is the *framing inside* the Driving-use-case field
("as \<role\> I need \<capability\> so \<outcome\>"), not a separate artifact. A **feature-spec link**
is used when the deliverable is large enough to warrant its own plan — the item links to
`_meta/plans/<slug>/` rather than inlining the detail. One item is the unit; the story frames it; the
spec link carries the depth.

**Ranked-vs-unranked:** an idea with no driving use case yet claimed enters as an *unranked
wishlist* entry — one line, "no use case claimed yet; per `use-case-driven-backlog` it waits until one
does" — not as a ready item. It is promoted to a full backlog item only when a named near-term use
case claims it. (Grounded in the backlog-seed plan's owner-decision default; ratified as a
standing rule by owner ruling 2026-07-12.)

### Application B — bench-entry form (a candidate enters the incubator)

A candidate enters `<incubator-repo>/incubator/<name>/` only with a **scope doc** carrying the
shared core, mapped onto the promotion gate's H/J checks so the entry is gate-ready from day one:

| Core field | In the scope doc as | Maps to gate check |
| --- | --- | --- |
| Driving use case | the **J1 hypothesis** — the ≥2-real-uses proof this candidate is expected to earn | J1 (proven ≥2 real uses) |
| Deliverables | what the candidate builds (the extender itself + its evidence trail) | — |
| Acceptance criteria | mapped to the **H/J gate** — which hard checks (H1/H2/H4/H5) it must pass and the J attestations it targets | H1/H2/H4/H5 + J1–J4 |
| Known overlaps | the **J4** statement — not a duplicate; if it supersedes a primitive, which | J4 (distinct) |
| Source pointers | where the driving material and prior art live | — |

The scope doc is the incubation-stage companion to the `REGISTRY.md` row; it states the *bet* (J1
hypothesis) up front so incubation accumulates the right evidence. The gate itself
(`<incubator-repo>/docs/promotion-gate.md`) and the pipeline
(`docs/extender-lifecycle.md`) are canonical for pass/fail — this form governs *entry*, not
qualification.

### Where the forms are cited

- **Backlog seed**: the backlog-seed workflow references this form for entry shape + minimum
  fields (use case, deliverables, overlaps, source pointers) — see the pointer in
  `_meta/plans/extender-ideas-backlog-seed/`.
- **Item authoring** (the `task-authoring` skill): the backlog-entry form IS the item-body
  conformance bar; that skill is authoritative for the mechanics.
- **Bench intake** (`<incubator-repo>/docs/extender-lifecycle.md`, Stage 1): intake
  references this form for the scope-doc requirement.

---

## Part 2 — The shared milestone set

A project's board should speak a **consistent gate/milestone vocabulary** so cross-project status
reads the same and dependencies line up. Two layers, from existing practice:

**Scope:** everything below is a worked example of one board's adoption, on a tracker that has
milestones as a first-class object. The doctrine is the ordered-promise discipline, not the
milestone object — a tracker without milestones expresses the same `P<n> — <promise>` vocabulary
as labels or a priority band.

### Layer 1 — milestones name promise levels (the "P-N" set)

A project adopts an ordered set of milestones, each a **promise level** — what becomes true when that
milestone closes — not a date. The `dotfiles-agents` set is the reference model:

| Milestone | Promise (what is true when it closes) |
| --- | --- |
| P1 — Lifecycle live | the curation loop runs for real (batch triage across the roster; first real promotion + retirement records) |
| P2 — Pilot proven | the flagship capability is proven on a real repo end-to-end |
| P3 — Rollout and retire | the standard is enacted across priority repos; superseded pieces retired |
| P4 — Cross-tool parity | the agnostic base format lands; cross-vendor parity is real |

The pattern a project reuses (not the exact titles): **ordered `P<n> — <promise>` milestones, each
describing a state the project reaches, sequenced so each depends on the prior.** A project renames the
promises to its own arc; it keeps the "ordered promise, not a date" discipline.

### Layer 2 — gate labels answer "what blocks the next promise?"

Alongside milestones, a `gate:<promise>` label marks the items that **block reaching the next promise
level**. An empty gate means that promise is safe to make — you check the gate, not the raw item
count. (From the project protocol: gate labels answer "what blocks the next promise level" and live
separately from the backlog.) Example in use: `dotfiles-agents` tracks P4 with the `gate:cross-tool`
label (per the P4 milestone description).

**Milestones vs gate labels:** the milestone is the *destination* (a promise level); the gate label is
the *blocker set* for the next hop. A milestone with an empty gate is ready to close.

### How a project adopts the set

1. Create the ordered `P<n> — <promise>` milestones (rename promises to the project's arc; keep them
   ordered and dependency-sequenced).
2. Add a `gate:<promise>` label per promise level whose readiness you want to track separately from the
   backlog; tag the blocking items.
3. On a **shared board** (one item set, many repos), milestones **mirror across the repos** so an item
   from either repo lands under the same promise level — the board is the single source of promise
   state.

### Mapping — the Agent Extenders board (acme/projects/9)

The joint `dotfiles-agents` + `<incubator-repo>` board ("Agent Extenders", one item set, many
views) adopts the set as follows:

| Element | Value on the board |
| --- | --- |
| Milestone set | the P1–P4 promise set above, **mirrored across both repos** (per the board's own description) so a workbench item and a dotfiles-agents item share one promise level |
| Gate label | `gate:cross-tool` marks what blocks P4 (agnostic base format + cross-vendor parity) |
| Item source | one item set spanning both repos, sliced into the board's views |
| Fields | per the field-map table in board-triage's `references/adapters/github-projects.md` (Workstream / Impact / Effort / Priority) |

New promise-level milestones the board needs are created **once and mirrored to both repos** so the two
never drift.
