# Planning desk — project config

_The project-specific bindings the planning-desk authoring modes read. Written once at setup by
detecting this repo's gates and templates; update it when the project's gates change. Where a value
couldn't be determined at setup, it's left as `TODO(owner):` — fill it in rather than guessing._

Repo: `<owner>/<name>`  ·  Set up: `<YYYY-MM-DD>`

## Issue templates

The conformance gate keys on the load-bearing sections, not exact wording:

- **feature / bug** (non-epic): an **Acceptance criteria** section + a **Dependencies & gates** section.
- **epic / tracker**: a **Close when** section.

| Template | Path | Required sections present |
| -------- | ---- | ------------------------- |
| feature | `.github/ISSUE_TEMPLATE/feature.md` | Acceptance criteria; Dependencies & gates |
| bug | `.github/ISSUE_TEMPLATE/bug.md` | Acceptance criteria; Dependencies & gates |
| epic | `.github/ISSUE_TEMPLATE/epic.md` | Close when |

> If this repo had no templates at setup, generic ones were seeded from the skill. Replace them with
> the project's real templates if/when they exist, keeping the required sections above.

## Gate menu

The gates a change must account for in an issue's **Dependencies & gates** and a plan's **Gate &
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
- Outward-facing GitHub edits get owner approval before publishing; staging on the desk is free.
- Run the `_utils/` scripts from the main working tree (they read live `gh` state + disk).
- `TODO(owner):` add any repo-specific gotchas (branch/commit conventions, required CI checks, etc.).
