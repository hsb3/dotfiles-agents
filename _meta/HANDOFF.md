# HANDOFF — dotfiles-agents

*Cold-start bridge. Secret-free (secrets live in `_meta/operations/`, never tracked). Not a journal — shipped work lives in git/PR history; this holds current state, in-flight work, decisions, and the gotchas that bite.*

## 0 · Orientation

Source of truth for **proven** coding-agent extenders (created 2026-06-26; built from scratch — NOT a rename of `hsb3-custom-plugins`, which stays frozen as the migration source). Siblings: `dotfiles` (tooling), `dotfiles-agents-workbench` (the unproven bench — promotes one-way INTO here), `dotfiles-bootstrap` (deploy/orchestrator). Governance on the strategy desk (`~/Documents/Claude/Projects/dotfiles-agents-cowork/`): `_structure/{CANON.md, repository-technical-plan.md}` is the design constitution; `analyses/` is historical. The promotion gate + lifecycle live in `dotfiles-agents-workbench/docs/`. **Planning desk** at `_meta/plans/` — run the `planning-desk` skill; `_config.md` has the gate menu.

## 1 · Current state

- **Translation service is feature-complete** across all four primitive types (skills · agents · CMA payloads · mcp) plus internal + externals-mcp inputs: `scripts/translate.py` renders `primitives-core/` + `externals.yaml` → `targets/{claude-code,opencode,claude-agents}/` + a content-hash lock. **Roster/build/test counts are live — run `make ci`** (5 lanes: `check` roster↔disk · `validate` primitive content · `names` id grammar · `build-check` targets drift · `test`). Green on main.
- **Roster schema:** `origin: authored|sourced` (internal is dead), required `disposition:`, optional `requires:` capability flags, sourced ⇒ `upstream`+`ref` guard-enforced.
- **Promotion gate RATIFIED** (CANON 12; J1 = ≥2 real uses). **Branch protection** live: required check is the `make ci` aggregate; force-push/deletion blocked; admin bypass retained — agents PR.

## 2 · In flight / next up

- **The backlog is fully planned AND ruled (2026-07-03):** every open issue (#27 #32 #33
  #36 #37 #39 #48 #49 #59) has a source-grounded `_meta/plans/<slug>/plan.md`, and the
  owner accepted the recommended defaults for all 51 open decisions — ruling record:
  `_meta/_archive/decision-sheet-2026-07-03.md`. Build waves start with **#39** (add the
  `record:` roster field) and **#32** (16-command disposition, `skills` CLI retirement,
  archive hsb3-custom-plugins — the only P1). #27 (pw- rename wave, plugin 0.3.0) next;
  coordinate version bumps with #32.
- **Gate-2 pilot (#33) is in close-out, not execution:** the pilot ran 2026-07-02
  (rgpt#541, 36/22 to 56/3); the 2026-07-03 round-2 mechanical pass is COMMITTED in
  raptorgpt-agents (d4ab1851; repo at `~/Developer/raptorgpt-agents` — flat, the old
  nested path is dead). Remaining: re-audit evidence, gap-justification ledger,
  TC-013/TC-010 addenda in the `hsb-2026` Obsidian vault, Henry's sign-off ticks.
- **fleet-dashboard is the plugin test bed** (owner decision 2026-07-03) — exercise
  project-workflow skills there first; it already produced #67/#72 (both fixed, 0.2.2).
- **J1 upgrades (post-Q-13):** the 2026-07-03 sweep (#31) dispositioned all 84 entries `grandfathered-pending-use` (17 flipped to `origin: sourced` with pinned refs); items now upgrade to `qualified` on ≥2 cited real uses (re-qualification record in the workbench promotions log) or demote on failure-in-use. #37's ra-platform adoption is use-citation #1 for `planning-desk`.
- **Promoting a parked item** (CANON 12) needs ≥2 cited real uses + H1–H5; `opencode-expert` is the strongest candidate.
- **Portability conformance wave (#79 + wb#32) — SHIPPED 2026-07-04.** da#80 + wb#33 both
  squash-merged; #79 + wb#32 closed; gate amendments **ratified** (H5-broadened/H6/H4-split,
  `promotion-gate.md`); plan archived at `_meta/_archive/79-portability-conformance-wave.md`.
  Machine-agnostic enforcement is now live in `make ci` (see gotcha below). Residual carried
  to the workbench backlog: `comms`' deck-builder toolchain is dead until that mcp
  re-promotes with an `install:` block (pptx-henry path still works); the 4 demoted mcp specs
  + dev-focus hooks incubate in the workbench (dev-focus re-promotion needs a prompt-file
  rendering answer in the translation service); workbench `claude-exchange` + `strategy-desk`
  flipped to blockers under the amended checks (true positives — REGISTRY has detail). One
  owner TODO left: record the gate-ratification decision in the vault registry.

## 3 · Conventions & gotchas

- **Never hand-edit generated `targets/` or the results lock** — they're drift-guarded. Edit `primitives-core/` then `make build`.
- **Tests are stdlib `unittest` only** — keep `make ci` zero-install (no pytest/uv in the required lane). **Fixtures live under `tests/` temp dirs, never `primitives-core/`** — `check_roster.py` flags on-disk orphans. Drift guards prove *consistency*; the tests + `validate_primitives.py` prove *correctness*.
- **SKILL.md `description` must not contain XML/angle-bracket tags** — Claude Cowork refuses to load such skills. Skill-specific: agent `.md` descriptions may use `<example>`. Enforced by `validate_primitives.py`.
- **Primitives must be machine-agnostic (#79, enforced in `make ci`):** no `/Users/...`, personal
  vault names, `~/Documents|Desktop` paths, or `--break-system-packages`; `~/dotfiles`,
  `/Applications/`, and machine-local tools (cc-project-memory, speak_gemini, …) are legal only
  with a covering roster `requires:` (`cli:<name>` / `env:dotfiles`); stdio mcp specs need an
  `install: {upstream, command}` block; hook configs are handler references only, inline prose
  ≤ 20 words. The workbench gate mirrors these (H5/H6/H4, wb#32).
- **Naming grammar is shared with the workbench:** `tests/test_check_naming.py` imports the sibling `../dotfiles-agents-workbench/scripts/promote_check.py` constants and asserts no drift — but it **silently skips when the sibling checkout is absent**. Keep the two repos side-by-side to run it; don't rename the grammar constants on either side.
- **Board scripts are authoritative HERE** (`primitives-core/skills/github-project-board/scripts/`) — deliberately diverged from frozen hsb3-custom-plugins; never re-copy from the frozen repo.
- **Archived plans:** `_meta/_archive/<issue>-<slug>.md` (tracked via gitignore negation). On close, `git mv` the `plan.md` there and move its README row ACTIVE→ARCHIVED so `reconcile.py` stays clean. Run `_meta/plans/_utils/` scripts from the **main tree** (they read live `gh` + disk); ACTIVE README rows use the **bare slug**, not a markdown link.
- **`gh` token gotcha:** env `GITHUB_TOKEN` can't resolve project-board owner — use `env -u GITHUB_TOKEN gh …` for `gh project` / `gh repo create`.
- **Conflicting PRs get NO CI:** GitHub skips `pull_request` workflows when the merge ref won't build — "no checks reported" means rebase onto main first, not that CI failed.
- **Deploy targets (verified, opencode 1.16.2):** opencode agents → `.opencode/agent(s)/` or `~/.config/opencode/agent(s)/`; opencode skills auto-scanned from `~/.claude/skills/` + `~/.agents/skills/` (config loaded once — restart opencode to pick up new skills). CC marketplace = two generated catalogs: `claude plugin marketplace add hsb3/dotfiles-agents` reads the repo-root `.claude-plugin/marketplace.json`; a local-path add of `targets/claude-code` reads that dir's own marketplace.json (what `dotfiles-bootstrap` uses). Both drift-guarded in `make ci`.
- `bgIsolation:none` in `.claude/settings.json` — this repo isn't parallel-mutated; background agents share the main tree.
- Trunk-based, remote is SSH: branch `<type>/<name>`, squash-merge, commits end with the `Claude-Session:` footer; agents PR (don't push main).

## 4 · Incident log

- **2026-07-04 — `gh issue edit` cross-repo clobber (recovered).** While filing the wave
  issues, `gh issue edit 32 --body-file <workbench-body>` ran from the dotfiles-agents cwd
  and overwrote **da#32**'s body (retire-hsb3-custom-plugins) instead of workbench#32.
  Restored within minutes from GitHub's edit history (GraphQL `userContentEdits` — the
  `diff` field holds full body snapshots). Lesson: **always pass `-R <owner>/<repo>` to
  `gh issue edit`/`view` when the target repo isn't the cwd** — issue numbers collide
  across sibling repos, and da/wb numbering is close enough to bite again.
