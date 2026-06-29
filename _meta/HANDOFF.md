# HANDOFF — dotfiles-agents

*Cold-start bridge. Secret-free (secrets live in `_meta/operations/`, never tracked).*

## 0 · Orientation
Fresh repo (created 2026-06-26): source of truth for proven coding-agent extenders. Built from scratch — NOT a rename of `hsb3-custom-plugins`, which stays live as the (frozen) migration source. Siblings (all created 2026-06-29): `dotfiles` (tooling), `dotfiles-agents-workbench` (unproven bench), `dotfiles-bootstrap` (orchestrator). Governance docs: `~/Documents/Claude/Projects/dotfiles-agents-cowork/planning/{CANON.md (decisions 1–15), repository-technical-plan.md, promotion-qualification-gate.md, backlog.md, phase-2-migration-manifest.md, phase-2-bootstrap-review.md, phase-2-command-dispositions.md}`. **Planning desk live** at `_meta/plans/` (run `planning-desk` skill for issue/plan/govern work; `_config.md` has the gate menu).

## 1 · Current standing
**ALL 5 PHASES COMPLETE — the full roadmap is delivered (issues #1–5, #7–9 closed); CI green. Only #6 (deferred mcp/CMA adapters) + the backlog remain.** Four repos live: dotfiles-agents (proven source), dotfiles-agents-workbench (unproven bench), dotfiles-bootstrap (orchestrator), + dotfiles (tooling). Phases 0–2: governance + migrated the homegrown LIVE set → `primitives-core/` (**76 roster entries: 53 skills + 18 agents + 5 hooks**), `externals.yaml` tracker, client-coupling genericized, commands dropped. **Phase 3 (#17): translation service** — `scripts/translate.py` renders `primitives-core/` → static `targets/{claude-code,opencode,claude-agents}/` + content-hash lock; deterministic, config-driven, `--check` drift mode. **Two CI drift guards** (`make ci`: roster↔disk + targets) green on every PR. **Promotion gate RATIFIED** (J1 = ≥2 real uses).

## 2 · Last delivered
- **Planning desk** stood up in dotfiles-agents + dotfiles-bootstrap (`_meta/plans/` tracked via gitignore negation; 7-script `_utils/` toolkit; seeded `.github/ISSUE_TEMPLATE/`; per-repo `_config.md` gate menus).
- **#6 brought into conformance** — staged a conformant issue body + deep `plan.md` at `_meta/plans/translation-deferred-adapters/`, published to live #6 (conformance gate 1/1). The plan scopes the residual: CMA adapter (A, unblocked) + mcp render (B, blocked on a first mcp primitive).
- Phase 3 MVP translation service — #17 (`4e8a05b`, closes #7): targets/ (475 files) + results lock + plugins.yaml + Makefile. Agent transform proven live in opencode 1.16.2.
- #16 roster guard + CI · #15 hooks+commands · #14/#13/#12 Phase 2.

## 3 · Where to start building
**Phase 3 is the plan's "consolidation + cross-tool" completion point; 4–5 are reproducibility polish.** Open work:
- **#6 — deferred translation adapters: BUILD-READY.** Conformant issue + full plan at `_meta/plans/translation-deferred-adapters/plan.md`. **A (CMA adapter)** is unblocked — replace the deferred-skip block at `scripts/translate.py:290-301`, emit static CMA payloads/build-sheets to `targets/claude-agents/` per the pinned CANON contract; 4 open decisions in the plan (recommend: static payloads, configurable default model, defer B, empty tool/skill arrays). **B (mcp render)** blocked on a first `type: mcp` primitive existing (`primitives-core/mcp/` empty).
- ~~**#8 — Phase 4 workbench**~~ **DONE 2026-06-29:** `dotfiles-agents-workbench` (private) created — https://github.com/hsb3/dotfiles-agents-workbench. 14 candidates seeded; ratified gate encoded as `scripts/promote_check.py` / `make promote-check` (8/14 pass hard checks; REGISTRY.md tracks status). Sibling repo — promotes one-way INTO here.
- ~~**#9 — Phase 5 bootstrap**~~ **DONE 2026-06-29:** `dotfiles-bootstrap` (private) — https://github.com/hsb3/dotfiles-bootstrap. `bootstrap.sh` (ensure source → `make build` → deploy → verify) + `scripts/deploy.py` (idempotent symlink deploy, dry-run default, `--prefix` sandbox, clobber-safe). Sandbox-tested (104 links). Post-MVP: wire dotfiles `install.sh`, auto marketplace add, Linux.
**Backlog (`planning/backlog.md`):** python-standards skill authoring; raptorxai-decks split; langchain-vs-official + frontend curation; externals upstream URLs; near-term enhancements (api-server-design, comms styling, CMS trio).
**Gate live (CANON 12):** promoting a PARKED item (`opencode-expert` strongest) needs ≥2 cited real uses + H1–H5.
**Deploy targets (verified, opencode 1.16.2):** opencode agents → `.opencode/agent(s)/` or `~/.config/opencode/agent(s)/`; opencode skills auto-scanned from `~/.claude/skills/` + `~/.agents/skills/` (config loaded once — restart opencode to pick up new skills). CC marketplace: `claude plugin marketplace add <repo>` reads `targets/claude-code/.claude-plugin/marketplace.json`.
- Sources: LIVE `~/Developer/FUNCTIONFORM/hsb3-custom-plugins` (frozen) + STAGING `_meta/desktop-cleanup/` (gitignored).

## 4 · Conventions & gotchas
- `bgIsolation:none` in `.claude/settings.json` — this repo isn't parallel-mutated; background agents share the main tree.
- Generated `targets/` + results lock are drift-guarded; never hand-edit. Edit `primitives-core/` then `make build`.
- Remote is SSH. Trunk-based: branch `<type>/<name>`, squash-merge PRs, commits end with the `Claude-Session:` footer.
- **Planning desk:** run `_meta/plans/_utils/` scripts from the **main tree** (they read live `gh` + disk). README ACTIVE rows use the **bare slug** (not a markdown link) — `reconcile.py` keys `cells[0]` against the on-disk folder name.
- **gh token gotcha:** the env `GITHUB_TOKEN` can't resolve project-board owner; use `env -u GITHUB_TOKEN gh ...` for `gh project`/`gh repo create` if it fails.

## 5 · Incident log
(none)
