# HANDOFF — dotfiles-agents

*Cold-start bridge. Secret-free (secrets live in `_meta/operations/`, never tracked).*

## 0 · Orientation
Fresh repo (created 2026-06-26): source of truth for proven coding-agent extenders. Built from scratch — NOT a rename of `hsb3-custom-plugins`, which stays live as the migration source. Siblings: `dotfiles` (tooling), `dotfiles-agents-workbench` (unproven; planned), `dotfiles-bootstrap` (planned). Decision record + build plan: `~/Documents/Claude/Projects/dotfiles-agents-cowork/planning/{CANON.md, repository-technical-plan.md}`.

## 1 · Current standing
**Phases 0–2 COMPLETE (issues #1–5 closed); CI green. Phase 3 (translation service) next.** Phase 0: repo + governance + board #9. Phase 1 (#11): layout + translation control files + naming taxonomy. Phase 2: migrated the homegrown LIVE set → `primitives-core/` as single-source copies — **76 roster entries (53 skills + 18 agents + 5 hooks)**; `externals.yaml` tracks third-party (cloned at build); client-coupling genericized; hooks built shape-C; 16 commands dropped. **Drift guard live:** `scripts/check_roster.py` / `make check` / CI on every PR. **Promotion gate RATIFIED** (J1 = ≥2 real uses).

## 2 · Last delivered
- Roster↔disk drift guard + Makefile + CI — #16 (`ea9f099`, closes #5). First green gate.
- Phase 2b hooks + command dispositions — #15 (`03552af`).
- Phase 2c polish — #14 · cleanup — #13 · migration — #12. (manifest + bootstrap review + command dispositions in `planning/`.)

## 3 · Where to start building
**Phase 3 — translation service (the cross-tool win; issues #6, #7):**
- Build `scripts/` translate: roster + `primitives-core-translation-config.yaml` → static `targets/{claude-code,opencode,claude-agents}/` + `primitives-core-translation-results.json` lock; `--check` CI drift mode (extend the existing ci.yml). Reference shape: `ant-update-openapi.py`.
- **MVP first** (technical-plan §2.1): skills (native copy) + agents (transform frontmatter) + CC marketplace assembly (`.claude-plugin/marketplace.json` + plugin dirs from roster membership). Defer mcp render + the CMA adapter; hooks ship CC-only.
- Then #7: verify a skill AND an agent load in opencode from generated `targets/opencode/` with zero hand-config.
- **Needs plugin-level metadata** (description/version per plugin) for marketplace assembly — not yet captured; pull from the frozen source's `plugins/<p>/.claude-plugin/plugin.json`.
**Then:** Phase 4 workbench (#8, encode the ratified gate as `make promote-check`), Phase 5 bootstrap (#9).
**Backlog (`planning/backlog.md`):** python-standards skill authoring, raptorxai-decks split, langchain-vs-official curation, frontend curation, externals upstream URLs, near-term enhancements.
**Gate live (CANON 12):** promoting a PARKED item (`opencode-expert` strongest) needs ≥2 cited real uses + H1–H5.
- Sources: LIVE `~/Developer/FUNCTIONFORM/hsb3-custom-plugins` (frozen) + STAGING `_meta/desktop-cleanup/` (gitignored).

## 4 · Conventions & gotchas
- `bgIsolation:none` in `.claude/settings.json` — this repo isn't parallel-mutated; background agents share the main tree.
- Generated `targets/` + results lock are drift-guarded; never hand-edit.
- Remote is SSH.

## 5 · Incident log
(none)
