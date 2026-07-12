> **Tracking:** #84, surfaced 2026-07-05 while routing the vault PM registries out. The `use-case-driven-backlog` decision is ratified, but two standards it implies (the backlog-entry form and the shared milestone set) have no home and would vanish when the vault registries freeze. This issue gives them a home as planning-desk reference content.

Surfaced while routing the vault PM registries out (2026-07-05): the `use-case-driven-backlog` decision is ratified, but **two standards it implies have no home today** — they would vanish when the vault registries freeze.

## Deliverable A — use-case backlog-entry form (was vault Q-14)
Define the FORM a "well-defined use case" takes to enter the backlog: user-story vs feature-spec link vs project-task shape, and the minimum fields. `#49` seeds entries but does not define the form.

**Scope amendment (owner-ruled 2026-07-11):** Deliverable A additionally defines the **workbench spec-entry form** — a candidate enters `dotfiles-agents-workbench/incubator/` only with a scope doc stating: driving use case (the J1 hypothesis), deliverables, acceptance criteria mapped to the H/J gate, and known overlaps (J4). The backlog-entry form and the bench-entry form share the same core fields; this standard defines both once.

## Deliverable B — shared milestone-set standard (was vault T-23b)
Define a "core milestone set shared across projects" so boards use a consistent gate/milestone vocabulary. Currently ad-hoc per repo; not specced anywhere.

## Acceptance criteria
- A written standard states the use-case entry form (fields + which representation) and is referenced by the backlog-seed workflow (#49).
- A written standard defines the shared milestone set and how a project adopts it; at least the Agent Extenders board is mapped to it.
- `docs/extender-lifecycle.md` (in dotfiles-agents-workbench) references the entry form at intake; first application: [wb#37](https://github.com/hsb3/dotfiles-agents-workbench/issues/37) (python-standards).
- Both land as planning-desk / project-workflow reference content (not a flat note), so future backlog + board setup cite them.

## Dependencies & gates
- **Blocks on:** the `use-case-driven-backlog` decision (ratified; migrating to the Strategy Desk). Pairs with #49 (backlog seed) and the board setup in #9.
- **Gates:** `make ci` (targets rebuild + tests) since it lands as planning-desk skill content. `project-workflow` version bump because the skill changes.
