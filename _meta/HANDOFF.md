# HANDOFF — dotfiles-agents

*Cold-start bridge. Secret-free (secrets live in `_meta/operations/`, never tracked).*

## 0 · Orientation
Fresh repo (created 2026-06-26): source of truth for proven coding-agent extenders. Built from scratch — NOT a rename of `hsb3-custom-plugins`, which stays live as the migration source. Siblings: `dotfiles` (tooling), `dotfiles-agents-workbench` (unproven; planned), `dotfiles-bootstrap` (planned). Decision record + build plan: `~/Documents/Claude/Projects/dotfiles-agents-cowork/planning/{CANON.md, repository-technical-plan.md}`.

## 1 · Current standing
**Phases 0–1 done; Phase 2 ~80% (2a migration + cleanup + polish all merged); 2b remaining.** Phase 0: repo + governance + board #9. Phase 1 (#11): layout + translation control files + naming taxonomy. Phase 2a (#12): migrated homegrown LIVE set → `primitives-core/` + roster + `externals.yaml`. Cleanup (#13): genericized client coupling, nano-banana-2→externals. Polish (#14): renamed `agent-dot-md-authoring`, finished machine-path sweep. **Roster now 71 entries / 53 skills + 18 agents.** **Promotion gate RATIFIED 2026-06-29** (J1 = ≥2 real uses). **Next: Phase 2b** (hooks + commands).

## 2 · Last delivered
- Phase 2c polish — #14 (`5568a16`): rename + machine-path sweep.
- Phase 2 cleanup — #13 (`9bf5de5`): genericize client coupling; nano-banana-2 → externals.
- Phase 2a migration — #12 (`39e208a`): 54 skills + 18 agents + roster + externals. Migration manifest + bootstrap review in `planning/`.
- Phase 1 (#11) / Phase 0 (`7a7cec3`).

## 3 · Where to start building
**Phase 2b (next):**
- **Hooks** — 5 handlers (dev-focus×2 stdlib; python-standards×3 need jq/ruff) PLUS inline prompt-type hooks in the plugins' `hooks.json`. **Open design fork:** canonical hook shape (per-plugin folder preserving `hooks.json` verbatim, vs per-(plugin×event) primitive renamed `<plugin>.<Event>.<slug>.sh`) before representing in `primitives-core/hooks/` + the translation-config hook adapter.
- **Commands (#4)** — fold/retire the 16 per migration-manifest §6.
- **#5** — hook naming + roster↔disk lint drift-guard.
- Plugin-level metadata (description/version) for marketplace assembly (Phase 3).
**Gate is live (CANON 12):** promoting a PARKED item (`opencode-expert` strongest, `langgraph-designer`, `raptorxai-decks`, `webapp-designer`) now needs ≥2 cited real uses from Henry + the H1–H5 checks.
- Direction backlog: `planning/backlog.md` (curation threads, near-term needs, future extenders).
- Sources: LIVE `~/Developer/FUNCTIONFORM/hsb3-custom-plugins` (frozen) + STAGING `_meta/desktop-cleanup/` (gitignored).
- `externals.yaml` upstream URLs mostly stubbed `null` — research TODO.

## 4 · Conventions & gotchas
- `bgIsolation:none` in `.claude/settings.json` — this repo isn't parallel-mutated; background agents share the main tree.
- Generated `targets/` + results lock are drift-guarded; never hand-edit.
- Remote is SSH.

## 5 · Incident log
(none)
