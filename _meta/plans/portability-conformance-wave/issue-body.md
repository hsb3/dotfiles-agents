> **Tracking:** #79, portability audit 2026-07-04 (fresh-machine session on the second MacBook surfaced machine-tied assumptions across all four primitive types); companion gate issue: workbench#32. Primitives must not assume any one machine's state; dependencies become a declared, checkable contract.

## Problem

Primitives were authored on one machine and silently assume its state. A full sweep of `primitives-core/` (audit session 2026-07-04) found three defect classes, none of which any current guard catches:

1. **Assumed-installed binaries.** All 4 MCP specs (`agent-bus`, `audio`, `deck-builder`, `excalidraw`) reference custom stdio binaries with zero install provenance — `primitives-core/mcp/README.md:17` documents `command` as "bare command — resolved on PATH (portable; no machine paths)", which assumes the binary exists and gives dotfiles-bootstrap nothing to act on. Skills likewise: `diagrams/SKILL.md:21-23` (`apt-get install -y graphviz`, `pip install --break-system-packages` — Linux-only + non-standard), `obsidian-cli/SKILL.md:20` (hardcoded `/Applications/Obsidian.app/...`), `memory-taxonomy/SKILL.md:14` (`cc-project-memory` with no source stated), `setup-project-dashboard/SKILL.md:51` (`speak_gemini`), `pptx-henry/scripts/render-pptx.sh:30` (`pdftoppm` + LibreOffice/PowerPoint, macOS-only).
2. **Machine/user-specific state.** `memory-taxonomy/SKILL.md:23-24` points at the `hsb-2026` Obsidian vault path as the authoritative design doc; `comms/references/comm-package-standard.md:14,22,37` hardcodes `~/Developer/fleet-dashboard`, `~/.claude/skills/pptx-henry/assets/theme-tokens.js`, and states the work GitHub account as `mhi-acme` (a client-token scrub left a factually wrong account name).
3. **No dependency contract.** The roster's `requires:` vocabulary is `hooks|local-mcp|hosted-mcp` only (`scripts/check_roster.py:9`) and exactly one entry uses it (`comms`). There is no way to declare "this primitive needs binary X / machine state Y", so nothing can check or provision it.

The hooks half of the problem (inline prompts in `dev-focus/hooks/hooks.json`, config/script split) is enforced by the new checks here; the gate-side rules land in the sibling workbench issue.

Why the guards missed it: the workbench gate's H5 scans only the literal `/Users/henry` (`dotfiles-agents-workbench/scripts/promote_check.py:215`), and all 84 roster entries are `grandfathered-pending-use` (promotions log, 2026-07-03 Q-13 record) — they never faced even that narrow check. This repo's `validate_primitives.py` has no portability checks at all.

## Deliverables

- A — **Roster schema: dependency grammar.** Extend `requires:` with `cli:<kebab>` (a binary/app that must be installed) and `env:<kebab>` (machine state, e.g. `env:dotfiles`), keeping the three existing capability words. Grammar validated in `scripts/check_roster.py`; documented in the `primitives-core.yaml` header and `primitives-core/README.md`.
- B — **MCP spec schema: install provenance.** A required `install:` block for stdio specs (`upstream` repo/URL + `install` command) in `primitives-core/mcp/README.md` schema, enforced by `scripts/validate_primitives.py`.
- C — **Mirror checks in `make ci`** (`scripts/validate_primitives.py` + tests): (1) machine-path scan over `primitives-core/` — `/Users/`, `~/` and `$HOME` paths outside the primitive's own tree, `/Applications/`, vault names, `apt-get install`, `--break-system-packages`; (2) undeclared-dependency scan — references to a maintained machine-local tool registry (custom `~/.local/bin` scripts, custom MCP binaries) must be covered by the entry's `requires:`; (3) hook config hygiene — `hooks.json` command values must be handler references (no inline scripts), inline prose (prompts/args) capped at 20 words.
- D — **In-place fixes** for: `diagrams` (portable per-platform install), `obsidian-cli` (per-platform binary resolution), `comms` references (resolve dashboard/theme paths at runtime; fix the account name), `memory-taxonomy` (genericize the vault pointer), `setup-project-dashboard` (declare `speak_gemini` optional with provenance), `pptx-henry` (per-platform prereqs section), `dotfiles-expert` (declare `requires: [env:dotfiles]` — domain-scoped by design, not demoted).
- E — **Demotions.** Remove the 4 MCP entries + the 2 `dev-focus.*` hook entries from the roster; move files to `dotfiles-agents-workbench/incubator/`; demotion records in the workbench promotions log citing this issue; the `dev-focus` plugin ships skill-only until the hooks re-qualify; `make build` regenerates targets.
- F — **`requires:` declarations** added across remaining entries wherever the new scan detects a dependency.

## Acceptance criteria

- [ ] `make ci` green, including the new validator checks and their unit tests.
- [ ] `validate_primitives.py` fails on test fixtures containing: a machine-local path, an undeclared registry tool, a stdio MCP spec without `install:`, and a hook config with a 21+ word inline prompt (each proven by a test).
- [ ] `rg -n '/Users/|/Applications/|hsb-2026|--break-system-packages|apt-get install' primitives-core/` returns zero hits (excluding test fixtures, which live under `tests/`).
- [ ] The roster has no entry for `agent-bus`, `audio`, `deck-builder`, `excalidraw`, `dev-focus.SessionStart.session-start`, or `dev-focus.Stop.stop-summary`; `make build-check` passes (targets contain no fragments for them).
- [ ] Workbench `incubator/` contains the 5 demoted items (4 MCP + dev-focus hooks) with `REGISTRY.md` rows, and `docs/promotions-log.md` carries one demotion record per item citing this issue.
- [ ] Every remaining roster entry whose content references a registry tool carries a covering `requires:` entry (the scan proves it — zero findings).
- [ ] `primitives-core/mcp/README.md` and `primitives-core/README.md` document the new schema in the same PR.

## Dependencies & gates

- Soft-ordered after the workbench gate-amendment issue (rules are canonical there; this repo mirrors them). Not hard-blocked — the mirror checks can land first as long as wording matches the gate amendment.
- Gates that fire: CI aggregate (`make ci`); roster drift (`make check` — entries removed); targets drift (`make build-check` — regenerate with `make build`); canonical-doc amendment (`primitives-core/README.md`, `primitives-core/mcp/README.md`; `CLAUDE.md` model section unchanged — verify); yamllint (roster edited, manual).
- Gates that do NOT fire: naming taxonomy (no renames; fixture names live under `tests/`).
- Cross-repo coupling: `tests/test_check_naming.py` imports workbench `promote_check.py` constants — the workbench change must not rename those constants.
- `comms` keeps working without the demoted `deck-builder` MCP via its `pptx-henry` toolchain; its `requires: [local-mcp]` line is updated to reflect reality.

## Out of scope

- Restructuring `dev-focus` itself (config/script split, prompt files) — that is workbench rework under the amended gate, before any re-promotion.
- opencode hook rendering — deferred per the distribution-capability-matrix decision (opencode hooks are TS-plugin-only).
- Q-13 re-qualification of the remaining grandfathered entries; the `record:` roster field (#39); the pw- rename wave (#27).

## Stated defaults (objections welcome, else these stand)

1. **Demotion mechanics:** a demoted item's roster entry is REMOVED (files leave the repo; the promotions-log record + workbench REGISTRY row carry the state). The `demoted` enum value stays for transitional use, but a rostered entry whose files are gone would fail the roster-disk guard.
2. **Dependency grammar:** `cli:<kebab>` / `env:<kebab>` extends `requires:` rather than adding a new roster field — one declaration point for deploy tooling.
3. **`developer-focus` skill stays rostered** (dev-focus plugin ships skill-only); only the hook primitives demote.
