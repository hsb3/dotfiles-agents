# Portability conformance wave — dependency contract, mirror checks, fixes + demotions

_Primitives were authored assuming one machine's state (paths, installed custom binaries, dotfiles). This wave makes dependencies a declared, checkable contract (roster `requires:` grammar + mcp `install:` block), mirrors the checks into `make ci`, fixes the fixable items in place, and demotes the unfixable-here items (4 mcp specs + dev-focus hooks) to the workbench. Companion: workbench#32 amends the gate (H5 broadened, H6 new, H4 config/script split) so the next candidate cannot repeat this._

Status: draft
Date: 2026-07-04

## Tracking

#79 (this repo) + workbench#32 (gate amendments). Origin: fresh-machine portability audit, session 2026-07-04. Contract impact: roster schema (`requires:` grammar), mcp spec schema (`install:` block) — both documented in `primitives-core/README.md` / `primitives-core/mcp/README.md` in the same PR. No API/DB surface.

## The problem (grounded in source)

- `primitives-core/mcp/README.md:17` — `command` documented as "bare command — resolved on PATH (portable; no machine paths)"; no install provenance field exists. All four specs (`agent-bus.json`, `audio.json`, `deck-builder.json`, `excalidraw.json`) reference custom binaries (`agent-bus`, `mcp-audio`, `mcp-deck-builder`, `fufo-excalidraw-wire`).
- `scripts/check_roster.py:9` — `requires` list is constrained to `{hooks, local-mcp, hosted-mcp}`; only `comms` uses it (`primitives-core.yaml:108`).
- `scripts/validate_primitives.py` (docstring, "What it checks") — validates frontmatter/spec shape only; no portability checks.
- Offending content, per the 2026-07-04 sweep: `memory-taxonomy/SKILL.md:23-24` (hsb-2026 vault path), `comms/references/comm-package-standard.md:14,22,37` (`~/Developer/fleet-dashboard`, `~/.claude/skills/pptx-henry/...`, wrong account name `mhi-acme`), `obsidian-cli/SKILL.md:20` (`/Applications/...`), `diagrams/SKILL.md:21-23` (`apt-get`, `--break-system-packages`), `setup-project-dashboard/SKILL.md:51` (`speak_gemini`), `pptx-henry/scripts/render-pptx.sh:30` (`pdftoppm`/LibreOffice), `dev-focus/hooks/hooks.json:18,28` (40/70-word inline prompts).
- Demotion mechanics: `translate.py` does not special-case `disposition: demoted` (rg: no hits) and the roster-disk guard requires sources on disk, so demotion = roster entry REMOVED + files moved; record trail in workbench `docs/promotions-log.md` (template there) + `REGISTRY.md` rows.
- Cross-repo guard: `tests/test_check_naming.py` imports naming constants from `../dotfiles-agents-workbench/scripts/promote_check.py` — the workbench change must not rename them.

## Deliverables

- **A — roster `requires:` grammar** (`scripts/check_roster.py`, `primitives-core.yaml` header, `primitives-core/README.md`): accept `cli:<kebab>` / `env:<kebab>` alongside the three capability words.
  Acceptance: unit test proves `requires: [cli:graphviz]` passes and `requires: [gibberish]` fails.
- **B — mcp `install:` block** (`primitives-core/mcp/README.md` schema + `scripts/validate_primitives.py`): stdio specs require `install: {upstream, command}`; http specs exempt.
  Acceptance: validator test fails a stdio fixture without `install:`; externals mcp specs (kind: mcp) covered by the same check.
- **C — mirror checks** (`scripts/validate_primitives.py` + `tests/`): machine-path scan (`/Users/`, `~/` + `$HOME` outside own tree, `/Applications/`, `hsb-2026`, `apt-get install`, `--break-system-packages`); machine-local tool registry scan (undeclared tool reference => must be covered by `requires: cli:<name>`); hook hygiene (`hooks.json` commands must reference `hooks-handlers/`, inline prose <= 20 words).
  Acceptance: one failing fixture test per check; `make ci` green on the fixed tree.
- **D — in-place content fixes** (7 skills, listed above + `dotfiles-expert` gets `requires: [env:dotfiles]`).
  Acceptance: the C-scan returns zero findings; the AC-4 rg sweep in #79 is clean.
- **E — demotions** (roster: remove 4 mcp entries + 2 `dev-focus.*` hook entries; files move to `../dotfiles-agents-workbench/incubator/`; `make build`).
  Acceptance: `make build-check` green; no target fragment for the 6 ids; workbench holds files + records.
- **F — `requires:` backfill** across entries the C-scan flags.
  Acceptance: scan zero-findings (same gate as D).
- Plugin version bumps in `plugins.yaml`: `dev-focus` 1.0.0 -> 2.0.0 (hooks removed), `project-workflow` 0.2.3 -> 0.2.4, `obsidian-plugin-dev` + `project-dashboard` patch bumps (content edits).

## Gate & contract hygiene

| Gate | Fires? | Why |
| ---- | ------ | --- |
| CI aggregate (`make ci`) | yes | always; includes the new checks |
| Roster drift (`make check`) | yes | 6 entries removed |
| Targets drift (`make build-check`) | yes | roster + content edits; run `make build` |
| Naming (`make names`) | no | no renames; fixtures live under `tests/` |
| yamllint | manual | roster + plugins.yaml edited |
| Canonical-doc amendment | yes | `primitives-core/README.md`, `primitives-core/mcp/README.md` same PR |

## Parallelism + landing order

| Unit | Scope | Serializes with |
| ---- | ----- | --------------- |
| workbench#32 (gate text + promote_check + receipt) | workbench repo | receives E's files; land its PR after E's files move, or receive them in the same PR |
| A + B + C | scripts/, tests/, two READMEs | one owner (shared validator file) |
| D | 7 skill dirs, disjoint | parallel-safe; serialize roster edits with F |
| E + F | primitives-core.yaml, targets/ | after C exists (proves the tree clean); one owner |

Safe order: A/B/C -> D -> E/F -> `make build` -> `make ci` -> da PR; workbench PR carries gate amendments + received files + records, citing the da PR.

## Open questions / owner decisions

Stated as defaults in #79 (owner may object): (1) demotion = roster removal; (2) `cli:`/`env:` grammar extends `requires:`; (3) `developer-focus` skill stays rostered, dev-focus plugin ships skill-only at 2.0.0.
