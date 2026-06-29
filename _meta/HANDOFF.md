# HANDOFF — dotfiles-agents

*Cold-start bridge. Secret-free (secrets live in `_meta/operations/`, never tracked).*

## 0 · Orientation
Fresh repo (created 2026-06-26): source of truth for proven coding-agent extenders. Built from scratch — NOT a rename of `hsb3-custom-plugins`, which stays live as the migration source. Siblings: `dotfiles` (tooling), `dotfiles-agents-workbench` (unproven; planned), `dotfiles-bootstrap` (planned). Decision record + build plan: `~/Documents/Claude/Projects/dotfiles-agents-cowork/planning/{CANON.md, repository-technical-plan.md}`.

## 1 · Current standing
**Phases 0–1 done.** Phase 0: repo + charter/CLAUDE/AGENTS/README, labels, milestones, board #9, seed issues. Phase 1 (PR #11, merged, closed issue #1): scaffolded `primitives-core/{skills,agents,mcp,hooks}`, `primitives-core.yaml` roster (documented schema, empty), `primitives-core-translation-config.yaml` (capability matrix encoded), results-lock stub, `manifests/naming.md`, `targets/` + `scripts/` skeletons. **Next: Phase 2** — migrate primitives into `primitives-core/` + populate the roster.

## 2 · Last delivered
- Phase 1 scaffold — PR #11 (squash-merged → `981d1c4`). Layout + translation control files per technical-plan §4/§2.1.
- Phase 0 governance scaffold — `7a7cec3`. Board + milestones.

## 3 · Where to start building
**Phase 2 (in progress):** reconcile the two migration sources → migration manifest → copy canonical primitive copies into `primitives-core/`, populate roster, apply naming taxonomy, drop the 18 commands.
- Sources: **LIVE** `~/Developer/FUNCTIONFORM/hsb3-custom-plugins` (20 skills, 14 agents, 11 plugins, hooks-inside-plugins; has INVENTORY.md/INDEX.md) + **STAGING** `_meta/desktop-cleanup/` (7 internal + 6 external skills, langgraph-designer agent, webapp-designer plugin, 24 third-party trimmed plugins, reference resources).
- Audit agent dispatched 2026-06-28 to produce the manifest; manifest will land in the planning folder (`phase-2-migration-manifest.md`). Verify its canonical-copy calls against source before mass-copying (subagent claims are hypotheses).
- `_meta/desktop-cleanup/` is gitignored (staging, not tracked).

## 4 · Conventions & gotchas
- `bgIsolation:none` in `.claude/settings.json` — this repo isn't parallel-mutated; background agents share the main tree.
- Generated `targets/` + results lock are drift-guarded; never hand-edit.
- Remote is SSH.

## 5 · Incident log
(none)
