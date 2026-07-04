> **Tracking:** #32, portability audit 2026-07-04 in dotfiles-agents (companion issue: dotfiles-agents#79). The promotion gate's hard checks are blind to the machine-tied assumptions that reached the proven repo; amend the gate and its checker so the next candidate cannot repeat them.

## Problem

A fresh-machine audit of `dotfiles-agents/primitives-core/` (2026-07-04) found pervasive machine-tied assumptions — hardcoded user paths, assumed-installed custom binaries, inline prose in hook configs. The gate should have caught these, but:

1. **H5 is nearly blind.** The gate text bans "machine-local absolute paths" (`docs/promotion-gate.md`, H5), but `scripts/promote_check.py:215` greps only the literal `/Users/henry`. Tilde paths (`~/Documents/Claude/...`), `$HOME` references, `/Applications/...`, vault names (`hsb-2026`), and platform-specific install commands (`apt-get install`) all pass clean.
2. **No dependency check exists.** Nothing requires a candidate to declare the binaries or machine state it needs. All 4 custom-binary MCP specs promoted with zero install provenance; skills invoking custom `~/.local/bin` tools (`cc-project-memory`, `speak_gemini`) promoted without declaring them.
3. **H4 says nothing about config structure.** `dev-focus/hooks/hooks.json` carries 40- and 70-word inline prompts and passed. The intended discipline: hooks are a JSON config + handler scripts — no inline scripts, no inline prose beyond ~20 words (prose lives in referenced files).

The grandfathered batch predates the gate, but the gate as implemented would not have caught these defects on a new candidate either.

## Deliverables

- A — **Gate amendments** in `docs/promotion-gate.md` (written now, marked pending ratification per governance — same pattern as the 2026-07-02 amendments):
  - **H5 broadened**: "self-contained and clean" explicitly covers tilde/`$HOME` paths outside the candidate's own tree, `/Applications/` paths, personal vault/project names, and platform-specific install commands.
  - **H6 (new): declared dependencies.** Every non-ubiquitous binary/app/machine-state a candidate invokes must be declared (destination roster `requires:` grammar `cli:<kebab>` / `env:<kebab>` — checked at the move like H3; `promote_check.py` prints the detected dependency list for attestation). A stdio MCP spec must carry an `install:` block (upstream + install command).
  - **H4 amended: config/script split.** Hook `hooks.json` command values must be handler-script references (no inline scripts); inline prose (prompts) capped at 20 words — longer prose lives in a referenced file beside the handlers.
- B — **`scripts/promote_check.py` implementation** of the three checks above, with the existing naming-grammar constants left untouched (dotfiles-agents `tests/test_check_naming.py` imports them).
- C — **Receive the demoted items** from the companion dotfiles-agents issue into `incubator/`: `agent-bus`, `audio`, `deck-builder`, `excalidraw` (MCP specs), `dev-focus` hooks (config + handlers). One `REGISTRY.md` row each; one demotion record each in `docs/promotions-log.md` citing the audit + companion issue (per `docs/requalification.md`, obligation 3: demote on failure-in-use).

## Acceptance criteria

- [ ] `promote_check.py` run against fixtures fails on: a file containing `~/Documents/...`; a file containing `/Applications/...`; a stdio MCP spec with no `install:` block; a `hooks.json` with a 21+ word inline prompt; a `hooks.json` with an inline shell command that is not a handler reference.
- [ ] `promote_check.py` against a clean fixture candidate stays green, and its output includes the detected-dependency list for H6 attestation.
- [ ] `docs/promotion-gate.md` carries the three amendments with a status line noting they are written but pending ratification.
- [ ] `incubator/` contains the 5 received items, each with a `REGISTRY.md` row; `docs/promotions-log.md` carries 5 demotion records with cited trigger and the dotfiles-agents roster-update ref.
- [ ] Naming-grammar constants in `promote_check.py` are byte-identical before/after (the dotfiles-agents cross-repo test still passes).

## Dependencies & gates

- Companion: dotfiles-agents portability-conformance-wave issue (roster removals land there; the demotion records here cite its PR/commit).
- Ratification: the gate-text amendments are Henry's to ratify (CANON governance); the checker can land first since it only tightens.
- Gates that fire: repo CI (promote-check self-tests, if present); cross-repo naming-grammar import from dotfiles-agents.

## Out of scope

- Reworking the received items to pass the amended gate (each is its own incubation effort; dev-focus needs the config/script split plus a prompt-file rendering answer before re-promotion).
- opencode hook support (deferred per the distribution-capability-matrix decision).
