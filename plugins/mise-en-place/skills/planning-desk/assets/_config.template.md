# Planning desk — project config

_The project-specific bindings the planning-desk authoring modes read. Written once at setup by
detecting this repo's tracker and gates; update it when either changes. Where a value couldn't be
determined at setup, it's left as `TODO(owner):` — fill it in rather than guessing._

Repo: `<owner>/<name>`  ·  Set up: `<YYYY-MM-DD>`

## Tracker binding

Which tracker the desk scripts read, and how they reach it. The scripts never talk to a tracker
directly: they read a snapshot exported by an adapter under `_utils/adapters/`, so a project swaps
backends by swapping this block.

| Setting | Value |
| ------- | ----- |
| Adapter | `TODO(owner): the adapter file under _utils/adapters/, e.g. the default one` |
| Project | `TODO(owner): the project name, or "resolved from the workspace binding"` |
| Snapshot | `TODO(owner): path of the checked-in export, if the desk keeps one; otherwise live` |

> "Resolved from the workspace binding" means no project is passed at all and the tracker resolves
> it from this working tree's own config — the usual case for a desk living in its project's repo.

The task-authoring bar the conformance gate keys on (load-bearing sections, not exact wording):

- **normal item**: an **Acceptance criteria** section + a **Dependencies & gates** section.
- **epic** (an item with children, or one labelled `epic`): a **Close when** section.

## Gate menu

The gates a change must account for in an item's **Dependencies & gates** and a plan's **Gate &
contract hygiene** — the commands it must pass and the source-of-truth artifacts it must keep in
sync. A plan picks the subset its change surface actually touches; it's explicit about which do NOT
fire. (Detected from the Makefile / package.json / pyproject / CI workflows — verify and prune.)

| Gate | Command / trigger | Fires when the change touches… |
| ---- | ----------------- | ------------------------------ |
| Pre-commit / test | `TODO(owner): e.g. make check / npm test` | always |
| Lint / format | `TODO(owner):` | always |
| Type / API codegen + same-PR contract amend | `TODO(owner): e.g. pnpm generate:types + amend api-contract.md` | a typed API / schema surface |
| DB migration (+ its run cost) | `TODO(owner):` | a schema change |
| Generated/spec artifact drift guard | `TODO(owner):` | a codegen'd artifact |
| Infra | `TODO(owner): e.g. terraform plan` | infra paths |

## Canonical docs to cite

The spine docs a plan should ground itself in (a claim cites `path:line` OR one of these):

- `TODO(owner): e.g. docs/charter.md (precedence), docs/api-contract.md, docs/schema.md, docs/architecture.md, ADRs under docs/decisions/`

## Conventions / gotchas

- ASCII-only inside markdown table cells (avoids the common prettier/markdown format-check trap).
- Outward-facing tracker edits get owner approval before writing; staging on the desk is free, and
  the adapter's `apply` is dry-run until `--apply` is passed.
- Run the `_utils/` scripts from the main working tree (they read the tracker + disk).
- `TODO(owner):` add any repo-specific gotchas (branch/commit conventions, required CI checks, etc.).
