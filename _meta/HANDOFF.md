# HANDOFF — dotfiles-agents

*Cold-start bridge. Secret-free (secrets live in `_meta/operations/`, never tracked).*

## 0 · Orientation
Fresh repo (created 2026-06-26): source of truth for proven coding-agent extenders. Built from scratch — NOT a rename of `hsb3-custom-plugins`, which stays live as the (frozen) migration source. Siblings (all created 2026-06-29): `dotfiles` (tooling), `dotfiles-agents-workbench` (unproven bench), `dotfiles-bootstrap` (orchestrator). Governance docs: `~/Documents/Claude/Projects/dotfiles-agents-cowork/planning/{CANON.md (decisions 1–15), repository-technical-plan.md, promotion-qualification-gate.md, backlog.md, phase-2-migration-manifest.md, phase-2-bootstrap-review.md, phase-2-command-dispositions.md}`. **Planning desk live** at `_meta/plans/` (run `planning-desk` skill for issue/plan/govern work; `_config.md` has the gate menu).

## 1 · Current standing
**ALL 5 PHASES COMPLETE + the full translation service (incl. mcp) is delivered — every build issue closed (#1–9, #17–21); CI green on main. Only the backlog remains.** Four repos live: dotfiles-agents (proven source), dotfiles-agents-workbench (unproven bench), dotfiles-bootstrap (orchestrator), + dotfiles (tooling). Phases 0–2: governance + migrated the homegrown LIVE set → `primitives-core/` (**80 roster entries: 53 skills + 18 agents + 5 hooks + 4 mcp**), `externals.yaml` tracker, client-coupling genericized, commands dropped. **Phase 3 (#17): translation service** — `scripts/translate.py` renders `primitives-core/` + `externals.yaml` → static `targets/{claude-code,opencode,claude-agents}/` + content-hash lock; deterministic, config-driven, `--check` drift mode. All four capability cells live (skills · agents · CMA payloads · mcp). **Build counts: CC 84 built · opencode 79 · claude-agents 72.** **Two CI drift guards** (`make ci`: roster↔disk + targets) green on every PR. **Promotion gate RATIFIED** (J1 = ≥2 real uses). README is now a real value-prop + proof page (`docs/images/` has the architecture + `make ci` SVGs).

## 2 · Last delivered
- **MCP support — fully delivered across 3 PRs (all merged 2026-06-29).**
  - **#18 (closes #6) — CMA adapter.** `translate.py` claude-agents block renders static CMA payloads to `targets/claude-agents/`: `agents/<id>.json` (`BetaManagedAgentsCreateAgentParams` — name + configurable `model` from `cma.default_model`=`claude-sonnet-4-5` + `system` from the agent body; tools/skills/metadata empty) and `skills/<id>/` + `skills/<id>.upload.json` (`POST /v1/skills` set + multipart sheet). Static-only (deploy/POST is dotfiles-bootstrap's job). **Bonus fix:** build now ignores `__pycache__`/`*.pyc` (skill-creator carried committed bytecode that CI drift caught).
  - **#20 (closes #19) — mcp render adapter + 4 self-authored primitives.** Neutral connection specs at `primitives-core/mcp/<name>.json` (`agent-bus`, `excalidraw`, `deck-builder`, `audio`; bare commands, secret-free) → `mcp_to_claude`/`mcp_to_opencode`/`mcp_to_cma`. mcp renders shelf-agnostically (config merged at deploy). `check_roster.py` now scans `primitives-core/mcp/`. Schema in `primitives-core/mcp/README.md`.
  - **#21 — curated third-party mcp via `externals.yaml kind:mcp`** (CANON 16): `github` (`${GITHUB_PERSONAL_ACCESS_TOKEN}` Keychain ref), `azure-tools`, `chrome-devtools` → CC+opencode; `claude_design` (remote) → all three, exercising CMA. Specs at `externals/mcp/<id>.json`; `translate.py` gained `parse_externals()`. **Also rewrote the README** (value-prop + honest "what it's not" + real `make ci` proof; SVGs in `docs/images/`).
- **CANON updated:** decision 16 (mcp = connection spec; self→primitives-core/mcp, third-party→externals.yaml kind:mcp) + its open item now resolved.
- **Planning desk** stood up in dotfiles-agents + dotfiles-bootstrap (`_meta/plans/` tracked via gitignore negation; 7-script `_utils/` toolkit; seeded `.github/ISSUE_TEMPLATE/`; per-repo `_config.md` gate menus).
- **#6 brought into conformance** — staged a conformant issue body + deep `plan.md` at `_meta/plans/translation-deferred-adapters/`, published to live #6 (conformance gate 1/1). The plan scopes the residual: CMA adapter (A, unblocked) + mcp render (B, blocked on a first mcp primitive).
- Phase 3 MVP translation service — #17 (`4e8a05b`, closes #7): targets/ (475 files) + results lock + plugins.yaml + Makefile. Agent transform proven live in opencode 1.16.2.
- #16 roster guard + CI · #15 hooks+commands · #14/#13/#12 Phase 2.

## 3 · Where to start building
**Phase 3 is the plan's "consolidation + cross-tool" completion point; 4–5 are reproducibility polish.** Open work:
- ~~**#6 / #19 — translation adapters (CMA + mcp render)**~~ **DONE — #18, #20, #21 all merged.** Plan archived at `_meta/plans/translation-deferred-adapters/plan.md`. The translation service is now feature-complete across all four primitive types + both internal and externals-mcp inputs.
- **NEXT (backlog, no open issues): skill/plugin clone-at-build externals.** `externals.yaml` tracks ~30 third-party skills/plugins with `upstream: null` (URLs unresearched) — only `kind: mcp` renders today. Building this means: research each upstream repo + pin a ref, then implement the clone-at-build step in `translate.py` (clone into `targets/` per CANON 11). This is the last unbuilt capability in the translation service.
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
