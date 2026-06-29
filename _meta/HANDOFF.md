# HANDOFF — dotfiles-agents

*Cold-start bridge. Secret-free (secrets live in `_meta/operations/`, never tracked).*

## 0 · Orientation
Fresh repo (created 2026-06-26): source of truth for proven coding-agent extenders. Built from scratch — NOT a rename of `hsb3-custom-plugins`, which stays live as the migration source. Siblings: `dotfiles` (tooling), `dotfiles-agents-workbench` (unproven; planned), `dotfiles-bootstrap` (planned). Decision record + build plan: `~/Documents/Claude/Projects/dotfiles-agents-cowork/planning/{CANON.md, repository-technical-plan.md}`.

## 1 · Current standing
**Phases 0–4 COMPLETE (issues #1–5, #7, #8 closed); CI green. Core + workbench done; only Phase 5 (bootstrap) + deferred adapters (#6) remain.** Phases 0–2: governance + migrated the homegrown LIVE set → `primitives-core/` (**76 roster entries: 53 skills + 18 agents + 5 hooks**), `externals.yaml` tracker, client-coupling genericized, commands dropped. **Phase 3 (#17): translation service** — `scripts/translate.py` renders `primitives-core/` → static `targets/{claude-code,opencode,claude-agents}/` + content-hash lock; deterministic, config-driven, `--check` drift mode. **Two CI drift guards** (`make ci`: roster↔disk + targets) green on every PR. **Promotion gate RATIFIED** (J1 = ≥2 real uses).

## 2 · Last delivered
- Phase 3 MVP translation service — #17 (`4e8a05b`, closes #7): targets/ (475 files) + results lock + plugins.yaml + Makefile (`build`/`build-check`/`ci`). Agent transform proven live in opencode 1.16.2.
- #16 roster guard + CI · #15 hooks+commands · #14/#13/#12 Phase 2.

## 3 · Where to start building
**Phase 3 is the plan's "consolidation + cross-tool" completion point; 4–5 are reproducibility polish.** Open work:
- **#6 — deferred translation adapters:** mcp-render (no mcp primitives yet) + the claude-agents (CMA) adapter (`POST /v1/skills` + `/v1/agents`, ref CANON "Resolved — CMA contract"). Currently recorded as deferred skips.
- ~~**#8 — Phase 4 workbench**~~ **DONE 2026-06-29:** `dotfiles-agents-workbench` (private) created — https://github.com/hsb3/dotfiles-agents-workbench. 14 candidates seeded; ratified gate encoded as `scripts/promote_check.py` / `make promote-check` (8/14 pass hard checks; REGISTRY.md tracks status). Sibling repo — promotes one-way INTO here.
- **#9 — Phase 5 bootstrap:** `dotfiles-bootstrap` MVP — clone → install → `extenders deploy` (place built targets/) → verify.
**Backlog (`planning/backlog.md`):** python-standards skill authoring; raptorxai-decks split; langchain-vs-official + frontend curation; externals upstream URLs; near-term enhancements (api-server-design, comms styling, CMS trio).
**Gate live (CANON 12):** promoting a PARKED item (`opencode-expert` strongest) needs ≥2 cited real uses + H1–H5.
**Deploy targets (verified, opencode 1.16.2):** opencode agents → `.opencode/agent(s)/` or `~/.config/opencode/agent(s)/`; opencode skills auto-scanned from `~/.claude/skills/` + `~/.agents/skills/` (config loaded once — restart opencode to pick up new skills). CC marketplace: `claude plugin marketplace add <repo>` reads `targets/claude-code/.claude-plugin/marketplace.json`.
- Sources: LIVE `~/Developer/FUNCTIONFORM/hsb3-custom-plugins` (frozen) + STAGING `_meta/desktop-cleanup/` (gitignored).

## 4 · Conventions & gotchas
- `bgIsolation:none` in `.claude/settings.json` — this repo isn't parallel-mutated; background agents share the main tree.
- Generated `targets/` + results lock are drift-guarded; never hand-edit.
- Remote is SSH.

## 5 · Incident log
(none)
