# HANDOFF — dotfiles-agents

*Cold-start bridge. Secret-free (secrets live in `_meta/operations/`, never tracked).*

## 0 · Orientation
Fresh repo (created 2026-06-26): source of truth for proven coding-agent extenders. Built from scratch — NOT a rename of `hsb3-custom-plugins`, which stays live as the migration source. Siblings: `dotfiles` (tooling), `dotfiles-agents-workbench` (unproven; planned), `dotfiles-bootstrap` (planned). Decision record + build plan: `~/Documents/Claude/Projects/dotfiles-agents-cowork/planning/{CANON.md, repository-technical-plan.md}`.

## 1 · Current standing
**Phases 0–1 done; Phase 2a in review.** Phase 0: repo + charter/CLAUDE/AGENTS/README, labels, milestones, board #9, seed issues. Phase 1 (PR #11 merged, closed #1): scaffolded layout + translation control files + naming taxonomy. **Phase 2a (PR #12, open):** migrated the homegrown LIVE set — 54 skills + 18 agents into `primitives-core/`, generated the 72-entry roster, added `externals.yaml` tracker. **Next: review/merge #12, then Phase 2b** (hooks + commands).

## 2 · Last delivered
- Phase 2a migration — **PR #12 (open)**: 54 skills + 18 agents + roster + `externals.yaml`. Advances #2, #3. Migration manifest at `planning/phase-2-migration-manifest.md` (foreman-verified).
- Phase 1 scaffold — PR #11 (`981d1c4`). Layout + translation control files.
- Phase 0 governance scaffold — `7a7cec3`. Board + milestones.

## 3 · Where to start building
**Phase 2b (next, after #12 merges):**
- **Hooks** — 5 handlers (dev-focus×2 stdlib; python-standards×3 need jq/ruff) PLUS inline prompt-type hooks in the plugins' `hooks.json`. Needs a canonical hook-shape decision before representing them in `primitives-core/hooks/` + the translation-config hook adapter.
- **Commands (#4)** — fold/retire the 16 per manifest §6.
- **#5** — hook naming + roster↔disk lint drift-guard.
- Plugin-level metadata (description/version) for marketplace assembly (Phase 3).
**Blocked deliverable — promotion qualification gate (CANON 12):** must be ratified before promoting the 4 PARKED staging items (`opencode-expert`, `langgraph-designer`, `raptorxai-decks`, `webapp-designer`). Henry asked to establish minimum qualifications first.
- Sources: **LIVE** `~/Developer/FUNCTIONFORM/hsb3-custom-plugins` (untouched migration source) + **STAGING** `_meta/desktop-cleanup/` (gitignored).
- `externals.yaml` upstream URLs are stubbed `null` — research TODO (CANON open item).

## 4 · Conventions & gotchas
- `bgIsolation:none` in `.claude/settings.json` — this repo isn't parallel-mutated; background agents share the main tree.
- Generated `targets/` + results lock are drift-guarded; never hand-edit.
- Remote is SSH.

## 5 · Incident log
(none)
