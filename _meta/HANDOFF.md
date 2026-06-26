# HANDOFF — dotfiles-agents

*Cold-start bridge. Secret-free (secrets live in `_meta/operations/`, never tracked).*

## 0 · Orientation
Fresh repo (created 2026-06-26): source of truth for proven coding-agent extenders. Built from scratch — NOT a rename of `hsb3-custom-plugins`, which stays live as the migration source. Siblings: `dotfiles` (tooling), `dotfiles-agents-workbench` (unproven; planned), `dotfiles-bootstrap` (planned). Decision record + build plan: `~/Documents/Claude/Projects/dotfiles-agents-cowork/planning/{CANON.md, repository-technical-plan.md}`.

## 1 · Current standing
**Phase 0 (governance scaffold) done:** repo + charter/CLAUDE/AGENTS/README, labels, milestones, board, seed issues. **Next: Phase 1** — scaffold the `primitives-core/` layout.

## 2 · Last delivered
- Phase 0 governance scaffold (this initial commit). See the project board + milestones.

## 3 · Where to start building
Phase 1 issue: scaffold `primitives-core/{skills,agents,mcp,hooks}`, `primitives-core.yaml` roster, translation config/results, `targets/`. Then Phase 2 — migrate primitives from `hsb3-custom-plugins`.

## 4 · Conventions & gotchas
- `bgIsolation:none` in `.claude/settings.json` — this repo isn't parallel-mutated; background agents share the main tree.
- Generated `targets/` + results lock are drift-guarded; never hand-edit.
- Remote is SSH.

## 5 · Incident log
(none)
