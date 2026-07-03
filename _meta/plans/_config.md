# Planning desk — project config

_The project-specific bindings the planning-desk authoring modes read. Detected at setup from the
Makefile, CI workflow, and repo docs. Update when the gates change._

Repo: `hsb3/dotfiles-agents`  ·  Set up: `2026-06-29`

## Issue templates

The conformance gate keys on the load-bearing sections, not exact wording:

- **feature / bug** (non-epic): an **Acceptance criteria** section + a **Dependencies & gates** section.
- **epic / tracker**: a **Close when** section.

| Template | Path | Required sections present |
| -------- | ---- | ------------------------- |
| feature | `.github/ISSUE_TEMPLATE/feature.md` | Acceptance criteria; Dependencies & gates |
| bug | `.github/ISSUE_TEMPLATE/bug.md` | Acceptance criteria; Dependencies & gates |
| epic | `.github/ISSUE_TEMPLATE/epic.md` | Close when |

> Generic templates seeded from the skill at setup (the repo had none). Replace with project-specific
> templates if/when they exist, keeping the required sections above.

## Gate menu

The gates a change must account for in an issue's **Dependencies & gates** and a plan's **Gate &
contract hygiene**. A plan picks the subset its change surface touches and is explicit about which do
NOT fire.

| Gate | Command / trigger | Fires when the change touches… |
| ---- | ----------------- | ------------------------------ |
| CI aggregate (required) | `make ci` (roster + content + naming + targets + tests) on every PR + push to main | always |
| Roster drift guard | `make check` (`scripts/check_roster.py`) | a primitive added / removed / renamed in `primitives-core/` |
| Targets drift guard | `make build-check`; fix with `make build` | any edit to `primitives-core/`, `primitives-core.yaml`, `plugins.yaml`, or the translation config |
| Naming taxonomy | `make names` (`scripts/check_naming.py`, in `make ci`); prefix families stay a manual check against `manifests/naming.md` | naming a new primitive or plugin |
| YAML / workflow lint | `yamllint`; `actionlint` (manual; wired into neither `make ci` nor a pre-commit hook) | editing `*.yaml`/`*.yml`; `.github/workflows/` |
| Canonical-doc amendment | manual review (no auto-check): amend the doc in the SAME PR as the surface change | a change alters behavior a spine doc describes: `CLAUDE.md`, `AGENTS.md`, `docs/CHARTER.md`, `docs/plugins/*`, `docs/sops/*` — a plan states whether this fires |

> `targets/` is GENERATED. Never hand-edit it; edit the source in `primitives-core/` and run
> `make build`. The drift guard fails any PR whose `targets/` or results lock is out of sync.

## Canonical docs to cite

A load-bearing claim cites `path:line` OR one of these:

- `docs/CHARTER.md` (precedence page) · `CLAUDE.md` (agent digest) · `AGENTS.md`
- `manifests/naming.md` (naming taxonomy) · `primitives-core.yaml` (the roster) · `externals.yaml`
- Governance (outside the repo): `~/Documents/Claude/Projects/dotfiles-agents-cowork/_structure/{CANON.md, repository-technical-plan.md}`; promotion gate at `dotfiles-agents-workbench/docs/promotion-gate.md`

## Conventions / gotchas

- ASCII-only inside markdown table cells (avoids the prettier/markdown format-check trap).
- Outward-facing GitHub edits get owner approval before publishing; staging on the desk is free.
- Run the `_utils/` scripts from the main working tree (they read live `gh` state + disk).
- **Commands are dropped** (CANON 3) — encode reusable procedures as skills, not commands.
- **Hooks are stdlib-only** and named `<plugin>.<Event>.<slug>.sh` (`manifests/naming.md`).
- **Externals are tracked, not vendored** — third-party extenders go in `externals.yaml`.
- Trunk-based: branch `<type>/<short-name>`, squash-merge PRs, commit prefixes `feat|fix|docs|refactor|chore(scope):`, commits end with the `Claude-Session:` footer.
